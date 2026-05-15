# Data Model: Critical File Declarations and Guardrails

**Feature**: 001-critical-files
**Phase**: 1 (Design)
**Date**: 2026-05-14

Four entities, three persistent (SQLite) and one config-derived. All persistent
entities live in `.idlergear/db.sqlite`. Backup file contents live on the
filesystem under `.idlergear/backups/`; the SQLite tables index them.

## CriticalFileDeclaration (config-derived, in-memory)

Source: `.idlergear/config.toml` array of `[[critical_files]]` tables. Re-read
at MCP server startup and on `idlergear reload`. Not persisted as a separate
table.

| Field | Type | Default | Notes |
|---|---|---|---|
| `path` | string | required | Gitignore-style glob pattern. Non-empty. |
| `canonical` | string | null | URI; recognised schemes: `gh:`, `hf:`, `s3://`, `https://`, or anything (paired with `check_cmd`). |
| `check_cmd` | string | null | Shell command, invoked with the local file path; exit 0 = match. |
| `auto_backup` | bool | true | Whether to back up before edits. |
| `backup_max` | int | 10 | Retention cap; ≥0. 0 means "no retention". |
| `opt_out` | bool | false | Disables protection for this declaration (use sparingly). |

### Validation rules

- `path` MUST be non-empty.
- `backup_max` MUST be ≥ 0.
- `opt_out = true` together with `auto_backup = true` produces a validation
  warning (the combination is legal but suspicious).
- `canonical` without `check_cmd` and without a recognised URI scheme produces
  a validation warning (no divergence check will run).
- Patterns matching common tool-managed paths (`.git/**`, `node_modules/**`,
  `__pycache__/**`) produce a validation warning.
- Malformed TOML or unknown top-level fields in a `[[critical_files]]` table:
  refuse to start the MCP server with a clear error (FR-011).

## CriticalFileBackup (SQLite)

Table: `critical_file_backup`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | TEXT | PRIMARY KEY | UUID4 hex. |
| `declaration_path` | TEXT | NOT NULL | The glob pattern that matched. |
| `source_path` | TEXT | NOT NULL, INDEXED | Absolute path of the file at backup time. |
| `backup_path` | TEXT | NOT NULL | Absolute path of the stored snapshot. |
| `created_at` | TEXT (ISO-8601) | NOT NULL, INDEXED | Includes microseconds. |
| `size_bytes` | INTEGER | NOT NULL | For pruning heuristics if needed. |
| `triggering_operation` | TEXT | NOT NULL | enum: `edit`, `overwrite`, `restore`. |

### Lifecycle

- Created before any in-place edit or in-place overwrite of a matched path.
- Pruned after each successful creation: rows for the same `source_path` beyond
  `backup_max` (oldest by `created_at`) are deleted, and their `backup_path`
  files unlinked.
- Never auto-deleted on file deletion of the source (a backup is the last
  recovery option in that case).

### Indexes

- `(source_path, created_at DESC)` — primary access pattern (find most recent
  backup of a given file).
- `(declaration_path, created_at DESC)` — for the status resource per-
  declaration view.

## DivergenceStatus (SQLite)

Table: `critical_file_divergence`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | TEXT | PRIMARY KEY | UUID4 hex. |
| `declaration_path` | TEXT | NOT NULL, INDEXED | |
| `source_path` | TEXT | NOT NULL, INDEXED | The actual matched file path. |
| `checked_at` | TEXT (ISO-8601) | NOT NULL | |
| `result` | TEXT | NOT NULL | enum: `match`, `diverge`, `error`, `not_configured`. |
| `error_message` | TEXT | nullable | Captured stderr when result is `error`. |
| `duration_ms` | INTEGER | NOT NULL | Wall-clock time of the check. |

### State transitions

```
[fresh declaration]
   │
   ├── no check_cmd ─────────────────────────────► not_configured
   │
   └── has check_cmd
            │
            ▼
       [run check]  ──── exit 0 ───────► match
            │
            ├── exit nonzero, stderr ───► diverge  (when exit code in {1,2})
            │
            └── exec error/timeout ─────► error    (preserves error_message)
```

The most recent row per `(declaration_path, source_path)` is the current
status; older rows form a history retained for at most 30 days.

## CriticalFileAuditEntry (SQLite)

Table: `critical_file_audit`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | TEXT | PRIMARY KEY | UUID4 hex. |
| `declaration_path` | TEXT | NOT NULL | |
| `source_path` | TEXT | NOT NULL, INDEXED | |
| `operation_type` | TEXT | NOT NULL | enum: `delete`, `overwrite`, `replace`, `edit`, `restore`. |
| `attempted_at` | TEXT (ISO-8601) | NOT NULL | |
| `outcome` | TEXT | NOT NULL | enum: `allowed`, `denied`, `confirmed`. |
| `backup_id` | TEXT | nullable, FK | Set when a backup was created as part of the operation. |
| `reason` | TEXT | nullable | E.g., "non-interactive context", "user cancelled". |

### Lifecycle

- One row per detected destructive operation (FR-014). Includes operations
  that were `allowed` because they matched no declaration? **No** — only
  operations against declared paths are recorded. Storing every operation
  would conflict with FR-015 (zero overhead when no declarations).
- Audit entries are never deleted by the feature itself. Retention is the
  user's responsibility via `idlergear doctor --vacuum-audit` (a future
  command, out of scope for v0.9).

## Relationships

```
CriticalFileDeclaration (config)
   │ (1) ─── matches by glob ───► (N) source paths on disk
   │
   ├──► (0..N) CriticalFileBackup
   │             linked by: declaration_path + source_path
   │
   ├──► (0..N) DivergenceStatus
   │             linked by: declaration_path + source_path
   │
   └──► (0..N) CriticalFileAuditEntry
                 linked by: declaration_path + source_path
                 audit.backup_id ─► CriticalFileBackup.id (nullable)
```

No foreign keys to `CriticalFileDeclaration` (it lives in TOML, not SQLite).
The `declaration_path` column is a soft reference — if a declaration is
removed from config, historical rows referencing it remain.

## Schema migrations

Initial schema is shipped as `001-critical-files.sql` in
`src/idlergear/migrations/`. The migration:

1. Creates the three tables and indexes.
2. Creates `.idlergear/backups/` if absent.
3. Records itself in a `schema_migrations` table.

No backward-compatibility migrations are needed (this is a v0.9 introduction).
Future schema changes follow the constitution's SemVer rules: PATCH for
additive optional columns; MINOR for additive structural changes with
migration scripts; MAJOR for breaking changes.

## Storage size estimates

Per declaration with daily edits and `backup_max = 10`:

- 10 backup files on disk (size proportional to source file size).
- 10 rows in `critical_file_backup` table (~200 bytes each).
- 1 row in `critical_file_divergence` per active check (or daily if cached).
- 1 row in `critical_file_audit` per destructive operation against the path.

For the llmfp case (~5 declared paths, ~20 destructive operations per week,
~50 edits per week), the SQLite tables are negligible (<100 KB/year) and
the backup directory size is dominated by the source file sizes (50-100 MB
per fingerprint × 10 retention = 500 MB-1 GB per declared file in steady
state).

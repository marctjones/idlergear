# MCP Tool Contracts: Critical File Declarations and Guardrails

**Feature**: 001-critical-files
**Phase**: 1 (Design)

This feature contributes **one new MCP tool** and **one extended tool**.
Tool count delta: **+1** against the v0.9 ceiling of 15.

## `idlergear_file_critical` (new)

State-modifying actions against critical-file declarations. The current MCP
tool surface for v0.9 is intentionally small: one tool with multiple action
modes, not many tools with overlapping behavior (Principle III).

### Input schema

```jsonc
{
  "action": "declare" | "undeclare" | "check" | "list" | "audit",
  "path": "string (required for declare/undeclare/check)",
  "canonical": "string (optional; declare only)",
  "check_cmd": "string (optional; declare only)",
  "auto_backup": "boolean (optional; declare only; default true)",
  "backup_max": "integer (optional; declare only; default 10)",
  "since": "ISO-8601 timestamp (optional; audit only)"
}
```

### Action: `declare`

Adds or updates a `[[critical_files]]` entry in `.idlergear/config.toml`.

- **Preconditions**: `path` is non-empty. If a declaration with the same `path`
  already exists, this overwrites it.
- **Side effects**: Writes to `.idlergear/config.toml`. Triggers a config
  reload in the running MCP server.
- **Returns**: `{ "declared": true, "path": "<path>", "warnings": [...] }`.
- **Validation warnings** are listed but do not block declaration: see
  CriticalFileDeclaration validation rules in `data-model.md`.

### Action: `undeclare`

Removes a `[[critical_files]]` entry by `path`.

- **Preconditions**: A declaration with the given path exists.
- **Side effects**: Writes to config. Does NOT delete existing backups,
  divergence history, or audit records (FR-009 preserves history).
- **Returns**: `{ "removed": true, "path": "<path>" }`.
- **Errors**: `not_found` if no declaration matches the path.

### Action: `check`

Runs the divergence check for a single declaration on demand and records the
result in `critical_file_divergence`.

- **Preconditions**: A declaration exists for `path` with `check_cmd` or a
  recognised `canonical` scheme.
- **Side effects**: Invokes the check command (subject to timeout); inserts a
  row in `critical_file_divergence`.
- **Returns**: `{ "result": "match" | "diverge" | "error", "checked_at": "...",
  "duration_ms": N, "error_message": "..." | null }`.

### Action: `list`

Returns the current declarations with their most recent divergence status and
backup counts.

- **Preconditions**: none.
- **Side effects**: none (read-only).
- **Returns**: see `idlergear://files/critical` resource shape in
  `mcp-resources.md`.

> **Note on duplication**: `list` overlaps with the `idlergear://files/critical`
> resource. The tool exists for clients that don't support resources; the
> resource is preferred when available. This is an explicit, narrowly-scoped
> redundancy justified in the plan's Complexity Tracking.

### Action: `audit`

Returns audit-log entries for destructive operations since `since` (or the
last 7 days by default).

- **Preconditions**: none.
- **Side effects**: none.
- **Returns**: `{ "entries": [{ "operation_type": "...", "source_path": "...",
  "attempted_at": "...", "outcome": "...", "reason": "..." }, ...] }`.

### Error responses

All actions use a uniform error envelope:

```json
{ "error": { "code": "string", "message": "string", "details": {} } }
```

Error codes:

- `invalid_path` — empty or non-string path.
- `not_found` — referenced declaration doesn't exist (undeclare, check).
- `config_invalid` — current config.toml is malformed (FR-011).
- `check_failed` — divergence check command failed to execute.
- `not_supported` — canonical scheme has no installed helper and no
  `check_cmd` was provided.

## `idlergear_doctor` (extended)

Existing tool — adds `--scope critical` and includes critical-file divergence
in the default `--scope all`. Tool count delta is **0** (extension, not new
tool).

### New behavior (only the additions)

- When called with `scope=="critical"` or `scope=="all"`:
  - Iterates declarations and runs each `check_cmd` (subject to the same
    timeout and error-capture semantics as `idlergear_file_critical.check`).
  - Returns a section in the output keyed `critical_files` with per-
    declaration status, backup counts, last-audit summary.
- Performance: when no declarations are present, the section is omitted with
  zero overhead (FR-015, SC-005).

## Out of scope for v0.9 (tools deliberately not added)

- `idlergear_file_critical_restore` (restore from a backup) — manual file copy
  from `.idlergear/backups/` suffices. Add in v0.10 if friction is observed.
- `idlergear_file_critical_diff` (show local-vs-canonical content diff) — the
  user can run their own diff against a fetched canonical version. Adding a
  tool here would require IdlerGear to fetch canonical content, which is out
  of scope.
- Per-action sub-tools (`idlergear_critical_declare`, `..._undeclare`, etc.):
  rejected to stay within tool ceiling.

## Tool description (≤200 chars per constitution)

```
idlergear_file_critical: declare, undeclare, check, list, or audit critical
file paths. Critical files trigger confirmation on destructive ops and are
backed up before edits. See idlergear://files/critical resource.
```

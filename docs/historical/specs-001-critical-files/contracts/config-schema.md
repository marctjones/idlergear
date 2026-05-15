# Config Schema: `.idlergear/config.toml` — critical_files section

**Feature**: 001-critical-files
**Phase**: 1 (Design)

This is the user-facing configuration contract. Stable for v0.9.x; changes
follow the constitution's SemVer rules.

## Top-level shape

```toml
[[critical_files]]
path = "fingerprints/*.json"
canonical = "hf:marcjon/llmfp-fingerprints"
check_cmd = "python scripts/hf_library_sync.py --check"
auto_backup = true
backup_max = 10
opt_out = false

[[critical_files]]
path = ".env"
auto_backup = true
# canonical and check_cmd omitted; protection-only

[[critical_files]]
path = "data/local-db.sqlite"
auto_backup = true
backup_max = 5
```

## Field reference

### `path` (required, string)

Gitignore-style glob pattern, evaluated relative to the project root. Examples:

- `fingerprints/*.json` — direct children
- `fingerprints/**/*.json` — recursive
- `.env` — exact match
- `data/**` — entire subtree

Must be non-empty.

### `canonical` (optional, string)

URI identifying the canonical version of the file. Recognised schemes:

| Scheme | Helper | Example |
|---|---|---|
| `gh:` | `gh` CLI | `gh:owner/repo/blob/main/path` |
| `hf:` | `huggingface-cli` | `hf:user/dataset` |
| `s3://` | `aws` CLI | `s3://bucket/key` |
| `https://` | `curl` | `https://example.com/file` |
| `file://` | local cp | `file:///mnt/canonical/path` |
| (anything else) | requires `check_cmd` | — |

If `canonical` is set and the scheme has a built-in helper, the helper is
used to perform divergence checks unless `check_cmd` overrides it.

### `check_cmd` (optional, string)

Shell command for checking divergence. Invoked with the local file path as
its sole argument. Exit code semantics:

| Exit | Meaning |
|---|---|
| 0 | Local matches canonical. |
| 1 | Local diverges. |
| 2 | Local diverges, structured stderr (advanced — captured to `error_message`). |
| other | Tool error; surfaced as `error` divergence result. |

Timeout: 30 seconds. Longer-running checks should write to a side-cache and
return quickly.

### `auto_backup` (optional, bool, default true)

Whether to back up before in-place edits (Write to existing path, Edit). If
false, edits proceed without backups. Removal/overwrite still require
confirmation regardless (FR-004).

### `backup_max` (optional, int, default 10)

Maximum retained backups per matched file path. Older backups are pruned
after each new backup is created. Set to 0 to disable retention entirely (a
backup is still created if `auto_backup=true` but is immediately eligible for
pruning if a newer one arrives).

### `opt_out` (optional, bool, default false)

Disables all protection for this declaration. Useful for negative-matching
patterns combined with broader declarations (e.g., declare `data/**` then
opt-out `data/scratch/**`).

The overlap-resolution rule applies (R10 in `research.md`): if a path matches
both an opt-out declaration and a protective declaration, the protective
declaration wins.

## Top-level fields

In addition to the `[[critical_files]]` array, the following optional
top-level fields configure feature-wide behavior:

### `elicitation_timeout_seconds` (optional, int, default 60)

How long the system waits for a user response to a confirmation elicitation
before defaulting to deny (FR-004). Range: 1-600 seconds. Values outside
this range produce a configuration error at startup (FR-011).

```toml
elicitation_timeout_seconds = 30      # tighter window for fast workflows
```

When elicitation is unavailable (the connected client does not advertise
elicitation capability), this field has no effect — non-interactive deny
applies immediately per FR-016.

## Validation

At MCP server startup and on `idlergear reload`:

| Condition | Result |
|---|---|
| TOML syntax error | server start FAILS with clear error (FR-011) |
| Unknown field in `[[critical_files]]` | server start FAILS |
| `path` empty | server start FAILS |
| `backup_max` < 0 | server start FAILS |
| `path` matches `.git/**`, `node_modules/**`, `__pycache__/**` etc. | warning, server starts |
| `canonical` set but no `check_cmd` and unrecognised scheme | warning, server starts |
| `opt_out = true` together with `auto_backup = true` | warning, server starts |

## Example use cases

### Example 1: HuggingFace-canonical fingerprints

```toml
[[critical_files]]
path = "fingerprints/*.json"
canonical = "hf:marcjon/llmfp-fingerprints"
auto_backup = true
backup_max = 10
```

### Example 2: Local-only protected configs

```toml
[[critical_files]]
path = ".env"
auto_backup = true

[[critical_files]]
path = "config/secrets.local.toml"
auto_backup = true
backup_max = 20
```

### Example 3: Subtree with carve-outs

```toml
[[critical_files]]
path = "data/**"
auto_backup = true
backup_max = 5

[[critical_files]]
path = "data/scratch/**"
opt_out = true
# scratch is fine to lose; but the "data/**" rule above still protects
# (overlap → most-protective wins), so this opt_out is effectively warning-
# level only. To truly exclude, remove the data/** glob from data/scratch/**.
```

## Migration from earlier versions

This feature is new in v0.9. No prior IdlerGear version had a
`[[critical_files]]` block. Users upgrading from v0.8.x see no change unless
they add declarations.

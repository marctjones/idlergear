# MCP Resource Contracts: Critical File Declarations and Guardrails

**Feature**: 001-critical-files
**Phase**: 1 (Design)

Resources contributed: **2**. Total Resources delta against the v0.9 ceiling
of 8: **+2**.

All resources are read-only (Principle III) and emit JSON unless otherwise
noted.

## `idlergear://files/critical`

The current list of critical-file declarations with summary state. Auto-
updates when declarations change.

### Returns

```jsonc
{
  "declarations": [
    {
      "path": "fingerprints/*.json",
      "canonical": "hf:marcjon/llmfp-fingerprints",
      "auto_backup": true,
      "backup_max": 10,
      "opt_out": false,
      "matches": 47,                  // current paths matching this glob
      "backup_count": 12,             // total backups stored
      "latest_backup_at": "2026-05-14T13:02:44.123Z",
      "latest_divergence": {
        "result": "match",            // match | diverge | error | not_configured
        "checked_at": "2026-05-14T12:00:00.000Z",
        "duration_ms": 1840
      },
      "warnings": []                  // from validation
    },
    ...
  ],
  "config_status": "ok" | "invalid",
  "config_error": null | "string"
}
```

### Subscribe semantics

Clients SHOULD subscribe. Updates are emitted when:

- A declaration is added, removed, or modified.
- A backup is created or pruned.
- A divergence check completes.
- The config file is reloaded.

### Performance

- Materialized from SQLite in <50 ms for ≤20 declarations.
- Does NOT trigger fresh divergence checks (those run on demand or via
  schedule). The reported `latest_divergence` is the most recent stored
  result.

## `idlergear://files/critical/{path}/status`

Detailed status for a single declaration, addressed by its `path` (URL-
encoded). Useful when Claude is focused on one critical file (e.g., during a
deprecation flow).

### Returns

```jsonc
{
  "declaration": {
    "path": "fingerprints/*.json",
    "canonical": "hf:marcjon/llmfp-fingerprints",
    "check_cmd": null,
    "auto_backup": true,
    "backup_max": 10,
    "opt_out": false
  },
  "matched_files": [
    "fingerprints/qwen-30b.json",
    "fingerprints/llama-70b.json",
    ...
  ],
  "backups": {
    "total": 12,
    "by_source": [
      {
        "source_path": "fingerprints/qwen-30b.json",
        "count": 3,
        "latest_at": "2026-05-14T13:02:44.123Z"
      },
      ...
    ]
  },
  "divergence_history": [
    {
      "source_path": "fingerprints/qwen-30b.json",
      "checked_at": "2026-05-14T12:00:00.000Z",
      "result": "match",
      "duration_ms": 1840,
      "error_message": null
    },
    ...
  ],
  "recent_audit": [
    {
      "source_path": "fingerprints/qwen-30b.json",
      "operation_type": "edit",
      "attempted_at": "2026-05-14T13:02:43.500Z",
      "outcome": "confirmed",
      "backup_id": "abc123...",
      "reason": null
    },
    ...
  ]
}
```

### Subscribe semantics

Same triggers as the parent resource, scoped to the addressed declaration.

### Error responses

- 404 if `{path}` does not match any declaration (returned as a structured
  error per MCP resource error conventions).

## Resource description (≤200 chars per constitution)

```
idlergear://files/critical: declared critical files with backup counts,
divergence status, and recent audit. Subscribe to monitor protection state.

idlergear://files/critical/{path}/status: detailed status for one
declaration including matched files, backups, divergence history, audit.
```

## Caching and freshness

Both resources are derived from SQLite + the in-memory declaration set. They
are always consistent with the database; no eventual-consistency window.
Divergence checks are *not* triggered on read — they happen on schedule (none
in v0.9) or on explicit `idlergear_file_critical.check` calls or on
`idlergear_doctor` invocations.

## Out of scope for v0.9 (resources deliberately not added)

- `idlergear://files/critical/{path}/backups/{id}` — exposing a specific
  backup as a resource. Out of scope; users restore manually from
  `.idlergear/backups/` in v0.9.
- `idlergear://files/critical/audit?since=...` — paged audit log resource.
  Use `idlergear_file_critical(action="audit", since=...)` instead in v0.9.

# Hook Contracts: Critical File Declarations and Guardrails

**Feature**: 001-critical-files
**Phase**: 1 (Design)

Hooks contributed: **1**. Total hooks delta against v0.9 ceiling of 6: **+1**.

## `ig_pre-tool-use-critical.sh`

A `PreToolUse` hook installed to `.claude/hooks/` by `idlergear install`. It
intercepts Claude Code tool invocations and routes destructive operations
against declared critical files through the elicit-and-confirm flow.

### Installation

Source path: `src/idlergear/hooks/ig_pre-tool-use-critical.sh`
Install target: `.claude/hooks/ig_pre-tool-use-critical.sh`

The hook script is a thin wrapper that delegates to:

```
idlergear hook critical-pre-tool-use --stdin
```

Reading the tool invocation JSON from stdin (per Claude Code hook protocol)
and writing structured output on stdout.

### Hook protocol (input)

Claude Code sends the hook JSON on stdin with the shape it documents for
`PreToolUse`. The relevant fields:

```jsonc
{
  "tool": "Bash" | "Edit" | "Write" | "...",
  "params": { /* tool-specific */ },
  "session_id": "string",
  "client_supports_elicitation": true | false
}
```

### Hook protocol (output)

Exit codes and stdout convey the decision:

| Exit | Stdout | Meaning |
|---|---|---|
| 0 | (any) | Allow the operation to proceed. |
| 1 | error message | Deny the operation; message shown to user/model. |
| 2 | elicitation request JSON | Pause; client elicits confirmation; result determines proceed/deny. |

### Detection logic

For each declaration in the in-memory set, the hook checks:

1. **Bash tool**: if `params.command` matches any of the following destructive
   patterns AND a target-path argument resolves to a declared path:
   - **File ops**: `rm`, `mv` (when destination exists or is a directory
     containing a declared path), `cp -f` / `cp --force`, `cp` whose
     destination exists, `trash`
   - **Shell redirection that overwrites or appends**: `>` and `>>` against
     a declared path
   - **Archive extraction that overwrites**: `tar -x` / `tar --extract` when
     any extracted entry overlaps a declared path
   - **Find-based deletion**: `find ... -delete` or `find ... -exec rm`
   - **In-place stream editing**: `sed -i`, `sed -i.bak` (and variants)
   - **Version-control working-tree overwrites**: `git checkout -- <path>`,
     `git restore <path>`, `git reset --hard`, `git clean -f` / `-fd` /
     `-ffd` / `-xd`
2. **Write tool**: if `params.file_path` matches a declaration AND the file
   exists, treat as overwrite.
3. **Edit tool**: if `params.file_path` matches a declaration, treat as edit
   (always — edits are in-place modifications).

Operations outside this enumerated set are explicitly NOT detected (FR-003).
The quickstart's "What's protected, what isn't" section MUST stay in sync
with this list.

### Behavior on match

1. Resolve effective settings via overlap rules (R10 in `research.md`).
2. If `opt_out == true` (no overlapping protective declaration): exit 0 (allow).
3. If the operation requires a backup AND backup creation fails: exit 1
   (deny) with explanation (FR-017).
4. If `client_supports_elicitation == true`:
   - Emit an elicitation request on stdout (exit 2).
   - Wait for the elicitation result up to `elicitation_timeout_seconds`
     (default 60s, configurable via the top-level
     `elicitation_timeout_seconds` field in `.idlergear/config.toml`; see
     `config-schema.md`).
   - On confirmation: create backup if required, write audit row with
     outcome `confirmed`, exit 0.
   - On cancellation: write audit row with outcome `denied` and reason
     `user_cancel`, exit 1.
   - On timeout (no response within the configured window): write audit
     row with outcome `denied` and reason `timeout`, exit 1 (FR-004).
5. If `client_supports_elicitation == false`:
   - Exit 1 with the FR-016 deny-with-message text:
     `"Operation against declared critical path '<path>' requires confirmation;
     current client does not support interactive confirmation. Override with
     IDLERGEAR_NONINTERACTIVE_POLICY=allow."`

### Audit recording

Every match (regardless of outcome) results in a row in `critical_file_audit`
before the hook returns its decision. This satisfies FR-014 even for denied
operations.

### Performance

- No-declaration case: the hook fast-exits in <5 ms (read config file size,
  see empty `[[critical_files]]`, exit 0).
- With 20 declarations and 100 paths matching: <50 ms median, <200 ms p99.

### Non-interactive override

The environment variable `IDLERGEAR_NONINTERACTIVE_POLICY` controls behavior
when the client doesn't support elicitation:

| Value | Effect |
|---|---|
| (unset) | Deny destructive ops (FR-016 default). |
| `allow` | Allow destructive ops with a warning logged to stderr. |
| `audit-only` | Allow but force a backup regardless of declaration setting. |

This is an explicit opt-in, satisfying FR-016's "MUST require a deliberate
choice."

### Out of scope for v0.9

- Per-tool fine-grained customization of which operations count as
  "destructive."
- Whitelisting specific commit hashes or job IDs as auto-allowed.
- Async/parallel-safe elicitation across multiple simultaneous operations
  (Claude Code sends `PreToolUse` events sequentially per session, so this
  isn't a v0.9 problem).

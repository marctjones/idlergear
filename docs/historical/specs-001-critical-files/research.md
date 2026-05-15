# Research: Critical File Declarations and Guardrails

**Feature**: 001-critical-files
**Phase**: 0 (Outline & Research)
**Date**: 2026-05-14

The spec passed validation with zero `NEEDS CLARIFICATION` markers. Research below
documents the load-bearing design decisions made while drafting the technical
context: each one closes a potential ambiguity that would otherwise surface
during planning. Decisions are recorded with rationale and rejected alternatives
so future amendments can be reasoned about.

## R1: Configuration format and schema

**Decision**: TOML, using arrays of tables (`[[critical_files]]`). Each table
holds `path` (required), `canonical` (optional URI), `check_cmd` (optional
shell command), `auto_backup` (bool, default `true`), `backup_max` (int, default
`10`), and `opt_out` (bool, default `false`).

**Rationale**: TOML is already IdlerGear's configuration format
(`.idlergear/config.toml`). Arrays of tables map cleanly to repeated declarations.
Python stdlib `tomllib` (3.11+) handles parsing — no new dependency.

**Alternatives considered**:

- YAML: more permissive but adds PyYAML dependency and indentation-sensitivity
  bugs are common.
- JSON: lacks comments, which matters here because declarations carry intent
  ("# protect because canonical is in HuggingFace dataset").
- A custom config file under `.idlergear/critical_files.toml`: clean separation
  but inconsistent with how the rest of IdlerGear configures itself.

## R2: Glob matching library

**Decision**: Use `pathspec` (already a transitive dependency for gitignore
handling) for declaration glob matching. Patterns follow gitignore semantics
(supports `**`, leading `/`, etc.).

**Rationale**: gitignore-style patterns are familiar to developers and already
present in the project. Centralising on one matcher avoids subtle semantic
differences between `fnmatch`, `pathlib.PurePath.match`, and `gitignore`.

**Alternatives considered**:

- `fnmatch.fnmatch` from stdlib: no `**` support; users would be surprised when
  `src/**/*.json` doesn't match nested files.
- `pathlib.PurePath.match`: similar limitations.
- Regex: too unfriendly for the typical user.

## R3: Destructive operation detection

**Decision**: Use Claude Code's `PreToolUse` hook, matched on the tool name plus
parameter shape:

- `Bash` with command matching `^\s*(rm|mv|cp\s+-f|trash)\b` against any
  declared path glob.
- `Write` where the target path matches a declaration AND the target file
  already exists.
- `Edit` where the target path matches a declaration (always — edits are
  in-place modifications, qualifying as "destructive" per the spec's definition
  of FR-006).

The hook is implemented as a shell script in `src/idlergear/hooks/` that calls
`idlergear hook critical-pre-tool-use` to do the actual matching, emitting
exit codes that Claude Code interprets per its hook protocol.

**Rationale**: `PreToolUse` is the only Claude Code primitive that can deny or
elicit before the operation runs. Doing this client-side (in a wrapper around
the operation) would require Claude Code to know about IdlerGear's wrapper —
the wrong dependency direction. Doing it in `PostToolUse` is too late (file is
already gone). A filesystem watcher would catch out-of-tool operations (e.g.,
user running `rm` in another terminal) but adds complexity, runs out-of-process,
and is out of scope for a feature focused on AI-assistant-mediated workflows.

**Alternatives considered**:

- Inotify/fswatch filesystem watcher: catches non-CC operations but requires a
  long-running daemon and adds substantial complexity.
- Wrapping `rm`/`mv` via shell aliases: brittle, leaks into the user's shell
  configuration.
- Claude Code permission rules in `settings.json`: can block specific commands
  but lacks the elicit-and-confirm UX and can't see config-driven globs.

## R4: User confirmation mechanism

**Decision**: Use MCP `Elicitation` to request confirmation. The elicitation
includes the operation type, the matched path, the matching declaration, and a
default of `cancel`. If the client doesn't advertise elicitation support, the
hook denies the operation with a clear message explaining how to override.

**Rationale**: Elicitation is the MCP-native primitive for server-initiated
user input. Per Principle III, this is the correct primitive for confirmation
flows. Denying-by-default in non-elicitation clients matches FR-016 (non-
interactive contexts deny).

**Alternatives considered**:

- Hardcoded blocking prompts in the hook script: works only in CLI contexts and
  isn't surfaced consistently across clients.
- Time-based auto-confirm with notification: explicitly rejected — the spec
  requires explicit confirmation, and silent auto-confirm defeats the purpose.
- Permission rules in `.claude/settings.json`: lacks per-operation context.

## R5: Backup storage layout

**Decision**: Flat directory structure:

```
.idlergear/backups/
└── <hash-of-source-path>/
    ├── 2026-05-14T12-30-15.789-edit.json
    ├── 2026-05-14T13-02-44.123-overwrite.json
    └── ...
```

Files are simple copies of the original. The hashed directory groups backups
per source path; filenames carry ISO-8601 timestamps and the triggering
operation type. The path mapping is recorded in the SQLite index for fast
lookup.

**Rationale**: Simple to inspect manually. No restore-time decoding needed.
Plays well with filesystem tools.

**Alternatives considered**:

- Tar archives: compresses but obscures contents from manual inspection.
- Git-style content-addressable store: efficient for unchanged content but
  significant complexity for a feature scope this small.
- Mirror the source-path hierarchy under `.idlergear/backups/`: clearer mental
  model but path-conflict edge cases (file vs. dir at same name) are awkward.

## R6: Audit log storage

**Decision**: SQLite table `critical_file_audit` in `.idlergear/db.sqlite`.
Columns: `id`, `declaration_path`, `source_path`, `operation_type`,
`attempted_at`, `outcome`, `backup_id` (nullable, FK to `critical_file_backup`),
`reason` (nullable).

**Rationale**: SQLite is already the planned data store (per the v0.9 spec).
Audit data is queryable for the doctor command and the status resource.

**Alternatives considered**:

- Append-only JSONL log: simpler to write, harder to query.
- OpenTelemetry events: would re-grow the OTel dependency that v0.9 is shrinking.

## R7: Canonical source check protocol

**Decision**: Command-based interface. The user's `check_cmd` is invoked with
the local file path as its sole argument; exit code 0 means "matches canonical",
non-zero means "diverges or check failed", stderr is captured and surfaced.
Built-in helper scripts ship for common protocols, recognised by URI scheme on
the `canonical` field:

| Scheme | Helper |
|---|---|
| `gh:` | wraps `gh api` to compare blob sha |
| `hf:` | wraps `huggingface-cli` (if installed) |
| `s3://` | wraps `aws s3` (if installed) |
| `https://` | curl + sha256 comparison |

If a scheme has no helper installed, divergence status reports "tool
unavailable" rather than failing the entire status check.

**Rationale**: Command-based is open-ended without coupling IdlerGear to any
specific protocol or SDK. Helpers are convenience, not requirement.

**Alternatives considered**:

- Native HTTP/SDK clients for each protocol: pulls in `boto3`, `huggingface-
  hub`, `PyGithub` — directly contradicts Principle II (don't duplicate OSS
  tools).
- Push the entire check to the user (always require `check_cmd`): higher
  friction; helpers cover the 90% case.

## R8: Non-interactive context detection

**Decision**: A context is "non-interactive" iff the connected MCP client did
not advertise elicitation capability during initialization. The hook records
this state at startup and uses it to choose between `elicit-and-confirm` (deny
default) and `deny-with-message` (FR-016 enforcement).

**Rationale**: This is the most reliable signal available within MCP. Falling
back to stdin/TTY checks is unreliable because MCP servers commonly run with
piped IO regardless of whether a human is present.

**Alternatives considered**:

- Check `sys.stdin.isatty()`: fails because MCP servers communicate via stdio
  with the client, never with the user directly.
- Environment-variable override (`IDLERGEAR_NONINTERACTIVE=1`): retained as an
  explicit opt-in for known automated contexts, but not the primary detection
  mechanism.

## R9: Doctor command integration

**Decision**: Extend the existing `idlergear doctor` CLI subcommand with a
`--scope critical` flag (and include critical-file divergence in the default
`--scope all`). Output is markdown-formatted for terminal use, JSON when
`--json` is passed.

**Rationale**: Doctor already exists in IdlerGear and is the canonical health-
check entry point. Extending rather than creating a new top-level command keeps
the CLI surface from growing.

**Alternatives considered**:

- New `idlergear critical-files status` subcommand: would duplicate doctor's
  purpose.
- Doctor extended only via plugins: out of scope; over-engineered for v0.9.

## R10: Overlapping declaration resolution

**Decision**: When a path matches multiple declarations:

- **Protection**: union — if any matching declaration requires confirmation,
  confirmation is required.
- **Backups**: union — if any matching declaration requires backup, backup is
  created.
- **Retention cap**: maximum across matching declarations.
- **Opt-out**: only applies when no overlapping declaration disables it.

This matches FR-012's "most-protective wins" formulation.

**Rationale**: Predictable to users — overlap can only make protection
stronger, never weaker. Removes a class of foot-guns where a permissive
declaration accidentally weakens a strict one.

**Alternatives considered**:

- "Most specific wins" (longest glob): brittle because path-specificity isn't
  well-ordered for glob patterns.
- "First declaration wins": position-sensitive, surprising.
- Reject overlapping declarations at validation time: too strict; legitimate
  overlap is common (a `*.json` rule plus a `fingerprints/**` rule).

## R11: Configuration reload semantics

**Decision**: mtime-checked between operations, with in-flight snapshot
stability. Each entry point (hook invocation, MCP tool call, MCP resource
read, doctor scope) compares the configuration file's modification time
against the cached value before processing. If the mtime has changed, the
loader re-reads the file and produces a fresh snapshot. Operations already
in flight (a backup write in progress, a divergence check running, an audit
row being recorded) complete using the snapshot they started with;
subsequent operations use the latest.

**Rationale**: simplest semantics that meet SC-001 ("declare → first
blocked op <60s") without polling. Per-entry-point check imposes zero
overhead when the config hasn't changed (a single `os.stat`). Snapshot
stability prevents surprising partial-execution errors when the user is
editing config while operations run. Aligns with Principle V (local-first,
file-mtime is a local-first signal).

**Alternatives considered**:

- Background polling timer: adds a long-running task, surfaces a class of
  threading/concurrency bugs, no benefit over mtime-on-entry.
- Explicit-reload-only: predictable but adds friction; users must remember
  to reload after every config edit.
- mtime + flush-pending cancellation: more surprising mid-backup.
  Operations against just-removed declarations get cancelled with a
  "config-changed" error. Rejected for added complexity with limited UX
  upside.

## R12: Elicitation timeout

**Decision**: server-side timeout with cancel-default. The system enforces
its own timeout on confirmation elicitations (default 60 seconds,
configurable via the top-level `elicitation_timeout_seconds` field). When
the timeout expires before a user response, the operation is denied and
the audit row records reason `timeout`.

**Rationale**: provides predictable behavior across MCP clients that may
have different (or no) elicitation timeouts of their own. 60s default
balances responsiveness with thinking time. Configurable for power users
who want faster or slower cadence. Pairs with FR-016 (non-interactive deny
default): when no human responds quickly, the system treats the prompt as
effectively unattended.

**Alternatives considered**:

- Defer entirely to the client: unpredictable. Some clients have no
  timeout; the hook could wait indefinitely.
- Short fixed timeout (15-30s): better responsiveness, but risks denying
  thoughtful users mid-deliberation on destructive ops.
- Long fixed timeout (5+ min): better for slow sessions but keeps Claude
  blocked.

## Open items deliberately deferred

- **Cross-machine backup consistency**: out of scope per spec assumptions.
- **Encryption of backups**: out of scope; non-adversarial threat model.
- **Restore UI**: out of scope for v0.9; manual file copy from
  `.idlergear/backups/` works.
- **Bulk-declaration import (e.g., from `.gitignore`-style file)**: nice-to-
  have, not needed for v0.9 acceptance.

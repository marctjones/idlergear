# Feature Specification: Critical File Declarations and Guardrails

**Feature Branch**: `001-critical-files`
**Created**: 2026-05-14
**Status**: Draft
**Input**: User description: "F4: Critical file declarations and guardrails. Allow projects to declare critical files (paths, optional canonical source, optional divergence check command) in .idlergear/config.toml. Block or elicit confirmation on destructive operations against declared files. Auto-backup before edits. Surface divergence from canonical sources via idlergear doctor and a status Resource."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare and Protect a Critical Path (Priority: P1)

A developer working on a project has files whose loss or accidental overwrite would
cost hours or days to recover — datasets, generated artifacts, in-flight job
checkpoints, local configuration that isn't in version control. They want to
designate which paths matter and have the tool refuse to delete or overwrite them
without explicit confirmation.

**Why this priority**: this is the irreducible MVP. Without protection on a
declared path, every other feature in this spec is decorative. A user who only
ever gets this story still has tangible protection against the most common
accidental-data-loss scenarios.

**Independent Test**: the user adds an entry to project configuration declaring a
path or glob as critical. They then attempt to delete or overwrite a matching
file. The tool surfaces a confirmation prompt with the operation, the path, and
the option to cancel. Cancelling leaves the file intact. Confirming allows the
operation to proceed.

**Acceptance Scenarios**:

1. **Given** a project with a critical-file declaration matching `fingerprints/*.json`,
   **When** the developer attempts to delete a file matching that pattern,
   **Then** the operation is paused and a confirmation prompt appears identifying the
   path and the operation, with cancel as the default.
2. **Given** the same configuration, **When** the developer reads or lists files
   matching the pattern, **Then** no confirmation is required and the operation
   proceeds normally.
3. **Given** the same configuration, **When** the developer attempts to write a
   new file to a non-existent path covered by the pattern, **Then** no
   confirmation is required (no existing critical content is at risk).
4. **Given** a project with no critical-file declarations, **When** the developer
   performs any operation, **Then** no prompts, latency, or behavior changes
   occur relative to the tool's behavior without this feature.
5. **Given** a declared critical path, **When** any destructive operation against
   it is denied, confirmed, or allowed, **Then** an audit record of the
   operation, path, timestamp, and outcome is persisted and inspectable later.

---

### User Story 2 - Auto-Backup Before Edits (Priority: P2)

The same developer edits a declared critical file (modifies its contents while
preserving the path). They want a prior-state snapshot saved automatically before
the edit applies, so an unsuccessful change can be reversed without re-running
the work that produced the file.

**Why this priority**: edits-in-place are a more frequent and quieter risk than
deletions. Backups also serve as the recovery mechanism if the confirmation prompt
from Story 1 is mistakenly accepted. Without Story 1, backups are still useful;
without Story 2, Story 1 still delivers most of the protection. P2 reflects that
ordering.

**Independent Test**: the user declares a critical path with auto-backup enabled.
They make an edit to a matching file. After the edit, a backup of the prior
contents exists in a known location, timestamped, and is recoverable.

**Acceptance Scenarios**:

1. **Given** a critical-file declaration with auto-backup enabled, **When** the
   developer edits a matching file, **Then** the prior contents are preserved as
   a timestamped backup before the edit applies.
2. **Given** ten consecutive edits to the same critical file with a retention cap
   of ten backups, **When** the eleventh edit applies, **Then** the oldest backup
   is pruned and ten backups remain.
3. **Given** a critical-file declaration with auto-backup explicitly disabled,
   **When** the developer edits a matching file, **Then** no backup is created
   and the edit proceeds normally.
4. **Given** a backup for a critical file, **When** the developer requests
   restoration of the prior version, **Then** the backup contents replace the
   current file contents and the restoration is itself a destructive operation
   subject to Story 1's protection.

---

### User Story 3 - Divergence Visibility for Canonical Sources (Priority: P3)

A developer working with files whose canonical store is external — a remote
dataset, an object-store bucket, an artifact registry — wants to know when their
local copy has drifted from the canonical version. They don't need automatic
synchronization, just visibility: "is what I have right now what the canonical
source has?"

**Why this priority**: without it, the user can still protect against destructive
operations (Story 1) and recover from edits (Story 2). Divergence visibility is
additive — it expands the value of declarations beyond local protection — but
the feature is useful without it. Users without external canonical sources won't
notice its absence.

**Independent Test**: the user declares a critical path with a canonical source
identifier and a divergence-check command. They run the project's status command.
The output reports, for each declared canonical source, whether the local
contents match the canonical version, when the check last ran, and whether the
check completed successfully.

**Acceptance Scenarios**:

1. **Given** a critical-file declaration with a canonical source and an available
   check command, **When** the developer runs the status command, **Then** the
   output reports whether the local file matches the canonical source, with a
   timestamp for when the check was performed.
2. **Given** a critical-file declaration with a canonical source but the check
   command is unavailable (missing tool, network failure), **When** the developer
   runs the status command, **Then** the output reports the failure for that
   declaration without blocking reporting on other declarations.
3. **Given** a critical-file declaration with no canonical source defined, **When**
   the developer runs the status command, **Then** the entry is listed with its
   protection state but the divergence column shows "not configured" rather than
   an error.

---

### Edge Cases

- What happens when a critical-file glob accidentally matches files inside
  `.git/`, `node_modules/`, or other tool-managed directories? (The system MUST
  treat the user's declaration as authoritative but SHOULD warn during
  configuration validation if a declaration matches well-known generated-or-
  tooling paths.)
- What happens when two declarations overlap on the same path with conflicting
  settings (one with backup enabled, one disabled)? (Most-protective wins:
  backups are created; opt-outs require an explicit per-declaration override.)
- What happens when a destructive operation is initiated by an automated process
  with no human present to confirm? (The operation is denied, not allowed by
  default; the user can configure a non-interactive policy explicitly, but it
  MUST require a deliberate choice rather than silent default.)
- What happens when configuration is malformed (invalid TOML, unknown fields)?
  (The system refuses to proceed with operations that would touch critical paths
  and emits a clear configuration error, rather than silently treating zero
  declarations as the state.)
- What happens when the backup directory is full or unwritable? (The destructive
  operation MUST be denied with a clear error; no edit applies without a
  successful backup when auto-backup is required.)

## Clarifications

### Session 2026-05-15

- Q: When `.idlergear/config.toml` has a malformed `[[critical_files]]` block,
  what scope of behavior does "refuse to operate" cover? → A: Component-level
  deny. The system itself MUST continue to start. Only entry points dependent
  on the critical-files configuration (declaration management, status reads,
  destructive-operation interception) MUST return a clear configuration-error
  response. Unrelated system functionality MUST remain available.
- Q: When the system requests confirmation for a destructive operation and the
  user does not respond, what determines the outcome? → A: Server-side timeout
  with cancel-default. The system MUST enforce its own timeout on confirmation
  prompts (default 60 seconds, configurable). After the timeout, the operation
  MUST be denied and the audit record MUST capture the timeout as the reason.
- Q: How aggressively should the hook detect destructive operations beyond the
  obvious file-removal/overwrite set? → A: Best-effort expanded set. The
  detected set MUST include at minimum: file removal, move-with-overwrite,
  force-copy or copy-with-overwrite, trash, shell redirects (`>` and `>>`),
  archive extraction that overwrites declared paths, find-with-delete, in-place
  stream editing (`sed -i`), and version-control operations that overwrite
  working-tree files (`checkout -- <path>`, `restore <path>`, `reset --hard`,
  `clean -fd`), plus tool-mediated edits and overwriting writes. The complete
  enumerated set MUST be documented in the implementation contract;
  operations outside the documented set are explicitly NOT detected, and this
  boundary MUST be visible to users in the quickstart.
- Q: When `.idlergear/config.toml` changes while the system is running, what
  reload semantics apply? → A: mtime-checked between operations with in-flight
  snapshot stability. Each entry point checks config mtime before processing
  and reloads if changed. Operations already in-flight complete using their
  starting snapshot; subsequent operations use the latest configuration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow projects to declare critical files via
  configuration entries containing a path or glob pattern.
- **FR-002**: System MUST allow each declaration to optionally include a
  canonical source identifier and a divergence-check command.
- **FR-003**: System MUST detect destructive operations against paths matching
  any declaration. The detected set MUST include at minimum: file removal,
  in-place edits, overwriting writes, overwriting shell redirection, overwriting
  archive extraction, find-with-delete, in-place stream editing, and
  version-control operations that overwrite working-tree files. The complete
  enumerated set MUST be documented in the implementation contract; operations
  outside the documented set are explicitly NOT detected, and this boundary
  MUST be surfaced to users via the quickstart.
- **FR-004**: System MUST request explicit confirmation from the developer before
  allowing a detected destructive operation to proceed. The system MUST enforce
  a confirmation timeout (default 60 seconds, configurable). If no response is
  received within the timeout, the operation MUST be denied and the audit
  record MUST capture timeout as the reason. Cancel MUST be the default
  outcome of an unattended prompt.
- **FR-005**: System MUST allow non-destructive operations (read, list, status
  inspection) against critical paths without prompting.
- **FR-006**: System MUST create a timestamped backup of a critical file's prior
  contents before any edit applies, unless backups are explicitly disabled for
  that declaration.
- **FR-007**: System MUST cap retained backups per critical file at a configurable
  maximum (default 10) and prune the oldest when the cap is exceeded.
- **FR-008**: System MUST surface, on demand, the divergence status between each
  declared file and its canonical source where a check command is configured.
- **FR-009**: System MUST surface the list of declared critical files and their
  current state through a read-only access path that performs no modifications.
- **FR-010**: System MUST degrade gracefully when canonical-source tooling is
  unavailable, reporting the failure for that declaration without blocking other
  reporting or unrelated operations.
- **FR-011**: System MUST refuse to operate on critical paths when the
  configuration is malformed. Specifically: every critical-files-related entry
  point (declaration management, status reads, destructive-operation
  interception) MUST return a clear configuration-error response. Other system
  functionality unrelated to critical files MUST remain available. The system
  MUST NOT silently treat malformed config as zero declarations.
- **FR-012**: System MUST support overlapping declarations: when multiple matches
  apply, the most-protective settings take effect (backups required if any
  declaration requires them; opt-out applies only when no overlapping declaration
  requires protection).
- **FR-013**: System MUST allow declarations to opt out of auto-backup explicitly,
  and to override the project-wide backup default at the declaration level.
- **FR-014**: System MUST record every blocked-or-confirmed destructive operation
  against a critical file, capturing the operation type, the path, a timestamp,
  and the outcome.
- **FR-015**: System MUST treat the absence of any declarations as a valid
  configuration with zero observable cost on operations against non-declared
  paths.
- **FR-016**: System MUST deny destructive operations when no human confirmation
  is available, unless the project has explicitly configured a non-interactive
  policy.
- **FR-017**: System MUST deny edits when auto-backup is required but cannot
  succeed (e.g., backup directory unwritable, disk full).
- **FR-018**: System MUST detect changes to the critical-files configuration via
  the configuration file's modification time, checked before each
  critical-files entry-point invocation. In-flight operations MUST complete
  using the configuration snapshot under which they started. Operations begun
  after a detected change MUST use the updated configuration.

### Key Entities

- **Critical File Declaration**: a configuration entry comprising a path or glob
  pattern, optional canonical source identifier, optional divergence-check
  command, optional per-declaration backup settings, and optional opt-out flag.
- **Critical File Backup**: a timestamped snapshot of a critical file's prior
  contents, retained on local storage until pruned by the retention cap.
- **Divergence Status**: a per-declaration record indicating whether the local
  file matches its canonical source, when the check last ran, and whether the
  check completed successfully.
- **Critical File Audit Entry**: a record of a destructive operation against a
  declared path, including operation type, path, timestamp, and outcome
  (allowed, denied, confirmed).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can declare a critical file and have a destructive
  operation against it blocked within 60 seconds of writing the declaration.
- **SC-002**: 100% of destructive operations against declared critical paths
  trigger confirmation before applying, across a test suite covering removal,
  overwrite, and replacement scenarios.
- **SC-003**: Across at least 10 backup-and-restore cycles in routine use, zero
  data is lost: each restored state matches its corresponding pre-edit state
  byte-for-byte.
- **SC-004**: A user can determine, in under 10 seconds, whether any declared
  critical file has diverged from its canonical source, given that the check
  command is available.
- **SC-005**: When no critical files are declared, the feature contributes no
  user-perceptible latency or measurable overhead to operations that do not
  touch declared paths.
- **SC-006**: A project that edits a declared critical file daily for 30 days
  retains exactly the retention cap's worth of backups at the end of that
  period, never more.
- **SC-007**: An attempt to perform a destructive operation in a non-interactive
  context without an explicitly-configured non-interactive policy is denied in
  100% of cases, with a clear error message.

## Assumptions

- Users typically declare a small number of critical paths per project (fewer
  than 20); performance against hundreds of declarations is out of scope for
  this release.
- The set of "destructive operations" is stable and conservative: file removal,
  in-place overwrite, replacement. Content edits to a persistent path are
  protected by auto-backup, not by confirmation prompts.
- Canonical sources are referenced by identifier; actually fetching from a
  canonical source is out of scope. This feature reports divergence, it does
  not synchronize.
- The user's environment has the tooling needed to perform any configured
  divergence checks; missing tools produce a graceful error rather than a
  retry or fallback.
- Backups are stored on the same filesystem as the protected files. Cross-machine
  durability of backups is the user's responsibility (mirroring, snapshots).
- This feature operates within a single project tree per invocation; sharing
  declarations across projects is out of scope.
- A "non-interactive context" is defined by the absence of a mechanism for the
  developer to receive and respond to a confirmation prompt within a bounded
  time. The specifics of how this is detected are an implementation concern not
  covered here.
- Encryption, secrets management, and tamper-resistance against malicious
  actors are explicitly out of scope. This feature protects against accidental
  loss by the user themselves, not against adversarial behavior.

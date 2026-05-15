# Implementation Plan: Critical File Declarations and Guardrails

**Branch**: `001-critical-files` | **Date**: 2026-05-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-critical-files/spec.md`

## Summary

Allow IdlerGear projects to declare critical file paths in
`.idlergear/config.toml` (via `[[critical_files]]` blocks). When Claude Code
attempts destructive operations against declared paths, IdlerGear surfaces an
MCP Elicitation requesting confirmation; when edits occur, IdlerGear creates a
timestamped backup first. Divergence against optional canonical sources is
surfaced through `idlergear doctor` and a status MCP Resource. The feature is
zero-overhead when no declarations are present, denies operations in non-
interactive contexts by default, and persists an audit record of every
detected destructive operation.

Technical approach (resolved in Phase 0 research):

- TOML-defined declarations, `pathspec` for glob matching.
- `PreToolUse` Claude Code hook routes matched operations through Elicitation
  (when supported) or denies them with explanation (when not).
- Backups stored as flat copies under `.idlergear/backups/<hash>/<timestamp>`,
  indexed in SQLite.
- Audit and divergence history live in SQLite tables
  (`critical_file_audit`, `critical_file_divergence`).
- Canonical-source checks are command-based (`check_cmd`); built-in helpers
  ship for `gh:`, `hf:`, `s3://`, `https://`, `file://` schemes.

## Technical Context

**Language/Version**: Python 3.11+ (uses stdlib `tomllib`, requires PEP 657
error context).
**Primary Dependencies**: official MCP Python SDK (already a dep), `pathspec`
(already transitive for gitignore), stdlib only otherwise. No new top-level
dependencies for this feature.
**Storage**: SQLite at `.idlergear/db.sqlite` (existing) — three new tables
shipped via migration `001-critical-files.sql`. Filesystem backups under
`.idlergear/backups/`.
**Testing**: pytest with `tmp_path` fixtures for filesystem behavior;
explicit hook-protocol tests asserting exit codes; round-trip tests for
backup + restore. Coverage target: ≥90% for `critical_files/` module.
**Target Platform**: Linux, macOS, Windows (anywhere Claude Code MCP servers
run). Path-handling uses `pathlib` end-to-end for cross-platform safety.
**Project Type**: Single Python library exposing MCP tools + resources +
hook entry points; embedded in the existing IdlerGear MCP server.
**Performance Goals**:
- Hook fast-path (no declarations): <5 ms per `PreToolUse` event.
- Hook hot-path (≤20 declarations, ≤100 matched paths): <50 ms median,
  <200 ms p99.
- Status resource materialization: <50 ms.
- Divergence check: bounded by user's `check_cmd` (30 s timeout).
**Constraints**:
- Non-adversarial threat model (FR boundaries: user error, not malicious
  actors).
- Single-project scope per invocation.
- Backups same-filesystem; durability is user's responsibility.
- ≤20 declarations per project assumed; behavior beyond that is supported
  but not optimised.
- Must work with stdio MCP transport (no out-of-process daemons).
**Scale/Scope**: Solo developer tool. Typical install: 3-5 declarations,
10-50 matched paths, <100 audit entries per week.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.0:

- [x] **Principle I (Three Jobs, No More)**: Maps to Job 3 — "Protect work
      that lives outside git." Direct mapping; no scope creep.
- [x] **Principle II (Compose, Don't Compete)**: Detection via Claude Code
      `PreToolUse` (native primitive). Confirmation via MCP Elicitation
      (native primitive). Backup is filesystem-level. Canonical-source checks
      shell out to user-supplied or built-in helper commands (`gh`, `aws`,
      `curl`, etc.) — no SDK duplication. No shell-command wrapping for its
      own sake.
- [x] **Principle III (MCP Primitives by Role)**: New surface is 1 Tool
      (`idlergear_file_critical`), 2 Resources
      (`idlergear://files/critical`, `.../{path}/status`), 0 Prompts,
      1 Hook script. Confirmation = Elicitation. Status read = Resource.
      State change = Tool. Detection = Hook. All correct.
- [x] **Principle IV (Evidence-Driven Features)**: Direct evidence from
      `IDLERGEAR_V0.9_SPEC.md` (F4 motivated by llmfp's `.partial`
      fingerprints) and from the llmfp session analysis (CLAUDE.md warnings
      against partial-file deletion; canonical store in HF dataset, not git).
      Documented in spec's User Story 1 and Acceptance Scenarios.
- [x] **Principle V (Local-First, Sync-Aware)**: Declarations, backups,
      audit, and divergence history all local. Canonical-source check is
      read-only and degrades gracefully on tool unavailability (FR-010).
      No silent overwrites.
- [x] **Size deltas under v0.9 ceilings**: +1 Tool (of 15), +2 Resources
      (of 8), +0 Prompts (of 6), +1 Hook script (of 6). All comfortably
      below.

**Gate result: PASS — no Constitution Check violations.**

## Project Structure

### Documentation (this feature)

```text
specs/001-critical-files/
├── spec.md                # Feature specification
├── plan.md                # This file
├── research.md            # Phase 0: research decisions
├── data-model.md          # Phase 1: persistent entities
├── quickstart.md          # Phase 1: user-facing walkthrough
├── checklists/
│   └── requirements.md    # Spec quality validation
├── contracts/
│   ├── mcp-tools.md       # MCP tool contracts
│   ├── mcp-resources.md   # MCP resource contracts
│   ├── hooks.md           # PreToolUse hook contract
│   └── config-schema.md   # .idlergear/config.toml schema
└── tasks.md               # Phase 2: created by /speckit-tasks (NOT this command)
```

### Source Code (repository root)

```text
src/idlergear/
├── critical_files/                # New module for this feature
│   ├── __init__.py
│   ├── declarations.py            # TOML parsing, validation, in-memory model
│   ├── matching.py                # Glob matching, overlap resolution
│   ├── backups.py                 # Create, prune, locate backups
│   ├── audit.py                   # SQLite audit writer + query
│   ├── divergence.py              # Run check_cmd + built-in helpers
│   ├── mcp_tools.py               # idlergear_file_critical handler
│   ├── mcp_resources.py           # idlergear://files/critical[*] handlers
│   ├── hook.py                    # CLI entry: `idlergear hook critical-pre-tool-use`
│   └── helpers/                   # Built-in canonical-source check helpers
│       ├── gh.py
│       ├── hf.py
│       ├── s3.py
│       ├── https.py
│       └── file.py
├── hooks/
│   └── ig_pre-tool-use-critical.sh  # Installable PreToolUse hook
├── migrations/
│   └── 001_critical_files.sql     # SQLite schema for new tables
├── doctor.py                      # Extended: --scope critical
└── cli.py                         # Extended: `idlergear hook` subcommand routes

tests/
├── critical_files/
│   ├── test_declarations.py       # TOML parsing, validation, edge cases
│   ├── test_matching.py           # Glob + overlap
│   ├── test_backups.py            # Create, prune, retention
│   ├── test_audit.py              # Audit recording
│   ├── test_divergence.py         # check_cmd protocol, helper integration
│   ├── test_hook.py               # Hook decision tree, exit codes
│   ├── test_mcp_tools.py          # Tool actions
│   ├── test_mcp_resources.py      # Resource materialization
│   └── fixtures/                  # Sample configs, sample files
└── integration/
    └── test_critical_flow.py      # End-to-end: declare → attempt op → confirm
```

**Structure Decision**: Single-project layout with a new `critical_files/`
sub-module inside the existing `src/idlergear/` package. The feature has
clear cohesion (one job, one persistent state owner) and minimal cross-
cutting surface — extending `doctor.py` and `cli.py` is the only outside-the-
module change. No new top-level packages, no new repos.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `list` action overlap between `idlergear_file_critical(action="list")` and the `idlergear://files/critical` Resource | Some MCP clients don't support resource subscription; the tool gives them a one-shot read path. | Forcing all clients to support Resources would block adoption on Goose, older Claude Code versions, etc. Documented in `contracts/mcp-tools.md`. |

No constitution-principle violations. The one entry is a small narrowly-
scoped redundancy noted for transparency.

## Re-evaluation after Phase 1 design

All Constitution Check items remain green:

- Phase 1 surface count is exactly what Phase 0 projected: 1 Tool, 2 Resources,
  1 Hook. No expansion.
- Phase 1 entities (4) are all directly traceable to spec requirements; no
  speculative state added.
- No new external dependencies introduced during Phase 1.
- Storage decisions (SQLite + flat backup files) match Principle V (local-
  first).

**Re-evaluation result: PASS.**

## Open questions for `/speckit-tasks`

None blocking. The following are deliberately deferred to v0.10 and should
NOT generate tasks here:

- `idlergear_file_critical.restore` action (manual cp suffices in v0.9).
- Audit log retention/vacuum.
- Cross-machine backup mirroring.
- Bulk-import declarations from `.gitignore`-style files.

`/speckit-tasks` should:

1. Generate tasks grouped by User Story (Story 1 = MVP / P1, Story 2 = P2,
   Story 3 = P3) per the constitution's testing discipline.
2. Treat tests as REQUIRED for: declarations (TOML parsing, validation),
   matching (glob, overlap), backups (create, prune, retention cap), hook
   (decision tree, exit codes), audit (round-trip), MCP tool actions, and
   the end-to-end integration flow. These all fall under the constitution's
   "hooks and their side effects" / "critical-file guardrails" categories.
3. Treat tests as OPTIONAL for: divergence helper scripts (`gh.py`, `hf.py`,
   etc.) — pure shell-out adapters.
4. Mark `[P]` parallelism aggressively within a story (different files, no
   sequential dependencies); models before services before MCP handlers
   within each story.

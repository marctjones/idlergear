<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0
Type: MAJOR (initial ratification establishing core governance and principles)

Modified principles: N/A (initial draft)

Added sections:
  - Core Principles (5)
  - Operational Constraints
  - Development Workflow
  - Governance

Removed sections: N/A

Templates examined for alignment:
  - .specify/templates/plan-template.md ✅ (Constitution Check gate present; no edits needed — gates are defined in this constitution under Governance > Constitution Check)
  - .specify/templates/spec-template.md ✅ (no constitution-driven sections; alignment OK)
  - .specify/templates/tasks-template.md ✅ (TDD discipline is OPTIONAL in template; reconciled via Principle V which requires tests only for specific layers — see Operational Constraints)
  - .specify/templates/checklist-template.md ✅ (no edits)
  - .specify/templates/constitution-template.md ✅ (this file's source; left untouched)

Templates requiring updates: none

Follow-up TODOs:
  - TODO(RUNTIME_GUIDANCE_SYNC): the project's CLAUDE.md and README.md still describe the pre-redesign IdlerGear (vision, plans, tasks, 200+ tools). These will be reconciled to the v0.9 scope during the Week 9 documentation phase. The constitution intentionally supersedes those docs (see Governance).
  - TODO(SUPERSEDED_DOCS): UX_REDESIGN_PLAN.md and REDESIGN_IMPLEMENTATION_ORDER.md are superseded by IDLERGEAR_V0.9_SPEC.md and this constitution. They will be moved to docs/historical/ or deleted in Week 9.
-->

# IdlerGear Constitution

## Core Principles

### I. Three Jobs, No More

IdlerGear exists to do exactly three jobs:

1. Make Claude Code fluent in the GitHub Issues workflow.
2. Track long-running work across sessions.
3. Protect work that lives outside git.

Every feature MUST map cleanly to one of these jobs. Features that serve none are
out of scope and MUST be rejected during specification, regardless of how appealing
they sound in isolation. Features that serve multiple jobs are preferred over features
that serve only one. The "platform" framing of pre-v0.9 IdlerGear is explicitly
retired; growth happens by deepening these three jobs, not by adding new ones.

**Rationale**: prior IdlerGear accumulated ~230 tools across vision/plan/notes/files/
git/tmux/containers/observability/multi-agent coordination. Most overlapped with
Claude Code natives, Spec Kit, or `gh`/`git`/`docker` themselves. Scope discipline
is the single highest-leverage change in the v0.9 redesign.

### II. Compose, Don't Compete

IdlerGear MUST NOT duplicate functionality available in:

- **Claude Code natives**: filesystem (Read/Edit/Write/Glob/Grep), background
  execution (`run_in_background`, Monitor), task management (TaskCreate/Update/List),
  hooks, skills, subagents, memory, plan mode, LSP, WebFetch/Search, worktrees.
- **GitHub Spec Kit**: the spec → clarify → plan → tasks → implement workflow.
  Project constitution, feature specifications, implementation plans live in
  `.specify/`, not in IdlerGear's data store.
- **Established OSS**: `gh` CLI for GitHub API transport, `git` for VCS operations,
  `tmux`/`docker`/`podman` for process and container management, `pytest` and
  `coverage.py` for testing, `mkdocs`/`sphinx`/`pdoc` for documentation.

When extending these tools is needed, prefer MCP hooks, Resources, Prompts, and
Sampling over reimplementation. A new IdlerGear tool whose entire body shells out
to an existing CLI MUST be rejected — Claude can call the CLI directly via Bash.

**Rationale**: the audit of llmfp sessions showed 80+ tools whose only value was
"shell command, in JSON." This wastes context, fragments the user's mental model,
and adds maintenance burden. The redesign deletes ~120 of the 230 prior tools.

### III. MCP Primitives by Role

Each piece of functionality MUST use the correct MCP primitive:

- **Resources** (`idlergear://...`): read-only data the model can subscribe to —
  project context, issue context, file annotations, sync status, job state.
- **Prompts** (`/`-invocable templates): user-controlled workflows — `/start`,
  `/work-on`, `/handoff`, `/standup`.
- **Tools**: state-modifying actions only. Reading data via a tool when a Resource
  would suffice is a violation.
- **Elicitation**: confirmation flows. Destructive operations on critical files,
  promotion of session tasks to persistent tasks, "this looks like a duplicate"
  prompts.
- **Sampling**: server-requested LLM generation. Pre-work briefs, auto-generated
  file annotations, `/handoff` summaries.
- **Roots**: project boundary detection. Use over custom heuristics where supported.

The v0.9 target ceiling is **~10 Tools, ~7 Resources, ~5 Prompts**. Exceeding any
ceiling requires a justified Complexity Tracking entry in the relevant feature
plan.

**Rationale**: the official MCP specification defines distinct primitives because
they have distinct caching, subscription, and user-control semantics. Conflating
them (e.g., "everything is a tool") wastes context and degrades UX.

### IV. Evidence-Driven Features

Every feature in IDLERGEAR_V0.9_SPEC.md and successors MUST be tied to observed
friction. Acceptable evidence sources:

- Session transcript analysis (e.g., the llmfp study identifying batch-job
  lifecycle as a P0 gap).
- Explicit user request with documented use case.
- Recurring support questions or confusion patterns.

Speculative features ("users might want...", "in case of...") MUST be deferred to
a future release until evidence accumulates. Each feature spec MUST include an
"out of scope" section and the project MUST maintain an explicit anti-features
list — features that look attractive but actively harm scope discipline.

Anti-features for v0.9 include: comprehensive activity dashboards/TUIs, multi-AI-
tool coordination daemons, container/process management, wiki integration beyond
linking, AI state reporting/telemetry to a separate observer, Linear/Jira adapters,
OpenTelemetry collection beyond a single query helper.

**Rationale**: prior IdlerGear shipped features ("AI state reporting", multi-agent
daemon, vector code search) whose evidence base was theoretical. Each carried real
maintenance cost. Evidence requirements prevent this drift.

### V. Local-First, Sync-Aware

All IdlerGear state MUST be stored locally:

- Structured data in `.idlergear/db.sqlite` (single file).
- Knowledge graph in `.idlergear/graph.db` (Kuzu).
- Critical-file backups in `.idlergear/backups/`.
- Cached issue/PR/project data in the SQLite cache.

GitHub is treated as canonical for shared state (issues, PRs, project boards,
custom fields). Synchronization between local and canonical MUST be:

- **Bidirectional** where both sides can mutate state.
- **Conflict-surfacing** — divergence is reported, never silently overwritten.
- **Explicit** — sync runs on schedule and on demand; the user can always force
  push or force pull with explicit intent.

IdlerGear MUST work offline against the local cache (read-only operations) and
MUST degrade gracefully when `gh auth` is missing.

**Rationale**: solo developers and air-gapped contexts need offline operation.
Teams need conflict resolution that doesn't silently destroy work. Both
constraints push toward local-first with explicit sync.

## Operational Constraints

**Size ceilings (v0.9):**

- Total LOC including tests: ≤ 5,000.
- MCP Tools: ≤ 15.
- MCP Resources: ≤ 8.
- MCP Prompts: ≤ 6.
- Hook scripts shipped to `.claude/hooks/`: ≤ 6.
- Subagents shipped to `.claude/agents/`: ≤ 2.

**Technology stack (v0.9):**

- Language: Python 3.11+.
- Storage: SQLite (data), Kuzu (graph).
- GitHub transport: `gh` CLI (no native HTTP client).
- MCP SDK: official Python MCP SDK.
- Tests: pytest, coverage.py.

**Testing discipline:** TDD is NOT mandatory for all code. Tests ARE required for:

- Hooks and their side effects.
- Bidirectional sync logic (round-trip correctness, conflict cases).
- Critical-file guardrails (destructive operation detection).
- Graph queries used by quality gates.

Tests are NOT required for pure data transforms, formatting helpers, or thin CLI
wrappers. The tasks template's "Tests are OPTIONAL" language is reconciled by this
constraint.

**Dependency stance:**

- Prefer the standard library and the existing dependency set.
- New dependencies require a justified entry in the feature plan's Complexity
  Tracking section.
- Heavy ML/vector dependencies (torch, chromadb, sentence-transformers) MUST be
  optional and lazily loaded. The OOM_FIXES.md history is non-negotiable: vector
  search remains opt-in.

**Backwards compatibility:**

- Tools deleted in v0.9 SHOULD emit deprecation warnings during v0.9.x and be
  removed in v1.0.
- Data formats (SQLite schema, graph schema, config TOML) follow semver:
  - PATCH: additive, optional fields.
  - MINOR: additive, with migration scripts.
  - MAJOR: structural changes with migration scripts and a documented upgrade
    path.

## Development Workflow

**Spec Kit drives the feature lifecycle.** Every non-trivial feature MUST flow
through:

1. `/speckit-specify` — authored from the v0.9 spec (or new evidence for
   post-v0.9 features).
2. `/speckit-clarify` (optional but recommended for ambiguous specs).
3. `/speckit-plan` — implementation plan with Constitution Check gate.
4. `/speckit-tasks` — dependency-ordered task list.
5. `/speckit-implement` — execution.

Spec artifacts live in `.specify/specs/{NNN-feature-name}/`. They are the source
of truth for feature scope and replace ad-hoc planning docs.

**Dogfooding requirement:** each v0.9 feature MUST be used in the development of
v0.9 itself for at least one week before the v0.9 release is tagged. If a feature
cannot be dogfooded (e.g., it depends on an external trigger that doesn't occur
naturally), this MUST be documented and the feature requires explicit user
acceptance testing.

**Issue-driven work:** Once Feature 2 (task ↔ issue sync) is operational,
substantive work on v0.9 MUST be tracked via GitHub Issues linked to IdlerGear
tasks. Sessions that produce ≥5 tool calls and ≥2 file edits without an issue
linkage are eligible for the session-task promotion flow.

**Critical files declared up front:** before any feature implementation work, the
v0.9 critical files MUST be declared in `.idlergear/config.toml`:
`.idlergear/db.sqlite`, `.idlergear/graph.db`, `.specify/memory/constitution.md`,
and any other file whose loss would block development.

## Governance

**Authority:** the constitution supersedes all earlier IdlerGear planning
documents, including but not limited to UX_REDESIGN_PLAN.md,
REDESIGN_IMPLEMENTATION_ORDER.md, and MCP_BEST_PRACTICES_ANALYSIS.md. Where those
documents conflict with this constitution, this constitution wins. Where they
provide useful detail (OOM_FIXES.md, parts of MCP_BEST_PRACTICES_ANALYSIS.md not
contradicted here), they remain reference material until reconciled.

**Constitution Check (used by plan-template.md):** every `/speckit-plan`
invocation MUST verify, before completing Phase 0:

- [ ] The feature maps to one of the three jobs in Principle I.
- [ ] The feature does not duplicate Claude Code, Spec Kit, or OSS functionality
      (Principle II).
- [ ] Each new tool/resource/prompt uses the correct MCP primitive (Principle III).
- [ ] The feature is backed by documented evidence (Principle IV).
- [ ] State changes respect local-first, sync-aware semantics (Principle V).
- [ ] Size deltas do not push the project over the v0.9 ceilings.

Violations MUST be recorded in the plan's Complexity Tracking section with
justification and a rejected simpler alternative. Unjustified violations block
plan approval.

**Amendments:**

- Patch (typo, clarification, non-semantic rewording): no review required;
  increment patch version.
- Minor (new principle, expanded guidance, new section): documented rationale in
  Sync Impact Report; bump minor version; update dependent templates if needed.
- Major (principle removed or redefined, governance change): documented rationale,
  migration plan for affected features and in-flight specs; bump major version.

All amendments MUST update the Sync Impact Report at the top of this file and
propagate to dependent templates as listed in the report.

**Compliance review:** each PR that touches `src/idlergear/` or `.specify/`
MUST link to its originating `.specify/specs/{NNN-feature-name}/` spec and plan,
and the PR description MUST confirm the Constitution Check gates passed.

**Version**: 1.0.0 | **Ratified**: 2026-05-14 | **Last Amended**: 2026-05-14

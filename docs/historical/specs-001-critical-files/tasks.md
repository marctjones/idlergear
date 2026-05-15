---

description: "Task list for Critical File Declarations and Guardrails (F4)"
---

# Tasks: Critical File Declarations and Guardrails

**Input**: Design documents from `/specs/001-critical-files/`
**Prerequisites**: plan.md ✅, spec.md ✅ (clarified 2026-05-15), research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Tests ARE REQUIRED for this feature per the constitution's Operational Constraints (hooks and side effects; critical-file guardrails). Helper adapters in `helpers/*.py` are pure shell-outs covered by the divergence-protocol tests rather than dedicated unit tests.

**Organization**: Tasks grouped by user story (US1 / US2 / US3) per the spec's P1/P2/P3 priorities. Each story is independently testable and independently shippable.

**Changes from previous tasks.md** (2026-05-15 regeneration): absorbs four spec clarifications — FR-003 expanded detection set, FR-004 elicitation timeout, FR-011 component-level config-invalid scope, FR-018 mtime-checked reload with in-flight snapshot stability. One new task added in Phase 2 (T013); descriptions tightened across hook/test/resource tasks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different file, no dependency on incomplete prior task in this phase.
- **[Story]**: `[US1]`, `[US2]`, `[US3]` — maps to spec user stories.
- File paths are absolute-from-repo-root.

## Path conventions

- Single Python project layout.
- New module: `src/idlergear/critical_files/`.
- Tests: `tests/critical_files/` (unit) + `tests/integration/test_critical_*.py` (end-to-end).
- Migrations: `src/idlergear/migrations/`.
- Installed assets (hooks/skills): `src/idlergear/hooks/`, `src/idlergear/skills/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Module skeleton and test scaffolding.

- [ ] T001 Create module skeleton `src/idlergear/critical_files/__init__.py` exporting the planned public surface (declarations, matching, backups, audit, divergence, mcp_tools, mcp_resources, hook, events) plus a `load_or_raise` helper used by every entry point
- [ ] T002 [P] Create test package `tests/critical_files/__init__.py` and `tests/critical_files/conftest.py` providing common fixtures: tmp_path-based config dir, sample SQLite db, isolated `.idlergear/` per test, mtime-mockable clock
- [ ] T003 [P] Create `tests/critical_files/fixtures/` with sample TOML configs (valid, malformed, with overlaps, with opt-out, with elicitation_timeout_seconds override) and dummy critical files for matching tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, parsing, matching, audit, the config-error gate, and the in-process event bus. Every user story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Create migration `src/idlergear/migrations/001_critical_files.sql` with `critical_file_backup`, `critical_file_divergence`, `critical_file_audit` tables and indexes per `data-model.md`
- [ ] T005 [P] Migration test `tests/critical_files/test_migration.py` — asserts all three tables, all indexes, and `schema_migrations` row exist after migration applied
- [ ] T006 Wire `001_critical_files.sql` into the existing IdlerGear migration runner (apply on MCP server startup if not yet applied; idempotent)
- [ ] T007 [P] Implement `src/idlergear/critical_files/declarations.py` — TOML loader using stdlib `tomllib`, `CriticalFileDeclaration` dataclass, validation per `data-model.md` rules (FR-001, FR-002, FR-011, FR-012, FR-013, FR-015), plus mtime tracking and `load_or_raise(config_path)` that returns a snapshot or raises `ConfigInvalidError` (FR-011, FR-018)
- [ ] T008 [P] Test declarations `tests/critical_files/test_declarations.py` — happy-path parsing, every validation rule, malformed-TOML rejection (FR-011), unknown-field rejection, opt_out+auto_backup warning, mtime-changed reload semantics, snapshot immutability (FR-018), elicitation_timeout_seconds field accepted at top-level
- [ ] T009 [P] Implement `src/idlergear/critical_files/matching.py` — pathspec-backed glob matcher, overlap resolution per R10 (most-protective wins)
- [ ] T010 [P] Test matching `tests/critical_files/test_matching.py` — single-glob match, recursive `**`, overlap (protection union), opt-out neutralised by overlapping protective declaration, well-known-path warning (`.git/**` etc.)
- [ ] T011 [P] Implement `src/idlergear/critical_files/audit.py` — SQLite writer and query helpers for `critical_file_audit`, `AuditEntry` dataclass per `data-model.md`, supports `reason` field for `timeout` (FR-004), `non_interactive_deny` (FR-016), `config_invalid` (FR-011), `user_cancel` (FR-004)
- [ ] T012 [P] Test audit `tests/critical_files/test_audit.py` — round-trip insert+query, outcome enum coverage (`allowed`/`denied`/`confirmed`), FR-014 always-logged invariant, reason taxonomy
- [ ] T013 [P] Implement `src/idlergear/critical_files/events.py` — minimal in-process event bus: publishers (declarations.reload, backups.create/prune, divergence.record_result, audit.write) and subscribers (resources subscribe semantics in T038). No filesystem watcher; pure in-process notifications

**Checkpoint**: Foundation ready. User stories can now proceed.

---

## Phase 3: User Story 1 — Declare and Protect a Critical Path (Priority: P1) 🎯 MVP

**Goal**: Declare a path as critical; destructive operations against it require explicit confirmation within the configured timeout. Audit log captures every detection. Malformed config never silently degrades.

**Independent Test**: Add a `[[critical_files]]` entry. Attempt `rm` (or `sed -i`, `git checkout --`, etc.) against a matching file. See confirmation prompt with cancel as default and the configured timeout. Cancelling preserves the file. Confirming proceeds. No response within timeout denies and records audit reason "timeout." Audit row written in every case. Malformed config returns `config_invalid` at every critical-files entry point while leaving unrelated IdlerGear features working.

### Tests for User Story 1 (write FIRST; ensure they fail before implementation)

- [ ] T014 [P] [US1] Hook decision-tree test `tests/critical_files/test_hook.py` covering:
  - Detection of the full FR-003 set: `rm`, `mv` overwriting, `cp -f` / `cp` overwriting, `trash`, shell redirects `>` and `>>`, `tar -x` extracting over a declared path, `find ... -delete`, `sed -i`, `git checkout -- <path>`, `git restore <path>`, `git reset --hard`, `git clean -fd`, Write against existing path, Edit
  - Non-detection of read-only ops (`cat`, `ls`, `wc`, `grep`) — exit 0 quietly
  - Elicitation request emission when client advertises capability (exit 2 + JSON)
  - Elicitation cancel-default after 60s timeout (FR-004) — exit 1 with audit reason `timeout`
  - Configurable timeout — verify `elicitation_timeout_seconds = 15` from fixture config is honoured
  - Non-interactive deny path (FR-016 default) — exit 1 with audit reason `non_interactive_deny`
  - `IDLERGEAR_NONINTERACTIVE_POLICY=allow` — exit 0 with stderr warning and audit recorded
  - `IDLERGEAR_NONINTERACTIVE_POLICY=audit-only` — exit 0 but forces a backup attempt regardless of declaration setting
  - Config invalid → exit 1 with structured `config_invalid` error to stdout (FR-011)
  - mtime change between calls triggers reload; in-flight call retains snapshot (FR-018)
- [ ] T015 [P] [US1] MCP tool test `tests/critical_files/test_mcp_tools.py` — `idlergear_file_critical` actions `declare`/`undeclare`/`list`/`audit`, error envelopes (`invalid_path`, `not_found`, `config_invalid`), config-file round-trip after declare, FR-011 verification: actions return `config_invalid` envelope on malformed config without taking partial effect
- [ ] T016 [P] [US1] Integration test `tests/integration/test_critical_protect.py` — full flow exercising US1 acceptance scenarios 1-5: declared `fingerprints/*.json`, attempt delete → elicit → cancel → file intact; non-destructive read → no prompt; new-path Write → no prompt; no-declaration state → zero-overhead; audit row present for every detection; SC-001 verified by declaring a file then attempting an op within 60s and seeing protection take effect; malformed-config injection causes `config_invalid` everywhere while other IdlerGear tools still work

### Implementation for User Story 1

- [ ] T017 [P] [US1] Implement `src/idlergear/critical_files/hook.py` — CLI entry routed via `idlergear hook critical-pre-tool-use --stdin`. Reads PreToolUse JSON on stdin; calls `declarations.load_or_raise` and catches `ConfigInvalidError` to emit `config_invalid` (FR-011); checks config mtime first to satisfy FR-018; applies the full FR-003 detection set (Bash regex covers the expanded ops; tool-name + parameter shape covers Edit/Write); writes elicitation request or exit-1 message to stdout per `contracts/hooks.md`; returns appropriate exit code
- [ ] T018 [P] [US1] Implement `src/idlergear/critical_files/mcp_tools.py` — `idlergear_file_critical` handler with `declare`/`undeclare`/`list`/`audit` action branches per `contracts/mcp-tools.md`. Each action wraps `declarations.load_or_raise` and returns a `config_invalid` envelope on `ConfigInvalidError` (FR-011). `declare`/`undeclare` write to TOML atomically (write-and-rename); `list` shares the loader with hook.py
- [ ] T019 [US1] Register the `idlergear_file_critical` tool in `src/idlergear/mcp_server.py` with the description per `contracts/mcp-tools.md` (≤200 chars per constitution Principle III)
- [ ] T020 [P] [US1] Create installable hook script `src/idlergear/hooks/ig_pre-tool-use-critical.sh` — thin shell wrapper delegating to `idlergear hook critical-pre-tool-use --stdin`, sets exit codes per Claude Code's hook protocol
- [ ] T021 [US1] Extend `src/idlergear/install.py` to copy `ig_pre-tool-use-critical.sh` into `.claude/hooks/` on `idlergear install` and register it in `.claude/settings.json` PreToolUse list (idempotent; respects existing entries)
- [ ] T022 [US1] In `hook.py`: emit elicitation request (exit 2 + JSON) when client advertises elicitation capability; enforce 60s default timeout (configurable via `elicitation_timeout_seconds` in `.idlergear/config.toml`); on timeout return exit 1 with audit reason `timeout`; on user cancel return exit 1 with reason `user_cancel` (FR-004)
- [ ] T023 [US1] In `hook.py`: honour `IDLERGEAR_NONINTERACTIVE_POLICY` env var with values `allow` / `audit-only` per `contracts/hooks.md` (deliberate opt-in satisfies FR-016); deny-by-default when unset and client lacks elicitation capability
- [ ] T024 [US1] Centralise declaration loading: ensure `hook.py`, `mcp_tools.py`, and the resource handlers (Phase 5) all use `declarations.load_or_raise` from T007; mtime check happens at each entry to enable post-declare protection within 60s (SC-001, FR-018)

**Checkpoint**: US1 is functional and shippable. The MVP for F4 is reachable here.

---

## Phase 4: User Story 2 — Auto-Backup Before Edits (Priority: P2)

**Goal**: Edits to a declared critical file create a timestamped backup of prior contents before applying. Pruning respects the retention cap. Backup-creation failure denies the edit.

**Independent Test**: Declare a path with `auto_backup = true`. Edit a matching file. Confirm a timestamped backup exists with prior contents. Make 11 edits with `backup_max = 10`; confirm pruning to exactly 10 backups.

### Tests for User Story 2 (write FIRST)

- [ ] T025 [P] [US2] Backup tests `tests/critical_files/test_backups.py` — create_backup happy path; prune with retention caps 0/1/N; FR-017 (deny edit when backup creation fails); FR-007 (oldest pruned); SC-006 (cap respected after long sequences)
- [ ] T026 [P] [US2] Integration test `tests/integration/test_critical_backup.py` — US2 acceptance scenarios 1-4: edit creates backup, 11 edits prune to 10, auto_backup=false skips, restore is itself a destructive op

### Implementation for User Story 2

- [ ] T027 [P] [US2] Implement `src/idlergear/critical_files/backups.py` — `create_backup`, `prune`, `locate_backups`, with hashed-source-path directory layout per R5; pruning ordered by `created_at`; publishes `backup.created` and `backup.pruned` events to the bus from T013
- [ ] T028 [US2] In `hook.py`: when Edit is detected against a declared path AND `auto_backup=true` for the effective declaration, call `backups.create_backup` before exit 0. Index the new backup in `critical_file_backup` table
- [ ] T029 [US2] In `hook.py`: if `create_backup` raises (disk full, dir unwritable), return exit 1 with FR-017 error message; do NOT proceed with the edit
- [ ] T030 [US2] Extend `mcp_tools.py:list` action to include backup counts per declaration in its output (depends on T027's `locate_backups`)
- [ ] T031 [US2] In `hook.py`: when a backup is created during a confirmed/auto edit, set `backup_id` on the audit row (cross-references audit.py from T011); also handle the `IDLERGEAR_NONINTERACTIVE_POLICY=audit-only` case which forces a backup regardless of declaration setting

**Checkpoint**: US2 is functional. Together with US1, the protection-and-recovery story is complete.

---

## Phase 5: User Story 3 — Divergence Visibility for Canonical Sources (Priority: P3)

**Goal**: When a declaration has a `canonical` source, the user can see whether the local file matches it. Built-in helpers cover `gh:`/`hf:`/`s3://`/`https://`/`file://` schemes. Missing tools degrade gracefully.

**Independent Test**: Declare a path with a `canonical` URI and an available `check_cmd` (or built-in helper). Run `idlergear doctor --scope critical`. Output reports `match`/`diverge`/`error`/`not_configured` per declaration with timestamps.

### Tests for User Story 3 (write FIRST)

- [ ] T032 [P] [US3] Divergence tests `tests/critical_files/test_divergence.py` — `check_cmd` protocol (exit 0/1/2/other), 30s timeout enforcement, stderr capture into `error_message`, missing-helper graceful degradation per FR-010
- [ ] T033 [P] [US3] Doctor extension test `tests/critical_files/test_doctor_extension.py` — `--scope critical` runs all checks, `--json` emits structured output, missing-helper does not block reporting of other declarations, FR-011 verification (malformed config produces a structured config-invalid section without crashing other doctor scopes)
- [ ] T034 [P] [US3] MCP resources test `tests/critical_files/test_mcp_resources.py` — shape of `idlergear://files/critical`, shape of `idlergear://files/critical/{path}/status`, subscribe-update triggers driven by the events bus (T013) on declarations.reload, backups.create/prune, divergence.record_result; 404 on unknown path; FR-011 verification (config_invalid returned as structured resource payload, not as a transport error)
- [ ] T035 [P] [US3] Integration test `tests/integration/test_critical_divergence.py` — US3 acceptance scenarios 1-3: declared canonical + available check → match/diverge correctly reported; unavailable check → per-declaration error without blocking others; no canonical → `not_configured`

### Implementation for User Story 3

- [ ] T036 [P] [US3] Implement `src/idlergear/critical_files/divergence.py` — `check_cmd` runner with `subprocess.run(timeout=30)`, exit-code-to-result mapping, stderr capture, persistence to `critical_file_divergence`; publishes `divergence.record_result` events to the bus from T013
- [ ] T037 [P] [US3] Implement built-in helpers in `src/idlergear/critical_files/helpers/`: `gh.py` (`gh api` blob-sha compare), `hf.py` (`huggingface-cli` wrap), `s3.py` (`aws s3` ETag compare), `https.py` (curl + sha256), `file.py` (stdlib `filecmp`). Each is a small standalone script callable from `divergence.py` when a recognised scheme is detected
- [ ] T038 [P] [US3] Implement `src/idlergear/critical_files/mcp_resources.py` — `list_resources` registration + handlers for `idlergear://files/critical` and `idlergear://files/critical/{path}/status` per `contracts/mcp-resources.md`; subscribe semantics implemented via the in-process events bus from T013; entry points wrap `declarations.load_or_raise` and surface `config_invalid` in the resource payload (FR-011)
- [ ] T039 [US3] Register the two resources in `src/idlergear/mcp_server.py` (depends on T038)
- [ ] T040 [P] [US3] Extend `src/idlergear/doctor.py` — add `--scope critical` mode iterating declarations, invoking `divergence.run_check` per declaration, formatting results for terminal and `--json` outputs; include in default `--scope all` when declarations exist (FR-008, FR-010, SC-004); on `ConfigInvalidError` emit a structured config-invalid section, do not abort other scopes (FR-011)
- [ ] T041 [US3] Extend `mcp_tools.py` with `check` action handler wired to `divergence.run_check`; returns `result`/`checked_at`/`duration_ms`/`error_message` per `contracts/mcp-tools.md`
- [ ] T042 [P] [US3] Wire the `idlergear-canonical-check` skill into `idlergear install`: copy `src/idlergear/skills/idlergear-canonical-check/` to `.claude/skills/idlergear-canonical-check/` on install; covered by an installer-level test asserting the destination exists post-install

**Checkpoint**: US3 is functional. All three stories deliverable. F4 complete and dogfoodable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Performance verification, documentation reconciliation, and end-to-end validation.

- [ ] T043 [P] Performance benchmark `tests/critical_files/test_perf.py` — assert:
  - Hook latency: <5ms with zero declarations (SC-005); <50ms median, <200ms p99 with 20 declarations × 100 matched paths
  - `idlergear_file_critical(action="list")` returns in <5ms with zero declarations
  - `idlergear://files/critical` resource materialises in <50ms with ≤20 declarations
  - `idlergear doctor --scope critical` no-ops in <10ms with zero declarations
- [ ] T044 [P] Update `CLAUDE.md` to document the `[[critical_files]]` config block, link to `idlergear-canonical-check` skill, and remove any pre-redesign references that conflict with F4 (partial Week-9 reconciliation per constitution Sync Impact Report TODO)
- [ ] T045 [P] Update `README.md` to mention F4 and link to `specs/001-critical-files/quickstart.md`
- [ ] T046 Final integration sweep `tests/integration/test_critical_full.py` — runs US1+US2+US3 sequentially in a single project tree, verifies no cross-test pollution (independent tmp paths, fresh SQLite per test, no leaked backup directories); also verifies FR-018 mtime reload across stories (add a declaration mid-test, verify subsequent ops see it within 60s)
- [ ] T047 [P] Verify no v0.9 tool surface budget violations — script asserting `idlergear_file_critical` is the only new tool from F4 and confirms current totals are still within 15/8/6/6 ceilings (Constitution Principle III)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: No dependencies. Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup. BLOCKS all user stories. Phase 2 now includes T013 (events bus) so US3's subscribe semantics have a foundation in place.
- **User Stories (Phase 3-5)**: Each depends on Foundational. Stories are independent of each other and can ship in any order after Foundational, but the natural order is P1 → P2 → P3.
- **Polish (Phase 6)**: Depends on all stories the team intends to ship.

### Within-phase dependencies

- **Phase 2**: T004 → T006 (migration sql before runner wiring). T005/T008/T010/T012 [P] are independent test files. T007/T009/T011/T013 [P] are independent implementation files.
- **Phase 3 (US1)**: Tests (T014/T015/T016) [P] FIRST. Then T017/T018/T020 [P] (independent files). T019 depends on T018. T021 depends on T020. T022/T023/T024 depend on T017 (same file). Note T024 also touches T018, but lands inside `declarations.load_or_raise` from T007 so cross-file coupling is minimal.
- **Phase 4 (US2)**: Tests (T025/T026) FIRST. Then T027 [P]. T028/T029/T031 depend on T027 and edit `hook.py` (sequential, same file). T030 depends on T027 and edits `mcp_tools.py`.
- **Phase 5 (US3)**: Tests (T032-T035) [P] FIRST. T036/T037/T038 [P] independent. T039 depends on T038. T040 [P] depends on T036. T041 depends on T036 and edits `mcp_tools.py`. T042 [P] is install-time.

### Parallel opportunities

- **Phase 1**: T002 and T003 in parallel.
- **Phase 2**: T005/T007/T008/T009/T010/T011/T012/T013 all in parallel after T004; T006 is the only serial task in this phase.
- **Phase 3 (US1)**: All three tests T014/T015/T016 in parallel; then T017/T018/T020 in parallel; rest serial.
- **Phase 4 (US2)**: T025/T026 in parallel; T027 standalone; T028/T029/T031 must serialize (same file).
- **Phase 5 (US3)**: All four tests T032-T035 in parallel; then T036/T037/T038/T040/T042 in parallel; rest mostly serial.
- **Cross-story**: After Phase 2, three developers (or three subagent tracks) could work US1/US2/US3 in parallel since stories are independent. Realistic for this feature: one developer ships sequentially.

### Parallel example: Phase 2 Foundational

```bash
# After T004 (migration sql) + T006 (runner wiring) complete:
Task: "Test migration in tests/critical_files/test_migration.py"
Task: "Implement declarations.py with TOML loader, validation, mtime tracking, load_or_raise"
Task: "Test declarations.py with all validation rules and reload semantics"
Task: "Implement matching.py with pathspec + overlap resolution"
Task: "Test matching.py with single/recursive/overlap/opt-out cases"
Task: "Implement audit.py SQLite writer with reason taxonomy"
Task: "Test audit.py round-trip and outcome/reason enums"
Task: "Implement events.py minimal in-process bus"
```

---

## Implementation Strategy

### MVP first (US1 only) — Week 1 of F4 development

1. Phase 1: Setup (T001-T003) — half a day.
2. Phase 2: Foundational (T004-T013) — 1-2 days. Now includes the events bus and the config-error gate.
3. Phase 3: US1 (T014-T024) — 2-3 days.
4. **STOP**. Run `tests/integration/test_critical_protect.py`. Verify the quickstart end-to-end manually with several destructive ops from the expanded FR-003 set.
5. Dogfood: declare `.idlergear/db.sqlite`, `.idlergear/graph.db`, and `.specify/memory/constitution.md` as critical files in this repo per the constitution's Development Workflow section. Use for 1 week.

After 1 week of dogfooding, decide whether to proceed to US2/US3 or revise based on observed friction (e.g., elicitation timeout duration, false positives in the expanded detection set).

### Incremental delivery

1. Setup + Foundational → foundation ready.
2. Add US1 → test independently → dogfood → demo (MVP).
3. Add US2 → test independently → dogfood → demo.
4. Add US3 → test independently → dogfood → demo.
5. Phase 6 polish → tag F4 complete in v0.9.

Each story adds value without breaking previous stories. F4 can be tagged after any story checkpoint if priorities shift.

---

## Notes

- `[P]` = different file, no dependency on incomplete prior task in this phase.
- `[Story]` = `[US1]`/`[US2]`/`[US3]`, mapping to spec user stories.
- Constitution requires tests for hooks, sync logic, and critical-file guardrails — F4 falls in those categories. **Tests-first within each story phase is mandatory.**
- Helpers in `src/idlergear/critical_files/helpers/*.py` are pure shell-out adapters; their behavior is exercised by T032 (divergence-protocol tests) rather than dedicated unit tests.
- Verify tests fail before implementing within each user story phase.
- Commit after each task or logical group (per Constitution Governance).
- Stop at any checkpoint to validate story independently.
- Avoid: vague tasks, same-file conflicts in parallel groups, cross-story dependencies that break independence.

### Out-of-band documentation updates required after implementation

The spec clarifications added on 2026-05-15 imply downstream contract updates that are NOT tasks (contracts are plan-time artifacts, not implementation work). These should be hand-patched before or during implementation:

1. `contracts/hooks.md` — extend "Detection logic" to enumerate the full FR-003 set (sed -i, tar -x, find -delete, git overwriting ops); add a "Confirmation timeout" subsection describing the 60s default and `elicitation_timeout_seconds` config knob.
2. `contracts/config-schema.md` — add a top-level `elicitation_timeout_seconds` field documentation.
3. `research.md` — append R11 (config reload semantics per FR-018) and R12 (elicitation timeout per FR-004) for future maintainers.

These are 5-10 minutes of editing total and should be done before T014 (hook test) so the test author can read them as authoritative.

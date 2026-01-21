---
id: 1
title: 'Design: Test Awareness Enhancements (idlergear test)'
created: '2026-01-17T16:44:41.202459Z'
updated: '2026-01-17T16:44:41.202489Z'
---
---
name: ig-test
title: Test Awareness Enhancements (idlergear test)
state: active
created: '2026-01-11T08:29:58.654702Z'
---
# Implementation Plan: Test Awareness Enhancements

## Current State

The core `idlergear test` functionality is **already implemented** (v0.3.28):

### Implemented Features ✅
- `idlergear test detect` - Framework detection (pytest, cargo, dotnet, jest, vitest, go, rspec)
- `idlergear test status` - Show cached last run results
- `idlergear test run` - Run tests, parse output, cache results
- `idlergear test history` - View test run history
- `idlergear test list` - Enumerate tests in project
- `idlergear test coverage` - Map source files to test files
- `idlergear test uncovered` - List files without tests
- `idlergear test changed` - Run only tests for changed files
- `idlergear test sync` - Import results from external test runs
- `idlergear test staleness` - Check if results are stale

### MCP Tools ✅
All 10 test-related MCP tools are implemented:
- `idlergear_test_detect`, `idlergear_test_status`, `idlergear_test_run`
- `idlergear_test_history`, `idlergear_test_list`, `idlergear_test_coverage`
- `idlergear_test_uncovered`, `idlergear_test_changed`
- `idlergear_test_sync`, `idlergear_test_staleness`

---

## Remaining Enhancements

Based on design note #35, the following integrations are proposed:

### Phase 1: Doctor Integration

Add test-related health checks to `idlergear doctor`:

**Checks to add:**
1. "Tests haven't been run in 24 hours" - Warn about stale test results
2. "New source files without test coverage" - Check for uncovered files
3. "Last test run had failures" - Remind about failing tests
4. "External test runs detected" - Suggest syncing results

**Implementation:**
- Add checks to `src/idlergear/doctor.py`
- Use existing `testing.py` functions: `get_last_result()`, `get_uncovered_files()`, `check_external_test_runs()`

### Phase 2: Watch Mode Integration

Enhance watch mode to be test-aware:

**Suggestions to add:**
1. "You modified `foo.py` but haven't run tests" - Detect code changes without test runs
2. "Tests for changed files: `test_foo.py`" - Show which tests to run
3. "Test coverage gap: new file `bar.py` has no tests" - Detect new uncovered files

**Implementation:**
- Modify `src/idlergear/watch.py` to check test staleness
- Add test-related suggestions to watch output

### Phase 3: Task Integration

Add test tracking to tasks:

**Features:**
1. `--needs-tests` flag on task create - Mark tasks that require test coverage
2. Track which tasks have associated test commits
3. Warn on task close if no tests were added

**Implementation:**
- Add optional `needs_tests` field to task metadata
- Track test file changes in commits linked to tasks

### Phase 4: Hook Integration

Add test reminders to hooks:

**Pre-commit hook:**
- Warn if committing code changes without running tests
- Block commit if tests are failing (optional, configurable)

**Post-tool-use hook:**
- After file modifications, remind about relevant tests

**Implementation:**
- Enhance existing hooks in `src/idlergear/hooks/`
- Add `test.require_before_commit` config option

---

## Files to Modify

**Phase 1:**
- `src/idlergear/doctor.py` - Add test health checks

**Phase 2:**
- `src/idlergear/watch.py` - Add test-aware suggestions

**Phase 3:**
- `src/idlergear/tasks.py` - Add needs_tests field
- `src/idlergear/cli.py` - Add --needs-tests flag

**Phase 4:**
- `src/idlergear/hooks/ig_pre-commit.sh` - Add test checks
- `src/idlergear/config.py` - Add test hook config

---

## Success Criteria

1. `idlergear doctor` reports test health issues
2. `idlergear watch` suggests running tests after code changes
3. Tasks can be marked as needing tests
4. Pre-commit hooks can optionally enforce test runs

---

## Priority Assessment

| Phase | Value | Effort | Priority |
|-------|-------|--------|----------|
| 1. Doctor | High | Low | **High** |
| 2. Watch | Medium | Medium | Medium |
| 3. Task | Low | Medium | Low |
| 4. Hooks | Medium | High | Low |

**Recommendation:** Start with Phase 1 (Doctor Integration) as it provides immediate value with minimal effort.

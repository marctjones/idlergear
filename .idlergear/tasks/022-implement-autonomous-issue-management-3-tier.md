---
id: 22
title: 'Implement autonomous issue management (3-tier: prompting, automatic, AI-initiated)'
state: open
created: '2026-01-03T06:07:16.123172Z'
labels:
- enhancement
- 'effort: large'
- 'component: daemon'
- core-v1
priority: high
---
## Summary

Implement three levels of autonomous issue management: (1) Enhanced prompting for Claude to proactively create tasks, (2) Automatic task creation based on heuristics, (3) Daemon-initiated AI sessions for complex analysis.

## Problem

**Current state:**
- ✅ Claude can create tasks when explicitly told
- ✅ CLAUDE.md provides guidance, but Claude doesn't always follow it (~40% compliance)
- ❌ No automatic task creation (test failures, TODO comments)
- ❌ No daemon-initiated AI sessions for background analysis
- ❌ No automatic task updates when progress is made

**Opportunities missed:**
- Test failures don't auto-create bug tasks
- Git commits with `#42` don't auto-update task #42
- Code analysis opportunities aren't captured
- Large commits aren't reviewed for follow-up work

## Proposed Solution: Three-Tier Hybrid System

### Level 1: Enhanced Prompting (Improve Claude Compliance)

**Goal:** Increase Claude's proactive task creation from ~40% to 80%+

**Implementation:**
1. Strengthen CLAUDE.md with MANDATORY directives
2. Add PostToolUse hook to detect patterns and prompt Claude:
   - Test failures → "Create bug task"
   - Large edits (>5 files) → "Create progress note"
   - TODO comments → "Create tech-debt task"
3. Add Stop hook to prompt for knowledge capture

**Cost:** Free (uses existing Claude session)  
**Reliability:** Medium (depends on Claude following prompts)  
**Quality:** High (Claude has full context)

### Level 2: Automatic Heuristics (Guaranteed Execution)

**Goal:** Auto-create/update tasks for obvious patterns

**Auto-create tasks:**
```python
# Test failure → Bug task
on_test_failure(log):
    idlergear task create \
        f"Fix failing test: {extract_test_name(log)}" \
        --label bug --label auto-created

# TODO comment in diff → Tech-debt task
on_todo_in_diff(file, line, text):
    idlergear task create \
        f"{text}" \
        --body "File: {file}:{line}" \
        --label technical-debt --label auto-created
```

**Auto-update tasks:**
```python
# Git commit with "Fix #42" → Update task #42
on_commit(message, files):
    task_ids = extract_task_refs(message)  # Finds #42
    for id in task_ids:
        idlergear task update id \
            --body-append f"\n\nCommit: {hash}\nFiles: {files}"
```

**Cost:** Free  
**Reliability:** High (guaranteed)  
**Quality:** Medium (no context, might be noisy)

### Level 3: Daemon-Initiated AI Sessions (Revolutionary)

**Goal:** Background AI analysis for complex situations

**How it works:**
1. Daemon detects event needing AI judgment (large commit, ambiguous failure)
2. Daemon spawns **headless Claude session** via API or CLI
3. Claude analyzes with full context, creates tasks if warranted
4. Session terminates, results persisted

**Use cases:**
- **Test failure analysis:** "These 3 tests failed. Should we create separate tasks or one umbrella task?"
- **Large commit review:** "15 files changed. Any follow-up tasks needed for testing/docs?"
- **Opportunity detection:** "12 occurrences of manual JSON parsing. Worth refactoring?"

**Example:**
```python
# Daemon detects test failure
daemon.ask_claude(f"""
Test failed: {logs}

Context: {idlergear context}

Should we create a task? If yes, create it with appropriate details.
Respond JSON: {{"action": "create_task|none", "reasoning": "..."}}
""")

# Claude analyzes and creates task if needed
```

**Cost:** Paid (API calls), user-configurable quota  
**Reliability:** High (guaranteed to analyze)  
**Quality:** High (Claude judgment with context)

## Implementation Plan

### Phase 1: Enhanced Prompting (Quick Win)
- [ ] Update CLAUDE.md with stronger "MANDATORY" directives
- [ ] Add PostToolUse hook for test failure detection
- [ ] Add PostToolUse hook for large edit detection
- [ ] Add Stop hook for knowledge capture prompt
- [ ] Measure Claude compliance rate (target: 80%+)

### Phase 2: Simple Automation (Low-Hanging Fruit)
- [ ] Implement test failure → bug task automation
- [ ] Implement git commit #42 ref → task update
- [ ] Implement TODO in diff → tech-debt task
- [ ] Add configuration: `autonomous.auto_create_on = ["test_failure", "todo_comment"]`
- [ ] Add label "auto-created" for all automated tasks
- [ ] Add user notification option

### Phase 3: Daemon-Initiated AI (Advanced)
- [ ] Research: Can Claude Code run headless? (`claude --headless`?)
- [ ] Alternative: Use Anthropic API directly for background sessions
- [ ] Implement daemon orchestrator (spawn session, send prompt, parse result)
- [ ] Add sandboxing (read-only FS except .idlergear/, timeout, token limit)
- [ ] Add user approval workflow (optional)
- [ ] Add usage quota (max sessions per hour/day)
- [ ] Add notification system (desktop, email)

## Configuration

```toml
# .idlergear/config.toml
[autonomous]
enabled = true

# Level 1: Prompting
enhance_prompts = true  # Add contextual hints to Claude

# Level 2: Automatic
auto_create_on = [
    "test_failure",
    "todo_comment",
    "build_failure"
]
auto_update_on = [
    "git_commit_with_task_ref"  # "Fix #42" updates task 42
]

# Level 3: AI Sessions
ai_sessions_enabled = false  # Disabled by default (costs money)
ask_claude_on = [
    "test_failure_ambiguous",   # Complex failures
    "large_commit",              # >10 files changed
    "opportunity_detected"       # Code smells
]
max_sessions_per_hour = 5
require_user_approval = true  # Prompt before spawning AI
notification_method = "desktop"
```

## Comparison Matrix

| Feature | Level 1: Prompting | Level 2: Automatic | Level 3: AI Sessions |
|---------|-------------------|-------------------|---------------------|
| **Reliability** | Medium (~80% if prompted well) | High (100%) | High (100%) |
| **Context** | High (Claude has full session) | None (heuristics) | High (Claude analyzes) |
| **Quality** | High (Claude judgment) | Medium (might be noisy) | High (Claude judgment) |
| **Speed** | Slow (waits for user's Claude) | Instant | Medium (spawns session) |
| **Cost** | Free | Free | Paid (API) |
| **User Control** | High (Claude can ask user) | Medium (config on/off) | High (approval workflow) |

## Use Cases

### Use Case 1: Test Suite Fails
**Event:** `pytest tests/` exits with 3 failures

**Level 1 Response (Prompting):**
- Hook adds context to Claude: "3 tests failed. Create bug tasks."
- Claude creates 3 tasks (if it follows prompt)

**Level 2 Response (Automatic):**
- Daemon immediately creates 3 tasks:
  - "Fix failing test: test_login"
  - "Fix failing test: test_logout"
  - "Fix failing test: test_refresh_token"
- All labeled `bug`, `auto-created`

**Level 3 Response (AI Session):**
- Daemon spawns headless Claude
- Claude analyzes failure logs + project context
- Claude determines: "All 3 failures from same root cause (auth refactor)"
- Claude creates 1 umbrella task: "Fix auth tests after OAuth2 refactor"
- Links to current task #42: "Implement OAuth2"

### Use Case 2: Large Commit (15 files)
**Event:** `git commit` with 15 files changed

**Level 1 Response:**
- No action (Claude not actively watching)

**Level 2 Response:**
- Daemon creates note: "Large commit detected: 15 files changed in abc123"

**Level 3 Response:**
- Daemon asks Claude: "Analyze this commit, any follow-up tasks?"
- Claude creates:
  - Task: "Add integration tests for OAuth2 flow"
  - Task: "Update API documentation for new endpoints"
  - Note: "Refactor looks good, follows existing patterns"

### Use Case 3: Code Opportunity
**Event:** Daemon's code analyzer detects 12 manual JSON parse blocks

**Level 1 Response:**
- No action

**Level 2 Response:**
- Auto-create: "Refactoring opportunity: 12 manual JSON parse blocks"

**Level 3 Response:**
- Claude analyzes code context
- Claude decides: "Worth refactoring, used in critical path"
- Creates task: "Refactor JSON parsing to safe_json_parse() utility"
- Includes code locations and migration plan

## Benefits

**Level 1 (Enhanced Prompting):**
- ✅ Improves Claude compliance without new infrastructure
- ✅ Free, simple to implement
- ✅ User still in control (Claude can ask)

**Level 2 (Automatic):**
- ✅ Guaranteed execution, no reliance on AI
- ✅ Instant feedback
- ✅ Works 24/7, even when Claude isn't running

**Level 3 (AI Sessions):**
- ✅ Best of both worlds: guaranteed + intelligent
- ✅ Background analysis without blocking user's Claude
- ✅ High-quality tasks with context

## Open Questions

1. **Claude Code headless mode?**
   - Does `claude` CLI support `--headless` or API mode?
   - If not, use Anthropic API directly?

2. **User notification preferences?**
   - Always notify on auto-created tasks?
   - Summary digest (daily/weekly)?
   - Only notify on AI-initiated sessions?

3. **Quality control?**
   - Review queue before publishing auto-tasks?
   - Allow user to approve/reject?
   - Learn from user feedback?

4. **Cost management?**
   - Level 3 uses API calls - who pays?
   - Hard limits (budget, tokens)?
   - Opt-in only?

## Related Issues

- #95 - Proactive task creation (merged into this issue as acceptance criteria)
- #112 - Watch mode (provides events for Level 2)
- #19 - Daemon prompt queue (infrastructure)
- #66 - Unified daemon architecture

## Acceptance Criteria

**From #95 (Proactive Task Creation):**
- [ ] Claude creates tasks without explicit "create a task" instruction
- [ ] Claude creates notes when discovering behaviors/quirks
- [ ] Claude updates existing tasks when making progress
- [ ] CLAUDE.md rules enforced via hooks and prompts

**Phase 1 (Prompting):**
- [ ] CLAUDE.md updated with MANDATORY directives
- [ ] PostToolUse hook detects test failures, adds prompt
- [ ] Stop hook prompts for knowledge capture
- [ ] Claude compliance measured at 80%+

**Phase 2 (Automatic):**
- [ ] Test failures auto-create bug tasks
- [ ] Git commit `Fix #42` auto-updates task #42
- [ ] TODO comments in diffs auto-create tech-debt tasks
- [ ] User can configure which automations to enable
- [ ] All auto-tasks labeled `auto-created`

**Phase 3 (AI Sessions):**
- [ ] Daemon can spawn headless Claude session (or use API)
- [ ] Sessions sandboxed (limited permissions, timeout)
- [ ] User approval workflow (if enabled)
- [ ] Usage quota enforced (max N sessions per hour)
- [ ] User notified of autonomous actions
- [ ] Works for test failures, large commits, opportunities

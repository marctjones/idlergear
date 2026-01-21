---
id: 1
title: Autonomous Issue Management and Daemon-Initiated AI Sessions
created: '2026-01-03T06:06:13.806992Z'
updated: '2026-01-03T06:06:13.807009Z'
---
# Autonomous Issue Management and Daemon-Initiated AI Sessions

## Current State

### What IdlerGear Does Today

**Reactive (user/Claude-initiated):**
- ✅ Claude can create tasks when explicitly told: "create a task for this bug"
- ✅ Claude *should* proactively create tasks (via CLAUDE.md guidance) but doesn't always
- ✅ Hooks can **remind** Claude to use IdlerGear (UserPromptSubmit hook)
- ✅ Hooks can **block** forbidden files (PreToolUse hook)

**What's Missing:**
- ❌ No automatic issue creation based on heuristics
- ❌ No autonomous issue updates based on progress
- ❌ No daemon-initiated Claude Code sessions
- ❌ No "ask Claude in background" capability

## The Vision: Three Levels of Autonomy

### Level 1: Proactive Prompting (Partially Implemented)

**Status:** ~60% implemented via hooks and CLAUDE.md

**How it works:**
- Claude Code makes a change
- Hook detects pattern (e.g., test failure, TODO comment)
- Hook **prompts** Claude to create task
- Claude decides whether to create task

**Example:**
```bash
# PostToolUse hook detects test failure
if echo "$TOOL_RESPONSE" | grep -q "FAILED"; then
    cat <<EOF
{
  "additionalContext": "Test failure detected. Create a task:
  idlergear task create 'Fix failing test' --label bug"
}
EOF
fi
```

**Limitations:**
- Relies on Claude following suggestion
- Claude might ignore the prompt
- Not truly autonomous

### Level 2: Automatic Issue Management (Not Yet Implemented)

**Status:** ❌ Not implemented

**How it would work:**
- Daemon monitors file changes, test results, git commits
- Daemon **automatically creates/updates** tasks based on heuristics
- No Claude involvement required

**Examples:**

#### Auto-Create Task on Test Failure
```python
# In daemon's LogWatcher
def on_test_failure(log_path, failure_message):
    """Automatically create task when test fails."""
    task = idlergear_task_create(
        title=f"Fix failing test: {extract_test_name(failure_message)}",
        body=f"Test failed with:\n{failure_message}",
        labels=["bug", "auto-created"]
    )
    print(f"Auto-created task #{task['id']}")
```

#### Auto-Update Task on Git Commit
```python
# In daemon's commit watcher
def on_commit(commit_message, changed_files):
    """Update tasks mentioned in commit message."""
    # Extract task references: "Fix #42: handle null values"
    task_ids = extract_task_refs(commit_message)
    
    for task_id in task_ids:
        idlergear_task_update(
            task_id,
            body_append=f"\n\nCommit: {commit_hash}\nFiles: {changed_files}"
        )
```

#### Auto-Create Task on Code Analysis
```python
# In watch mode
def on_file_modified(file_path):
    """Analyze code changes for issues."""
    diff = git_diff(file_path)
    
    # Detect TODO comments added
    todos = extract_todos(diff)
    for todo in todos:
        idlergear_task_create(
            title=todo['description'],
            body=f"File: {file_path}:{todo['line']}\n{todo['context']}",
            labels=["technical-debt", "auto-created"]
        )
```

**Pros:**
- ✅ Guaranteed execution (no reliance on Claude)
- ✅ Immediate feedback
- ✅ Works 24/7 even when Claude isn't running

**Cons:**
- ❌ No context/judgment (might create low-quality tasks)
- ❌ Might create noise (too many auto-tasks)
- ❌ No natural language understanding

### Level 3: Daemon-Initiated Claude Sessions (Revolutionary)

**Status:** ❌ Not implemented, requires significant architecture

**How it would work:**
- Daemon detects situation needing AI judgment
- Daemon **spawns a headless Claude Code session**
- Daemon sends prompt to Claude
- Claude analyzes and creates/updates tasks
- Session terminates, results persisted

**Architecture:**

```
┌─────────────────────────────────────────┐
│      IdlerGear Daemon                   │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ Event Detection                   │  │
│  │ - Test failure                    │  │
│  │ - Large commit                    │  │
│  │ - Code smell detected             │  │
│  └─────────────┬─────────────────────┘  │
│                │                         │
│                ▼                         │
│  ┌───────────────────────────────────┐  │
│  │ Should Ask Claude?                │  │
│  │ - Heuristics: complexity > 3/10   │  │
│  │ - Context matters                 │  │
│  │ - User preference                 │  │
│  └─────────────┬─────────────────────┘  │
│                │ YES                     │
│                ▼                         │
│  ┌───────────────────────────────────┐  │
│  │ Spawn Headless Claude Session     │  │
│  │ - No UI, background process       │  │
│  │ - Sandboxed environment           │  │
│  │ - Limited permissions             │  │
│  └─────────────┬─────────────────────┘  │
│                │                         │
│                ▼                         │
│  ┌───────────────────────────────────┐  │
│  │ Send Prompt via stdin             │  │
│  │ "Test failed: [logs]. Should we   │  │
│  │  create a task? If yes, create it.│  │
│  │  Context: [idlergear context]"    │  │
│  └─────────────┬─────────────────────┘  │
│                │                         │
│                ▼                         │
│  ┌───────────────────────────────────┐  │
│  │ Claude Analyzes                   │  │
│  │ - Reads logs                      │  │
│  │ - Checks context                  │  │
│  │ - Creates task if warranted       │  │
│  └─────────────┬─────────────────────┘  │
│                │                         │
│                ▼                         │
│  ┌───────────────────────────────────┐  │
│  │ Capture Result                    │  │
│  │ - Task created?                   │  │
│  │ - Task ID                         │  │
│  │ - Reasoning                       │  │
│  └─────────────┬─────────────────────┘  │
│                │                         │
│                ▼                         │
│  ┌───────────────────────────────────┐  │
│  │ Persist & Notify                  │  │
│  │ - Store in .idlergear/auto-tasks/ │  │
│  │ - Notify user (optional)          │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Example Use Cases:**

#### Use Case 1: Test Failure Analysis
```bash
# Daemon detects test failure
# Spawns headless Claude session with prompt:

"The test suite failed with the following errors:

<errors>
FAILED tests/test_auth.py::test_login - AssertionError: 401 != 200
FAILED tests/test_auth.py::test_logout - AttributeError: 'NoneType' object has no attribute 'id'
</errors>

Context from idlergear:
- Current task: #42 'Implement OAuth2 flow'
- Recent changes: Modified auth.py, session.py

Should tasks be created for these failures? If yes, create them with appropriate labels and context."

# Claude analyzes, creates tasks:
# Task #117: Fix login test failure (401 vs 200)
# Task #118: Fix logout NoneType error
# Both linked to #42 as blockers
```

#### Use Case 2: Large Commit Review
```bash
# Daemon detects commit with 15+ files changed
# Spawns Claude session with prompt:

"A large commit was just made with 15 files changed:

<commit>
Message: Refactor authentication system
Files:
- src/auth.py (234 lines changed)
- src/session.py (189 lines changed)
- src/middleware.py (new file, 156 lines)
...
</commit>

<diff>
[Abbreviated diff of key changes]
</diff>

Questions:
1. Should follow-up tasks be created for testing/documentation?
2. Are there any code smells or technical debt introduced?
3. Does this align with the current plan?

Current plan: [idlergear plan show]

Please analyze and create any necessary tasks."

# Claude creates:
# Task #119: Add integration tests for OAuth2 flow
# Task #120: Document new middleware configuration
# Note: "Authentication refactor looks solid, follows existing patterns"
```

#### Use Case 3: Opportunity Detection
```bash
# Daemon's code analyzer detects repeated pattern
# Spawns Claude with prompt:

"Code analysis detected a repeated pattern that could be refactored:

<pattern>
Location: src/utils.py, src/handlers.py, src/middleware.py
Pattern: Manual JSON serialization with error handling
Occurrences: 12

Example:
try:
    data = json.loads(content)
except json.JSONDecodeError as e:
    logger.error(f"JSON parse error: {e}")
    return None
</pattern>

This appears to be a refactoring opportunity. Should we:
1. Create a task to refactor into a utility function?
2. Ignore (acceptable duplication)?
3. Create a note for future consideration?

Analyze and decide."

# Claude creates:
# Task #121: Refactor JSON parsing into safe_json_parse() utility
```

**Implementation Requirements:**

1. **Headless Claude Execution**
```bash
# Can we run Claude Code without UI?
claude --headless --prompt "..." --project /path/to/project

# Or via API?
curl -X POST localhost:9000/claude/execute \
    -d '{"prompt": "...", "project": "/path"}'
```

2. **Sandboxing & Permissions**
- Limited filesystem access (read-only except .idlergear/)
- No network access (except IdlerGear MCP)
- Time limit (max 60 seconds)
- Resource limits (max 100k tokens)

3. **Daemon Orchestration**
```python
class DaemonClaudeOrchestrator:
    def __init__(self):
        self.active_sessions = {}
        self.max_concurrent = 2  # Limit parallel sessions
    
    async def ask_claude(self, prompt: str, context: dict) -> dict:
        """Spawn headless Claude session with prompt."""
        session_id = str(uuid4())
        
        # Build full prompt with context
        full_prompt = f"""
        {await self.load_context()}
        
        {prompt}
        
        Respond with JSON:
        {{
            "action": "create_task|update_task|create_note|none",
            "reasoning": "...",
            "details": {{...}}
        }}
        """
        
        # Spawn Claude session
        process = await asyncio.create_subprocess_exec(
            'claude', '--headless', '--prompt', full_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for response (with timeout)
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60
            )
        except asyncio.TimeoutError:
            process.kill()
            return {"error": "timeout"}
        
        # Parse response
        response = json.loads(stdout)
        
        # Execute action if needed
        if response['action'] == 'create_task':
            task = self.create_task(**response['details'])
            response['task_id'] = task['id']
        
        return response
```

4. **User Control & Preferences**
```toml
# .idlergear/config.toml
[autonomous]
enabled = true  # Master switch

# When to ask Claude automatically
ask_claude_on = [
    "test_failure",
    "large_commit",  # >10 files
    "code_smell",
    "opportunity_detected"
]

# Restrictions
max_sessions_per_hour = 5
max_concurrent_sessions = 2
require_user_approval = false  # If true, prompt user first

# Notification
notify_on_auto_task = true
notification_method = "desktop"  # or "email", "none"
```

## Comparison: Three Levels

| Feature | Level 1: Prompting | Level 2: Automatic | Level 3: Daemon-Initiated AI |
|---------|-------------------|-------------------|------------------------------|
| **Reliability** | Low (Claude might ignore) | High (guaranteed) | High (guaranteed) |
| **Context Awareness** | High (Claude has full context) | Low (heuristics only) | High (Claude analyzes) |
| **Quality** | High (Claude judgment) | Medium (might be noisy) | High (Claude judgment) |
| **Speed** | Slow (waits for Claude) | Fast (immediate) | Medium (spawns session) |
| **User Control** | High (Claude asks user) | Medium (configurable rules) | High (can require approval) |
| **Implementation** | Simple (hooks + prompts) | Medium (event detection) | Complex (headless Claude) |
| **Cost** | Free (user's Claude session) | Free | Paid (API calls) |

## Recommended Approach: Hybrid

**Combine all three levels:**

### Tier 1: Simple Heuristics (Level 2)
Auto-create tasks for obvious cases:
- Test failures (create bug task)
- TODO comments in commits (create tech-debt task)
- Build failures (create bug task)

**No AI needed, instant, free.**

### Tier 2: AI Prompting (Level 1)
Prompt Claude when it's active:
- Large commits (suggest review)
- Code smells detected (suggest refactoring)
- Opportunities identified (suggest task)

**Uses existing Claude session, no cost.**

### Tier 3: Background AI (Level 3)
Ask Claude in background for complex cases:
- Ambiguous test failures (needs analysis)
- Large refactoring opportunities (needs judgment)
- Architecture decisions (needs context)

**Only when needed, user can disable, limited quota.**

## Implementation Roadmap

### Phase 1: Enhanced Prompting (Level 1)
- [ ] Strengthen CLAUDE.md guidance on proactive behavior
- [ ] Add PostToolUse hook to detect test failures
- [ ] Add Stop hook to prompt for knowledge capture
- [ ] Add metrics to track Claude's compliance rate

### Phase 2: Simple Automation (Level 2)
- [ ] Auto-create tasks on test failures
- [ ] Auto-update tasks on git commits (extract #42 refs)
- [ ] Auto-create tasks on TODO comments in diffs
- [ ] Add user controls (enable/disable per event type)

### Phase 3: Background AI Sessions (Level 3)
- [ ] Research headless Claude Code execution
- [ ] Implement daemon session spawner
- [ ] Add sandboxing & resource limits
- [ ] Add user approval workflow
- [ ] Add usage quotas & rate limiting
- [ ] Add notification system

## Open Questions

1. **Can Claude Code run headless?**
   - Does `claude` CLI support `--headless` or API mode?
   - Alternative: Use Anthropic API directly (not Claude Code)

2. **User consent & control?**
   - Always notify user when daemon creates tasks?
   - Require approval before spawning AI sessions?
   - Daily/weekly summary of autonomous actions?

3. **Cost management?**
   - If using Anthropic API, who pays?
   - How to limit usage (tokens, sessions, cost)?

4. **Security & sandboxing?**
   - How to prevent daemon-spawned Claude from doing dangerous things?
   - Read-only filesystem except .idlergear/?
   - No network access?

5. **Quality control?**
   - How to prevent low-quality auto-created tasks?
   - Review queue before publishing?
   - Machine learning to improve heuristics?

## Related Issues

- #95 - Proactive task creation (Level 1)
- #112 - Watch mode for change monitoring (Level 2)
- #19 - Daemon prompt queue (infrastructure for Level 3)
- #94 - AI adoption strategies

## Acceptance Criteria (for full implementation)

### Level 1 (Prompting)
- [ ] Claude proactively creates tasks 80%+ of the time (without explicit instruction)
- [ ] Integration tests verify task creation, not just mentions
- [ ] Hooks prompt Claude on test failure, large commits, code smells

### Level 2 (Automatic)
- [ ] Test failures auto-create bug tasks
- [ ] Git commit messages with #42 auto-update task #42
- [ ] TODO comments in diffs auto-create tech-debt tasks
- [ ] User can enable/disable each automation

### Level 3 (AI Sessions)
- [ ] Daemon can spawn headless Claude session
- [ ] Sessions are sandboxed (limited permissions)
- [ ] User can approve/deny session before it runs
- [ ] Usage limited by quota (sessions per hour/day)
- [ ] User notified of autonomous actions

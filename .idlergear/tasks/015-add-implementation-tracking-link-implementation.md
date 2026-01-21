---
id: 15
title: Add implementation tracking - link implementation work to tasks
state: closed
created: '2026-01-03T05:33:58.091447Z'
labels:
- enhancement
- 'priority: high'
- 'effort: large'
- core-v1
- 'component: integration'
priority: high
---
## Summary

Based on session analysis, 36.1% of commands are implementation requests ("implement...", "add...", "create..."). Need system to track implementations and link them to tasks.

## Problem

Analysis of 72 Claude Code session transcripts shows:
- **36.1% of commands are implementation requests** (26 commands)
- Implementation work happens but tasks aren't always created/updated
- No automatic linking between "implement X" command and task tracking
- Task lifecycle not maintained (created → in_progress → completed)

Example commands from sessions:
- "implement..."
- "add [feature]..."
- "create [component]..."

## Proposed Solution

Multi-part system to track implementation work:

### 1. UserPromptSubmit Hook - Detect Implementation Intent

Add to `.claude/hooks/user-prompt-submit.sh`:

```bash
#!/bin/bash
# Detect implementation commands and suggest task creation

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

# Pattern: Implementation command
if echo "$PROMPT" | grep -qiE "^(implement|add|create|build|write|make) "; then
  # Extract feature name
  FEATURE=$(echo "$PROMPT" | sed -E 's/^(implement|add|create|build|write|make) //i' | cut -d' ' -f1-5)
  
  # Check if task exists for this
  EXISTING=$(idlergear task list --state open 2>/dev/null | grep -i "$FEATURE" || echo "")
  
  if [ -z "$EXISTING" ]; then
    cat <<EOF
{
  "additionalContext": "Implementation request detected: ${FEATURE}\n\nConsider creating a task to track this work:\n  idlergear task create \"Implement ${FEATURE}\" --priority high\n\nOr link to existing task with:\n  idlergear task update <id> --status in_progress"
}
EOF
  else
    cat <<EOF
{
  "additionalContext": "Related task found:\n${EXISTING}\n\nUpdate status to in_progress?"
}
EOF
  fi
fi

exit 0
```

### 2. Stop Hook - Prompt for Task Update

Add to `.claude/hooks/stop.sh`:

```bash
#!/bin/bash
# Check if implementation work should update tasks

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')

# Check recent messages for implementation activity
if [ -f "$TRANSCRIPT" ]; then
  RECENT=$(tail -100 "$TRANSCRIPT")
  
  # Look for implementation patterns
  if echo "$RECENT" | grep -qiE "(implement|added|created|built)"; then
    # Check for in-progress tasks
    IN_PROGRESS=$(idlergear task list --state open 2>/dev/null | grep -c "in_progress" || echo 0)
    
    if [ "$IN_PROGRESS" -gt 0 ]; then
      cat <<EOF
{
  "decision": "block",
  "reason": "Implementation work detected. Update task status? ($IN_PROGRESS in-progress tasks)"
}
EOF
      exit 0
    fi
  fi
fi

echo '{"decision": "approve"}'
exit 0
```

### 3. Git Commit Hook - Link Commits to Tasks

Add detection in PostToolUse:

```bash
# Detect git commits
if [[ "$TOOL" == "Bash" ]] && echo "$TOOL_INPUT" | grep -qE "git commit"; then
  # Extract commit message
  COMMIT_MSG=$(echo "$TOOL_INPUT" | grep -oP "(?<=-m \")[^\"]+")
  
  # Check for task references (#42, task-42, etc.)
  if ! echo "$COMMIT_MSG" | grep -qE "#[0-9]+"; then
    OPEN_TASKS=$(idlergear task list --state open 2>/dev/null | head -5)
    cat <<EOF
{
  "additionalContext": "Commit created without task reference.\n\nOpen tasks:\n${OPEN_TASKS}\n\nConsider:\n  1. Adding task reference to commit: git commit --amend -m \"... (#42)\"\n  2. Updating task: idlergear task update 42 --body \"Fixed in commit abc123\"\n  3. Closing task: idlergear task close 42"
}
EOF
  fi
fi
```

### 4. Implementation Command Tracking

Create `.idlergear/implementation_tracking.json`:

```json
{
  "sessions": [
    {
      "session_id": "abc123",
      "started": "2026-01-03T10:00:00Z",
      "implementation_request": "implement user authentication",
      "task_id": 42,
      "status": "in_progress",
      "commits": ["abc123", "def456"],
      "completed": null
    }
  ]
}
```

### 5. MCP Tool for Task Linking

```python
def link_implementation_to_task(description: str, task_id: int = None):
    """Link current implementation work to a task."""
    if task_id is None:
        # Create new task
        task = create_task(f"Implement: {description}", priority="high")
        task_id = task['id']
    else:
        # Update existing task
        update_task(task_id, status="in_progress")
    
    # Track in session
    session_id = get_current_session_id()
    track_implementation(session_id, description, task_id)
    
    return {"task_id": task_id, "tracked": True}
```

## Workflow Example

```
User: "implement user authentication"
  ↓
UserPromptSubmit hook: "Create task to track this?"
  ↓
User: "/yes" or AI creates task automatically
  ↓
Task #42 created: "Implement user authentication" [in_progress]
  ↓
... implementation happens ...
  ↓
git commit -m "feat: add auth (#42)"
  ↓
PostToolUse: "Task #42 referenced in commit"
  ↓
Stop hook: "Close task #42? Implementation appears complete"
  ↓
Task #42 closed
```

## Acceptance Criteria

- [ ] UserPromptSubmit detects implementation commands
- [ ] Suggests task creation for new implementations
- [ ] Suggests task status update for existing tasks
- [ ] Stop hook prompts to update task status after implementation
- [ ] Git commits can reference tasks (#42)
- [ ] Missing task references are flagged
- [ ] MCP tool for manual task linking
- [ ] Session tracking of implementation → task mapping
- [ ] Works across session boundaries (resume)

## Related

- Session analysis: 36.1% of work is implementation
- Issue #7 (Enhance UserPromptSubmit hook)
- Issue #6 (Implement Stop hook)
- Reference: "Claude Code Session Analysis - Common Command Patterns"

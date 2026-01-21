---
id: 1
title: Claude Code Hooks and IdlerGear Integration Opportunities
created: '2026-01-03T05:18:36.331815Z'
updated: '2026-01-03T05:18:36.331835Z'
---
# Claude Code Hooks and IdlerGear Integration Opportunities

## Complete Hook Reference with IdlerGear Use Cases

| Hook Type | Trigger | Parameters | Current IdlerGear Use | Potential IdlerGear Enhancements |
|-----------|---------|------------|----------------------|----------------------------------|
| **SessionStart** | Session starts/resumes | `source` (startup/resume/clear/compact), `session_id`, `CLAUDE_ENV_FILE` | None | **[HIGH VALUE]** Auto-run `idlergear context` and inject into conversation. Detect if first session vs resume. Set env vars for IdlerGear paths. |
| **UserPromptSubmit** | User submits prompt | `prompt`, `session_id` | Check for context reminder (current) | **[MEDIUM VALUE]** Detect session start (first prompt). Inject task list if user asks about "what's next". Pattern detection for TODO/bug mentions → suggest task creation. |
| **PreToolUse** | Before tool executes | `tool_name`, `tool_input`, `tool_use_id` | None | **[HIGH VALUE]** Block Write/Edit for forbidden files (TODO.md, NOTES.md). Auto-suggest IdlerGear alternatives. Detect git commit → suggest task closure. |
| **PostToolUse** | After tool completes | `tool_name`, `tool_input`, `tool_response` | Check forbidden files after Write/Edit (current) | **[MEDIUM VALUE]** After Edit with bug fix → prompt "Create task?". After multiple edits → suggest commit + task update. Detect test failures → create bug task. |
| **Stop** | Claude finishes response | `stop_hook_active` (bool) | None | **[HIGH VALUE]** Check if tasks marked complete. Suggest "Save progress with note?". Prompt to update current task status. Auto-save session state. |
| **SubagentStop** | Subagent (Task tool) finishes | `stop_hook_active` (bool) | None | **[MEDIUM VALUE]** Subagents often do research - prompt to save findings as notes/references. Check if discoveries should become tasks. |
| **PermissionRequest** | Permission dialog shown | `tool_name`, permission context | None | **[LOW VALUE]** Track high-risk operations for audit. Log to IdlerGear run. |
| **Notification** | Claude sends notification | `message`, `notification_type` (permission_prompt, idle_prompt, etc.) | None | **[LOW VALUE]** Capture notifications in session log. Alert user if critical permission needed. |
| **PreCompact** | Before compacting transcript | `trigger` (manual/auto), `custom_instructions` | None | **[MEDIUM VALUE]** Save pre-compact snapshot as note. Extract important decisions before compaction. Auto-create references from long discussions. |

## Detailed Integration Strategies

### 1. SessionStart Hook - **HIGHEST PRIORITY**

**Goal:** Ensure Claude ALWAYS has project context at session start.

**Implementation:**
```bash
#!/bin/bash
# .claude/hooks/session-start.sh

# Run idlergear context and format for injection
CONTEXT=$(idlergear context --format compact 2>/dev/null)

if [ $? -eq 0 ]; then
  # Output for Claude to consume
  cat <<EOF
{
  "additionalContext": "=== PROJECT CONTEXT ===\n\n$CONTEXT\n\n=== END CONTEXT ===\n\nYou now have full project context. Proceed with the user's request."
}
EOF
else
  # IdlerGear not initialized - silent fallback
  exit 0
fi
```

**Configuration:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

**Impact:** 100% session start context loading (no reliance on Claude remembering)

---

### 2. PreToolUse Hook - File Prevention

**Goal:** Block forbidden file operations BEFORE they happen.

**Implementation:**
```bash
#!/bin/bash
# .claude/hooks/pre-tool-use.sh

# Read JSON input
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input')

# Extract file path based on tool
if [[ "$TOOL" == "Write" || "$TOOL" == "Edit" ]]; then
  FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // .path // empty')
  
  # Check against forbidden patterns
  FORBIDDEN_PATTERNS=(
    "TODO.md" "NOTES.md" "SESSION.*\\.md"
    "BACKLOG.md" "SCRATCH.md" "TASKS.md"
  )
  
  for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    if [[ "$FILE_PATH" =~ $pattern ]]; then
      # Block the operation
      cat <<EOF >&2
ERROR: Forbidden file pattern detected: $FILE_PATH

Instead of creating $FILE_PATH, use:
  - idlergear task create "..." (for tasks/todos)
  - idlergear note create "..." (for scratch notes)
  - idlergear reference add "..." (for documentation)

See CLAUDE.md for full guidelines.
EOF
      exit 2  # Exit code 2 = blocking error
    fi
  done
fi

exit 0  # Allow operation
```

**Configuration:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/pre-tool-use.sh"
          }
        ]
      }
    ]
  }
}
```

**Impact:** 0% forbidden file creation (hard enforcement)

---

### 3. Stop Hook - Session Completion

**Goal:** Prompt for knowledge capture before session ends.

**Implementation (Prompt-based):**
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Before stopping, check:\n1. Are there open tasks that should be updated?\n2. Were any discoveries made that should be saved as notes?\n3. Were any design decisions made that should be documented as references?\n\nIf yes to any, respond with {\"decision\": \"block\", \"reason\": \"Need to capture knowledge first\"}.\nIf no, respond with {\"decision\": \"approve\"}."
          }
        ]
      }
    ]
  }
}
```

**Impact:** Reduced knowledge loss at session boundaries

---

### 4. UserPromptSubmit Hook - Pattern Detection

**Goal:** Detect patterns in user prompts that indicate IdlerGear should be used.

**Implementation:**
```bash
#!/bin/bash
# .claude/hooks/user-prompt-submit.sh

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

# Pattern: User asks "what's next" or "what should I work on"
if echo "$PROMPT" | grep -qiE "(what.s next|what should|to do|work on)"; then
  TASKS=$(idlergear task list --state open 2>/dev/null | head -5)
  if [ -n "$TASKS" ]; then
    cat <<EOF
{
  "additionalContext": "Open tasks from IdlerGear:\n$TASKS"
}
EOF
  fi
fi

# Pattern: User mentions "bug" or "broken"
if echo "$PROMPT" | grep -qiE "(bug|broken|error|issue|problem)"; then
  echo '{"additionalContext": "REMINDER: When you find/fix a bug, create a task: idlergear task create \"...\" --label bug"}' 
fi

exit 0
```

**Impact:** Proactive IdlerGear suggestions based on user intent

---

### 5. PostToolUse Hook - Activity Detection

**Goal:** Detect work patterns and suggest appropriate IdlerGear actions.

**Implementation:**
```bash
#!/bin/bash
# .claude/hooks/post-tool-use.sh

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input')
TOOL_RESPONSE=$(echo "$INPUT" | jq -r '.tool_response')

# Count recent file edits (track in temp file)
EDIT_COUNT_FILE="/tmp/claude-idlergear-edit-count-$$"
if [[ "$TOOL" == "Edit" || "$TOOL" == "Write" ]]; then
  COUNT=$(cat "$EDIT_COUNT_FILE" 2>/dev/null || echo 0)
  COUNT=$((COUNT + 1))
  echo "$COUNT" > "$EDIT_COUNT_FILE"
  
  # After 5 edits, suggest commit + task update
  if [ "$COUNT" -ge 5 ]; then
    cat <<EOF
{
  "additionalContext": "You've made $COUNT file changes. Consider:\n1. Creating a git commit\n2. Updating the current task status\n3. Creating notes for any discoveries"
}
EOF
    rm "$EDIT_COUNT_FILE"  # Reset counter
  fi
fi

# Detect test failures
if [[ "$TOOL" == "Bash" ]]; then
  if echo "$TOOL_RESPONSE" | grep -qiE "(test.*failed|error|assertion)"; then
    cat <<EOF
{
  "additionalContext": "Test failure detected. Consider creating a bug task:\nidlergear task create \"Fix failing test\" --label bug"
}
EOF
  fi
fi

exit 0
```

**Impact:** Contextual prompting based on Claude's activities

---

## Environment Variables for Hooks

| Variable | Available In | Purpose |
|----------|-------------|---------|
| `CLAUDE_PROJECT_DIR` | All hooks | Absolute path to project root |
| `CLAUDE_CODE_REMOTE` | All hooks | "true" if web environment, empty for CLI |
| `CLAUDE_ENV_FILE` | SessionStart only | Path to file for persisting env vars across session |
| `TOOL_INPUT_PATH` | PostToolUse (Write/Edit) | File path being written/edited |

**IdlerGear-specific vars to set:**
```bash
# In SessionStart hook
echo "export IDLERGEAR_ROOT=$(idlergear config get root)" >> "$CLAUDE_ENV_FILE"
echo "export IDLERGEAR_SESSION_ID=$session_id" >> "$CLAUDE_ENV_FILE"
```

---

## Hook JSON Input Schema Examples

### SessionStart
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript",
  "cwd": "/path/to/project",
  "permission_mode": "ask",
  "source": "startup"
}
```

### UserPromptSubmit
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript",
  "cwd": "/path/to/project",
  "permission_mode": "ask",
  "prompt": "Help me fix this bug"
}
```

### PostToolUse
```json
{
  "session_id": "abc123",
  "tool_name": "Edit",
  "tool_input": {"file_path": "src/main.py", "old_string": "...", "new_string": "..."},
  "tool_response": "Success",
  "tool_use_id": "xyz789"
}
```

---

## Implementation Priority

| Priority | Hook | Benefit | Effort |
|----------|------|---------|--------|
| P0 | SessionStart | 100% context loading | Low |
| P1 | PreToolUse | Prevent forbidden files | Low |
| P1 | Stop | Reduce knowledge loss | Medium |
| P2 | PostToolUse | Activity-based suggestions | Medium |
| P2 | UserPromptSubmit | Intent detection | Medium |
| P3 | SubagentStop | Research capture | Low |
| P4 | PreCompact | Archive decisions | Low |

---

## Testing Hooks

```bash
# Test hook manually
echo '{"session_id":"test","source":"startup"}' | ./.claude/hooks/session-start.sh

# Enable verbose hook logging in Claude Code settings
# See hook execution in real-time
```

---

## Current IdlerGear Hook Usage

From `.claude/hooks.json`:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "idlergear check --file \"$TOOL_INPUT_PATH\" --quiet"
      }
    ],
    "UserPromptSubmit": [
      {
        "command": "idlergear check --context-reminder"
      }
    ]
  }
}
```

**Status:** Basic enforcement exists, but missing session start, pre-tool blocking, and stop hooks.

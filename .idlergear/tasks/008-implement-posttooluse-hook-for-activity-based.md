---
id: 8
title: Implement PostToolUse hook for activity-based suggestions
state: open
created: '2026-01-03T05:23:28.432575Z'
labels:
- enhancement
- 'priority: medium'
- 'effort: medium'
- 'component: integration'
priority: medium
---
## Summary

Enhance PostToolUse hook to detect work patterns and suggest appropriate IdlerGear actions (e.g., after N edits → suggest commit, after test failure → create bug task).

## Problem

Current PostToolUse only validates forbidden files. We can provide contextual suggestions:
- After 5+ edits → "Consider committing and updating task status"
- After test failure → "Create a bug task for this?"
- After implementing feature → "Update or close the related task?"

## Proposed Solution

**Hook:** PostToolUse  
**Priority:** P2 (improves workflow)  
**Expected impact:** More natural IdlerGear adoption through contextual prompts

### Implementation

Create `.claude/hooks/post-tool-use.sh`:

```bash
#!/bin/bash
# Detect activity patterns and suggest IdlerGear actions

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input')
TOOL_RESPONSE=$(echo "$INPUT" | jq -r '.tool_response')

SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
EDIT_COUNT_FILE="/tmp/idlergear-edit-count-${SESSION_ID}"

SUGGESTIONS=""

# Track file edits
if [[ "$TOOL" == "Edit" || "$TOOL" == "Write" ]]; then
  COUNT=$(cat "$EDIT_COUNT_FILE" 2>/dev/null || echo 0)
  COUNT=$((COUNT + 1))
  echo "$COUNT" > "$EDIT_COUNT_FILE"
  
  # After 5 edits, suggest commit
  if [ "$COUNT" -ge 5 ]; then
    SUGGESTIONS="${SUGGESTIONS}You've made ${COUNT} file changes. Consider:\n"
    SUGGESTIONS="${SUGGESTIONS}  1. Creating a git commit\n"
    SUGGESTIONS="${SUGGESTIONS}  2. Updating the current task status\n"
    SUGGESTIONS="${SUGGESTIONS}  3. Creating notes for any discoveries\n\n"
    rm "$EDIT_COUNT_FILE"  # Reset counter
  fi
fi

# Detect test failures in Bash output
if [[ "$TOOL" == "Bash" ]]; then
  if echo "$TOOL_RESPONSE" | grep -qiE "(test.*failed|assertion.*failed|error:|FAILED)"; then
    SUGGESTIONS="${SUGGESTIONS}Test failure detected. Consider creating a bug task:\n"
    SUGGESTIONS="${SUGGESTIONS}  idlergear task create \"Fix failing test\" --label bug\n\n"
  fi
fi

# Detect git commits - suggest task update
if [[ "$TOOL" == "Bash" ]] && echo "$TOOL_INPUT" | grep -qE "git commit"; then
  OPEN_TASKS=$(idlergear task list --state open 2>/dev/null | grep -c "^#" || echo 0)
  if [ "$OPEN_TASKS" -gt 0 ]; then
    SUGGESTIONS="${SUGGESTIONS}Commit created. Consider updating or closing related task.\n\n"
  fi
fi

# Output suggestions if any
if [ -n "$SUGGESTIONS" ]; then
  cat <<EOF
{
  "additionalContext": "${SUGGESTIONS}"
}
EOF
fi

exit 0
```

### Configuration

Update in `.claude/hooks.json` (merge with existing PostToolUse):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "idlergear check --file \"$TOOL_INPUT_PATH\" --quiet"
      },
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/post-tool-use.sh"
          }
        ]
      }
    ]
  }
}
```

### Acceptance Criteria

- [ ] Counts edits across session
- [ ] Suggests commit after N edits (configurable)
- [ ] Detects test failures → suggests bug task
- [ ] Detects git commit → suggests task update
- [ ] Doesn't spam suggestions (threshold-based)
- [ ] Session-specific counters (isolated per session)
- [ ] Cleanup on session end

## Related

- Current PostToolUse validation
- Integration strategy Phase 2
- Reference: "Claude Code Hooks and IdlerGear Integration Opportunities"

---
id: 7
title: Enhance UserPromptSubmit hook with pattern detection and context injection
state: open
created: '2026-01-03T05:23:27.947953Z'
labels:
- enhancement
- 'priority: medium'
- 'effort: small'
- 'component: integration'
priority: medium
---
## Summary

Enhance UserPromptSubmit hook to detect user intent patterns and proactively inject relevant IdlerGear context (e.g., task list when user asks "what's next?", bug reminder when user mentions errors).

## Problem

Current UserPromptSubmit hook only does basic context reminder. We can be smarter:
- User asks "what's next?" → auto-inject task list
- User mentions "bug" → remind to create task
- User asks "what did we decide?" → search references

## Proposed Solution

**Hook:** UserPromptSubmit  
**Priority:** P2 (improves UX, but not blocking)  
**Expected impact:** Proactive IdlerGear suggestions based on user intent

### Implementation

Create `.claude/hooks/user-prompt-submit.sh`:

```bash
#!/bin/bash
# Detect user intent and inject relevant context

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt')

ADDITIONAL_CONTEXT=""

# Pattern: User asks about next steps
if echo "$PROMPT" | grep -qiE "(what.s next|what should|to do|work on|continue)"; then
  TASKS=$(idlergear task list --state open 2>/dev/null | head -n 10)
  if [ -n "$TASKS" ]; then
    ADDITIONAL_CONTEXT="${ADDITIONAL_CONTEXT}Open tasks from IdlerGear:\n${TASKS}\n\n"
  fi
fi

# Pattern: User mentions bugs or errors
if echo "$PROMPT" | grep -qiE "(bug|broken|error|issue|problem|failing)"; then
  ADDITIONAL_CONTEXT="${ADDITIONAL_CONTEXT}REMINDER: When you find or fix a bug, create a task:\n  idlergear task create \"...\" --label bug\n\n"
fi

# Pattern: User asks about decisions
if echo "$PROMPT" | grep -qiE "(why did we|what did we decide|decision|approach)"; then
  REFS=$(idlergear reference list 2>/dev/null | head -n 5)
  if [ -n "$REFS" ]; then
    ADDITIONAL_CONTEXT="${ADDITIONAL_CONTEXT}Recent references (design decisions):\n${REFS}\n\n"
  fi
fi

# Pattern: First message in session (simple heuristic)
TRANSCRIPT="${transcript_path}"
if [ -f "$TRANSCRIPT" ]; then
  MSG_COUNT=$(grep -c "\"role\": \"user\"" "$TRANSCRIPT" 2>/dev/null || echo 1)
  if [ "$MSG_COUNT" -le 1 ]; then
    ADDITIONAL_CONTEXT="${ADDITIONAL_CONTEXT}TIP: This appears to be a new session. Full context loaded via SessionStart hook.\n\n"
  fi
fi

# Output additional context if any
if [ -n "$ADDITIONAL_CONTEXT" ]; then
  cat <<EOF
{
  "additionalContext": "${ADDITIONAL_CONTEXT}"
}
EOF
fi

exit 0
```

### Configuration

Update in `.claude/hooks.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/user-prompt-submit.sh"
          }
        ]
      }
    ]
  }
}
```

### Acceptance Criteria

- [ ] Detects "what's next" pattern → injects task list
- [ ] Detects bug mentions → reminds to create task
- [ ] Detects decision questions → shows references
- [ ] Doesn't inject unnecessarily (avoid noise)
- [ ] Fast execution (< 100ms)
- [ ] Graceful handling of IdlerGear errors

## Related

- Current basic UserPromptSubmit hook
- Integration strategy Phase 2
- Reference: "Claude Code Hooks and IdlerGear Integration Opportunities"

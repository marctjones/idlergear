---
id: 4
title: Implement SessionStart hook for automatic context injection
state: closed
created: '2026-01-03T05:23:26.563622Z'
labels:
- enhancement
- 'priority: high'
- 'effort: small'
- core-v1
- 'component: integration'
priority: high
---
## Summary

Add SessionStart hook to automatically inject `idlergear context` into every Claude Code session, eliminating reliance on Claude remembering to run it.

## Problem

Currently, Claude must remember to run `idlergear context` or `/start` at session start. Compliance is estimated at ~60%. This leads to:
- Missing project context
- Re-explaining goals and current state
- Inconsistent IdlerGear usage

## Proposed Solution

**Hook:** SessionStart  
**Priority:** P0 (highest impact)  
**Expected impact:** 100% context loading compliance

### Implementation

Create `.claude/hooks/session-start.sh`:

```bash
#!/bin/bash
# Auto-inject IdlerGear context at session start

CONTEXT=$(idlergear context --format compact 2>/dev/null)

if [ $? -eq 0 ]; then
  cat <<EOF
{
  "additionalContext": "=== PROJECT CONTEXT ===\n\n$CONTEXT\n\n=== END CONTEXT ===\n\nYou now have full project context. Proceed with the user's request."
}
EOF
  
  # Persist session ID for other hooks
  if [ -n "$CLAUDE_ENV_FILE" ]; then
    echo "export IDLERGEAR_SESSION_ID=${session_id}" >> "$CLAUDE_ENV_FILE"
  fi
else
  # IdlerGear not initialized - silent fallback
  exit 0
fi
```

### Configuration

Add to `.claude/hooks.json`:

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

### Acceptance Criteria

- [ ] Hook script created and executable
- [ ] Configuration added to hooks.json
- [ ] Context automatically injected on session start
- [ ] Context automatically injected on session resume
- [ ] Works with `source` types: startup, resume, clear, compact
- [ ] Graceful fallback if IdlerGear not initialized
- [ ] Session ID persisted to `$CLAUDE_ENV_FILE`

## Related

- Integration strategy reference: "Claude Code Hooks and IdlerGear Integration Opportunities"
- Issue #114 (session state persistence)
- Integration strategy Phase 1

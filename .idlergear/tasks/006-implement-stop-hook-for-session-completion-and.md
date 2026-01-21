---
id: 6
title: Implement Stop hook for session completion and knowledge capture
state: closed
created: '2026-01-03T05:23:27.452114Z'
labels:
- enhancement
- 'priority: high'
- 'effort: medium'
- core-v1
- 'component: integration'
priority: high
---
## Summary

Add Stop hook to prompt Claude for knowledge capture before ending a session - checking for unclosed tasks, unsaved discoveries, and undocumented decisions.

## Problem

When Claude finishes a response and stops, knowledge is often lost:
- Tasks worked on but not updated
- Discoveries made but not saved as notes
- Design decisions discussed but not documented
- Session state not captured (relates to #114)

## Proposed Solution

**Hook:** Stop  
**Priority:** P1 (reduces knowledge loss)  
**Expected impact:** Significant reduction in lost context at session boundaries

### Implementation (Prompt-based)

Add to `.claude/hooks.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Before stopping, evaluate if knowledge should be captured:\n\n1. Were any tasks worked on that should be updated or closed?\n2. Were any discoveries, quirks, or insights found that should be saved as notes?\n3. Were any design decisions or architectural choices made that should be documented as references?\n4. Should the current session state be saved for next time?\n\nIf YES to any, respond with:\n{\"decision\": \"block\", \"reason\": \"Need to capture: [specific items]\"}\n\nIf NO (all knowledge already captured), respond with:\n{\"decision\": \"approve\"}\n\nBe honest - don't block unnecessarily, but don't let important context get lost."
          }
        ]
      }
    ]
  }
}
```

### Alternative: Command-based Implementation

For more control, create `.claude/hooks/stop.sh`:

```bash
#!/bin/bash
# Check if knowledge should be captured before stopping

# Check for in-progress tasks
IN_PROGRESS=$(idlergear task list --state open 2>/dev/null | grep -c "in_progress" || echo 0)

# Check session transcript for uncaptured patterns
TRANSCRIPT="${transcript_path}"
if [ -f "$TRANSCRIPT" ]; then
  # Look for potential uncaptured knowledge
  BUGS_MENTIONED=$(grep -ciE "(bug|broken|error|issue)" "$TRANSCRIPT" || echo 0)
  DECISIONS_MADE=$(grep -ciE "(we should|let's use|decided to)" "$TRANSCRIPT" || echo 0)
fi

if [ "$IN_PROGRESS" -gt 0 ] || [ "$BUGS_MENTIONED" -gt 2 ] || [ "$DECISIONS_MADE" -gt 1 ]; then
  cat <<EOF
{
  "decision": "block",
  "reason": "Potential uncaptured knowledge: $IN_PROGRESS in-progress tasks, $BUGS_MENTIONED bug mentions, $DECISIONS_MADE decision patterns"
}
EOF
  exit 0
else
  echo '{"decision": "approve"}'
  exit 0
fi
```

### Acceptance Criteria

- [ ] Hook configuration added
- [ ] Prompts Claude before stopping
- [ ] Can block stop if knowledge needs capturing
- [ ] Provides specific reason for blocking
- [ ] Doesn't block unnecessarily (false positives)
- [ ] Integrates with session state saving (#114)

## Related

- Issue #114 (session state persistence)
- Integration strategy Phase 2
- Reference: "Claude Code Hooks and IdlerGear Integration Opportunities"

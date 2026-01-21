---
id: 9
title: Implement SubagentStop hook for research capture
state: open
created: '2026-01-03T05:23:28.924784Z'
labels:
- enhancement
- 'priority: low'
- 'effort: small'
- 'component: integration'
priority: low
---
## Summary

Add SubagentStop hook to prompt for knowledge capture when Task tool (subagent) completes, since subagents often perform research and exploration.

## Problem

When Claude spawns subagents (via Task tool) for research or exploration:
- Discoveries are made but not always captured
- Subagent findings stay in transcript, not in IdlerGear
- Knowledge gets lost when transcript compacts

## Proposed Solution

**Hook:** SubagentStop  
**Priority:** P3 (nice to have, improves research workflows)  
**Expected impact:** Better capture of exploration findings

### Implementation

Create `.claude/hooks/subagent-stop.sh`:

```bash
#!/bin/bash
# Prompt to capture subagent research findings

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')

# Check if subagent was doing research/exploration
if [ -f "$TRANSCRIPT" ]; then
  # Look for exploration patterns in recent messages
  TAIL_LINES=$(tail -n 100 "$TRANSCRIPT")
  
  if echo "$TAIL_LINES" | grep -qiE "(explore|research|investigate|analyze|understand)"; then
    cat <<EOF
{
  "additionalContext": "Research subagent completed. Consider capturing findings:\n  - idlergear note create \"...\" --tag explore (for questions/investigations)\n  - idlergear reference add \"...\" (for confirmed knowledge)\n  - idlergear task create \"...\" (if follow-up work needed)"
}
EOF
  fi
fi

exit 0
```

### Configuration

Add to `.claude/hooks.json`:

```json
{
  "hooks": {
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/subagent-stop.sh"
          }
        ]
      }
    ]
  }
}
```

### Alternative: Prompt-based

```json
{
  "hooks": {
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "A subagent just completed. Did it discover anything worth capturing?\n\nIf YES, respond with: {\"decision\": \"block\", \"reason\": \"Need to capture: [findings]\"}\nIf NO, respond with: {\"decision\": \"approve\"}"
          }
        ]
      }
    ]
  }
}
```

### Acceptance Criteria

- [ ] Detects subagent completion
- [ ] Prompts only for research-oriented subagents
- [ ] Suggests appropriate IdlerGear command (note vs reference)
- [ ] Doesn't prompt unnecessarily
- [ ] Low overhead (< 50ms)

## Related

- Task tool (subagent invocation)
- Integration strategy Phase 3
- Reference: "Claude Code Hooks and IdlerGear Integration Opportunities"

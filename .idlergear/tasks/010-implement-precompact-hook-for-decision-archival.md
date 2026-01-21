---
id: 10
title: Implement PreCompact hook for decision archival
state: open
created: '2026-01-03T05:23:29.433505Z'
labels:
- enhancement
- 'priority: low'
- 'effort: medium'
- 'component: integration'
priority: low
---
## Summary

Add PreCompact hook to extract and save important decisions/discoveries as references before transcript compaction destroys the detailed context.

## Problem

When Claude compacts the transcript:
- Detailed discussions get summarized or lost
- Design decisions fade into summaries
- Nuanced reasoning disappears
- Future sessions lose context depth

## Proposed Solution

**Hook:** PreCompact  
**Priority:** P3 (prevents gradual knowledge erosion)  
**Expected impact:** Preserve important context across compactions

### Implementation

Create `.claude/hooks/pre-compact.sh`:

```bash
#!/bin/bash
# Archive important decisions before compaction

INPUT=$(cat)
TRIGGER=$(echo "$INPUT" | jq -r '.trigger')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')

# Only process if transcript exists
if [ ! -f "$TRANSCRIPT" ]; then
  exit 0
fi

# Extract potential decisions (simple heuristic)
DECISIONS=$(grep -iE "(decided to|chosen|we should|let's use|approach)" "$TRANSCRIPT" | head -n 10)

if [ -n "$DECISIONS" ]; then
  # Save to temp file for user review
  TEMP_FILE="/tmp/idlergear-precompact-decisions-$(date +%s).txt"
  echo "=== Decisions from transcript ===" > "$TEMP_FILE"
  echo "$DECISIONS" >> "$TEMP_FILE"
  echo "" >> "$TEMP_FILE"
  echo "To save: idlergear reference add \"Decision: <title>\"" >> "$TEMP_FILE"
  
  cat <<EOF
{
  "additionalContext": "Before compacting, review potential decisions in:\n  $TEMP_FILE\n\nConsider saving important ones as references."
}
EOF
fi

exit 0
```

### Alternative: Automated Extraction

More sophisticated version that uses LLM to extract decisions:

```bash
#!/bin/bash
# Use LLM to extract decisions from transcript

# Extract last N messages
RECENT=$(tail -n 500 "$TRANSCRIPT")

# Prompt LLM (via mcp__anthropic__complete or similar)
# "Identify design decisions from this transcript. Format as references."

# Auto-create references (requires user confirmation)
```

### Configuration

Add to `.claude/hooks.json`:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "auto|manual",
        "hooks": [
          {
            "type": "command",
            "command": "./.claude/hooks/pre-compact.sh"
          }
        ]
      }
    ]
  }
}
```

### Acceptance Criteria

- [ ] Detects both auto and manual compaction
- [ ] Extracts decision patterns from transcript
- [ ] Provides easy way to review and save
- [ ] Works for both CLI and web environments
- [ ] Doesn't block compaction (non-blocking)
- [ ] Fast execution (< 1 second)

## Related

- Transcript compaction feature
- Integration strategy Phase 4
- Reference: "Claude Code Hooks and IdlerGear Integration Opportunities"

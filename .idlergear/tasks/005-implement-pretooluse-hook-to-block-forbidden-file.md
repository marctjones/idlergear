---
id: 5
title: Implement PreToolUse hook to block forbidden file operations
state: closed
created: '2026-01-03T05:23:27.004179Z'
labels:
- enhancement
- 'priority: high'
- 'effort: small'
- core-v1
- 'component: integration'
priority: high
---
## Summary

Add PreToolUse hook to block Write/Edit operations on forbidden files (TODO.md, NOTES.md, etc.) BEFORE they happen, with helpful error messages suggesting IdlerGear alternatives.

## Problem

Currently, forbidden file detection happens in PostToolUse (after the file is created). This means:
- File is created then validation fails
- Claude has already spent effort on wrong approach
- Creates friction and rework

## Proposed Solution

**Hook:** PreToolUse  
**Priority:** P1 (high impact, prevents bad behavior)  
**Expected impact:** 0% forbidden file creation

### Implementation

Create `.claude/hooks/pre-tool-use.sh`:

```bash
#!/bin/bash
# Block forbidden file operations BEFORE they happen

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input')

if [[ "$TOOL" == "Write" || "$TOOL" == "Edit" ]]; then
  FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // .path // empty')
  
  FORBIDDEN_PATTERNS=(
    "TODO.md" "NOTES.md" "SESSION.*\\.md"
    "BACKLOG.md" "SCRATCH.md" "TASKS.md"
    "FEATURE_IDEAS.md" "RESEARCH.md"
  )
  
  for pattern in "${FORBIDDEN_PATTERNS[@]}"; do
    if [[ "$FILE_PATH" =~ $pattern ]]; then
      cat <<EOF >&2
ERROR: Forbidden file pattern detected: $FILE_PATH

Instead of creating $FILE_PATH, use IdlerGear commands:
  - idlergear task create "..." (for tasks/todos)
  - idlergear note create "..." (for scratch notes)
  - idlergear reference add "..." (for documentation)

See CLAUDE.md for full guidelines.
EOF
      exit 2  # Exit code 2 = blocking error
    fi
  done
fi

exit 0
```

### Configuration

Add to `.claude/hooks.json`:

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

### Acceptance Criteria

- [ ] Hook script created and executable
- [ ] All forbidden patterns from CLAUDE.md included
- [ ] Error message suggests appropriate IdlerGear alternative
- [ ] Blocks operation with exit code 2
- [ ] Allows non-forbidden files through
- [ ] Works for both Write and Edit tools
- [ ] Error message is helpful and actionable

## Related

- Current PostToolUse validation in .claude/hooks.json
- CLAUDE.md forbidden file list
- Integration strategy Phase 1

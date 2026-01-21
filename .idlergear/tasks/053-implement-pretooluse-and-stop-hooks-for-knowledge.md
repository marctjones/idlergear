---
id: 53
title: Implement PreToolUse and Stop hooks for knowledge capture enforcement
state: closed
created: '2026-01-07T04:18:04.141993Z'
labels:
- enhancement
- hooks
- integration
- core-v1
priority: high
---
Implement Option B - Hook Integration:

**PreToolUse Hook (Task #5):**
- Block forbidden file operations BEFORE they happen
- Detect TODO.md, NOTES.md, SESSION_*.md patterns
- Provide helpful error messages with IdlerGear alternatives

**Stop Hook (Task #6):**
- Prompt for knowledge capture before ending session
- Check for in-progress tasks
- Detect uncaptured discoveries in transcript
- Block stop if important context would be lost

**Benefits:**
- 100% enforcement of IdlerGear usage (no forbidden files)
- Zero knowledge loss at session boundaries
- Proactive knowledge capture reminders

---
id: 28
title: Add --format flag for assistant-specific output (goose, json, markdown, html)
state: open
created: '2026-01-07T01:37:00.114460Z'
labels:
- enhancement
- goose
- ux
priority: high
---
## Summary
Add output format options to all major commands to support different AI assistants and interfaces.

## Context
From Goose integration analysis (Note #4): Goose GUI needs visual-friendly output, CLI needs text, MCP needs structured data.

## Implementation

Add `--format` flag to key commands:
```bash
idlergear context --format goose       # Goose-optimized (top 3 tasks, visual markers)
idlergear context --format json        # Structured data
idlergear context --format markdown    # GUI rendering with badges
idlergear context --format html        # Rich visual dashboard

idlergear status --format goose-card   # GUI card with badges 🔴 🟡 🟢
```

## Features by Format

**goose**: 
- High-signal information (top 3 tasks, not all)
- Visual markers for GUI rendering
- Conversational tone

**json**: 
- Structured, machine-readable
- Complete data

**markdown**:
- Visual badges (🔴 3 high-priority)
- Collapsible sections
- Suitable for GUI rendering

**html**:
- Full dashboard with CSS
- Interactive elements
- Can be embedded in GUI

## Acceptance Criteria
- [ ] `--format` flag works on `context`, `status`, `task list`, `note list`
- [ ] Each format produces valid output
- [ ] Default format is current text output (backward compatible)
- [ ] Tests for each format type
- [ ] Documentation updated

## Related
- Note #4 (Goose integration analysis)
- #112 (watch mode)
- #113 (status command - already implemented)

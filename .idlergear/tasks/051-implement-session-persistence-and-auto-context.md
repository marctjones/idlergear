---
id: 51
title: Implement session persistence and auto-context loading
state: closed
created: '2026-01-07T04:10:39.644758Z'
labels:
- enhancement
- session-management
- high-priority
priority: high
---
Two-part implementation:

1. **Session State Persistence**
   - Track session state (current task focus, recent context mode, working files)
   - Save/restore between sessions
   - Store in `.idlergear/session_state.json`

2. **Auto-Context Loading via Server Instructions**
   - Update MCP server `instructions` parameter to STRONGLY recommend calling context at session start
   - Add helper tool `idlergear_session_start()` that loads context + session state
   - Make it extremely clear in tool descriptions

Implementation approach:
- Session state storage (JSON file)
- `idlergear_session_start()` tool (loads context + state)
- Update server instructions to make usage obvious
- CLI command: `idlergear session save/restore/clear`

This solves #114 (session continuity) and makes context loading more automatic without true hooks.

---
id: 3
title: Add adoption metrics tracking - measure session start compliance and tool usage
state: open
created: '2026-01-03T04:57:07.580300Z'
labels:
- enhancement
- 'component: monitoring'
priority: medium
---
From integration strategy success metrics:

**Track:**
- % sessions starting with idlergear_context (target: 90%+)
- % bugs resulting in task creation (target: 80%+)
- % forbidden files created (target: 0%)
- % design decisions documented (target: 50%+)

**Implementation options:**
1. Log analysis of MCP tool calls
2. IdlerGear telemetry (opt-in)
3. Manual periodic review

**Why:** "What gets measured gets managed" - need data to validate integration improvements

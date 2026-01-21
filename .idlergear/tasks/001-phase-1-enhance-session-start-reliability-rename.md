---
id: 1
title: 'Phase 1: Enhance session start reliability - rename /context to /start and
  update instructions'
state: closed
created: '2026-01-03T04:57:07.315152Z'
labels:
- enhancement
- core-v1
- 'component: integration'
priority: high
---
From integration strategy Phase 1:

**Actions:**
1. Rename `/context` → `/start` in slash command
2. Update CLAUDE.md to feature /start as FIRST instruction
3. Add "MANDATORY" language to idlergear_context MCP tool description
4. Consider statusline integration showing "Run /start to begin"

**Why:** 90%+ session start compliance is critical for context continuity. Current /context command gets skipped too often.

**Success metric:** Track % of sessions that call idlergear_context in first 3 messages

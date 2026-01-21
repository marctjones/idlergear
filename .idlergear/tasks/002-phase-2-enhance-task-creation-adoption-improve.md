---
id: 2
title: 'Phase 2: Enhance task creation adoption - improve MCP descriptions with specific
  triggers'
state: closed
created: '2026-01-03T04:57:07.433186Z'
labels:
- enhancement
- core-v1
- 'component: integration'
priority: high
---
From integration strategy Phase 2:

**Actions:**
1. Update task_create MCP description with SPECIFIC triggers:
   - "When you find a bug" → create task with --label bug
   - "When you make a design decision" → use reference_add
   - "When you add TODO comment" → create task with --label tech-debt
2. Add pattern examples to CLAUDE.md
3. Consider TodoWrite → IdlerGear task conversion

**Why:** Claude creates tasks only ~50% of the time when appropriate. Need explicit behavioral triggers.

**Success metric:** 80%+ of bugs found result in task creation

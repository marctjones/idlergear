---
id: 32
title: Add lightweight context summary tools (context_summary, session_diff)
state: open
created: '2026-01-07T01:37:00.161347Z'
labels:
- enhancement
- performance
- mcp
priority: medium
---
## Summary
Add MCP tools and CLI commands for quick context checks without loading full context.

## Context
From Goose integration analysis (Note #4): AI assistants need fast ways to check "what's new" without full context load.

## New MCP Tools

### 1. `idlergear_context_summary()`
Returns high-level summary:
```json
{
  "tasks_open": 12,
  "tasks_high_priority": 3,
  "notes_recent": 5,
  "runs_active": 1,
  "last_session": "2 hours ago",
  "changes_since_last": {
    "new_tasks": 2,
    "completed_tasks": 1,
    "new_notes": 3
  }
}
```

### 2. `idlergear_session_diff()`
Git-style diff of knowledge state:
```
Since last session (2 hours ago):
+ Task #42: Fix parser bug [high priority]
+ Task #43: Add tests
✓ Task #41: Update docs (closed)
+ Note: "Parser quirk with compound words"
+ Note: "Need to support Windows"
```

### 3. CLI Commands

```bash
idlergear summary              # Quick summary
idlergear diff                 # Session diff
idlergear diff --since 1d      # Changes in last day
idlergear diff --since-commit  # Changes since last git commit
```

## Implementation

### Session Tracking
- Store timestamp of last context query
- Track knowledge state changes
- Compare current vs last snapshot

### Performance
- Fast reads (no GitHub API calls)
- Cache summary data
- <100ms response time

## Acceptance Criteria
- [ ] MCP tools implemented: context_summary, session_diff
- [ ] CLI commands work: summary, diff
- [ ] Diff shows new/changed/closed items
- [ ] --since flag works with time periods
- [ ] Response time <100ms for local backend
- [ ] Tests for all tools
- [ ] Documentation with examples

## Related
- Note #4 (Goose integration analysis)
- #114 (session persistence)
- #113 (status command)

---
id: 30
title: Add smart context windowing (idlergear context --mode smart)
state: open
created: '2026-01-07T01:37:00.140526Z'
labels:
- enhancement
- performance
- ux
priority: medium
---
## Summary
Implement intelligent context prioritization to avoid overwhelming AI assistants with too much information.

## Context
From Goose integration analysis (Note #4): Full context may exceed token limits or include too much noise. Need smart filtering.

## Implementation

```bash
idlergear context --mode smart    # Intelligent prioritization
idlergear context --mode full     # Everything (current behavior)
idlergear context --mode minimal  # Vision + top 3 tasks only
```

## Smart Mode Algorithm

Priority order:
1. **Always include**: Vision, current plan
2. **Recent items** (last 7 days): Tasks, notes
3. **Active runs**: Currently running processes
4. **Referenced items**: References mentioned in recent tasks/notes
5. **Omit**: Closed tasks >30 days old, old notes without tags

## Configuration

```toml
[context]
mode = "smart"  # or "full", "minimal"
max_tokens = 2000
max_age_days = 7
prioritize = ["vision", "tasks", "notes", "runs"]
```

## Output Optimization

- Token counting
- Smart truncation (show first 3 + "... N more")
- Collapsible sections for GUI formats

## Acceptance Criteria
- [ ] Three modes work: smart, full, minimal
- [ ] Smart mode respects max_tokens config
- [ ] Smart mode includes high-priority items even if old
- [ ] Tests for each mode
- [ ] Token estimation accurate
- [ ] Documentation with examples

## Related
- Note #4 (Goose integration analysis)
- #114 (session persistence)
- #113 (status command)

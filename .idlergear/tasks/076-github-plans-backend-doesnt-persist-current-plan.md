---
id: 76
title: GitHub Plans backend doesn't persist current plan selection
state: open
created: '2026-01-09T01:06:19.455925Z'
labels:
- bug
- 'component: backend'
- 'effort: small'
---
## Problem

The `GitHubPlanBackend` class stores `_current_plan` as an instance variable, which means the current plan selection is lost between CLI invocations.

## Current Behavior

```python
class GitHubPlanBackend:
    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path
        self._current_plan: str | None = None  # Lost on each CLI call
```

## Expected Behavior

The current plan should be persisted to `.idlergear/config.toml` or a similar state file, similar to how the local backend works.

## Files

- `src/idlergear/backends/github.py:687` - `GitHubPlanBackend`

## Impact

`idlergear plan switch <name>` works for one command but the selection is lost on the next command.

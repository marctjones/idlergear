---
id: 75
title: GitHub Notes backend doesn't support tags
state: open
created: '2026-01-09T01:06:18.883619Z'
labels:
- bug
- 'component: backend'
- 'effort: small'
---
## Problem

The `GitHubNoteBackend` class in `src/idlergear/backends/github.py` doesn't support the `tags` parameter that the local backend supports.

## Current Behavior

```python
def create(self, content: str) -> dict[str, Any]:
```

The `create` method only accepts `content`, not `tags`.

## Expected Behavior

```python
def create(self, content: str, tags: list[str] | None = None) -> dict[str, Any]:
```

Tags should be mapped to GitHub labels on the issue (e.g., `tag:explore`, `tag:idea`, `tag:bug`).

## Files

- `src/idlergear/backends/github.py:427` - `GitHubNoteBackend.create()`

## Impact

Users with `backends.note = "github"` cannot use `--tag explore` or `--tag idea` when creating notes.

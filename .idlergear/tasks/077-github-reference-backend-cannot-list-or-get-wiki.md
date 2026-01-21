---
id: 77
title: GitHub Reference backend cannot list or get wiki pages
state: open
created: '2026-01-09T01:06:20.200380Z'
labels:
- bug
- 'component: backend'
- 'effort: medium'
---
## Problem

The `GitHubReferenceBackend` class has stub implementations for `list()` and `get()` that return empty/None because GitHub doesn't have a wiki listing API.

## Current Behavior

```python
def list(self) -> list[dict[str, Any]]:
    # GitHub doesn't have a wiki list API
    # Would need to clone wiki repo to list pages
    return []

def get(self, title: str) -> dict[str, Any] | None:
    # Would need to clone wiki repo to get content
    return None
```

## Proposed Solution

Clone the wiki repo to a cache directory (`.idlergear/.wiki-cache/`) and operate on the local clone:

```python
def _ensure_wiki_cloned(self) -> Path:
    cache_dir = self.project_path / ".idlergear" / ".wiki-cache"
    if not cache_dir.exists():
        # Clone: git clone https://github.com/owner/repo.wiki.git .wiki-cache
        ...
    return cache_dir
```

Then `list()` can glob `*.md` files and `get()` can read them directly.

## Related Issues

- #116 - Add `idlergear reference sync` for bidirectional wiki synchronization
- #117 - Fix GitHubReferenceBackend to correctly sync with GitHub Wiki

## Files

- `src/idlergear/backends/github.py:600` - `GitHubReferenceBackend`

## Impact

Users with `backends.reference = "github"` cannot list or view references.

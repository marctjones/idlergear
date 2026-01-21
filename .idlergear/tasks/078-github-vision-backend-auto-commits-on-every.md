---
id: 78
title: GitHub Vision backend auto-commits on every vision edit
state: open
created: '2026-01-09T01:06:20.722012Z'
labels:
- enhancement
- 'component: backend'
- 'effort: small'
---
## Problem

The `GitHubVisionBackend.set()` method automatically commits the vision change, which may not be desired behavior.

## Current Behavior

```python
def set(self, content: str) -> None:
    vision_path = self.project_path / self.VISION_FILE
    vision_path.write_text(content)

    # Optionally commit the change
    try:
        subprocess.run(["git", "add", self.VISION_FILE], ...)
        subprocess.run(["git", "commit", "-m", "Update project vision"], ...)
    except subprocess.CalledProcessError:
        pass
```

## Issues

1. Auto-commits may create many small commits
2. Commit message is hardcoded and not descriptive
3. No option to disable auto-commit
4. Should this push automatically? Currently doesn't.

## Proposed Solution

1. Add config option `vision.auto_commit = false`
2. If enabled, use a more descriptive commit message
3. Consider adding `idlergear vision sync` command for explicit push

## Files

- `src/idlergear/backends/github.py:534` - `GitHubVisionBackend`

## Impact

Users may get unexpected commits when editing vision.

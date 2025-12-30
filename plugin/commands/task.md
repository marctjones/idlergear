---
description: Create a new IdlerGear task (syncs to GitHub Issues)
---

Create a new task with the provided description:

```bash
idlergear task create "$ARGUMENTS"
```

The task will be synced to GitHub Issues if the GitHub backend is configured.

Examples:
- `/task Fix the login button styling`
- `/task Add unit tests for auth module --label bug`
- `/task Refactor database queries --label technical-debt`

---
id: 34
title: Add async/daemon-backed operations for fast MCP responses
state: open
created: '2026-01-07T01:37:00.179801Z'
labels:
- enhancement
- performance
- daemon
- 'effort: large'
priority: high
---
## Summary
Implement async operation mode where slow operations (GitHub sync) happen in background via daemon, giving fast responses to AI assistants.

## Context
From Goose integration analysis (Note #4): GitHub API calls can take seconds, blocking AI sessions. Need instant responses with background sync.

## Architecture

```
Goose MCP call → IdlerGear CLI → Daemon queue → GitHub API
                       ↓
                  Instant response
```

## Implementation

### 1. **Async Flag**
```bash
# CLI
idlergear task create "title" --async

# MCP tool
task_create(title="title", async=True)
```

### 2. **Daemon Queue**
- Local storage write (instant)
- Queue GitHub sync operation
- Background worker processes queue
- Status tracking per operation

### 3. **Status Checking**
```bash
idlergear sync status
# Output: "3 pending, 2 syncing, 15 completed"

idlergear sync status --task 42
# Output: "Task #42: synced to GitHub at 2026-01-06 20:30"
```

### 4. **Configuration**
```toml
[sync]
mode = "async"      # or "sync", "manual"
auto_retry = true
max_retries = 3
batch_size = 10     # Batch multiple ops
```

## Behavior Modes

**sync** (current):
- Operation blocks until GitHub completes
- Guaranteed consistency
- Slow (1-3 seconds per operation)

**async** (new):
- Instant local write + response
- GitHub sync in background
- Fast (<100ms)
- Eventual consistency

**manual** (new):
- No auto-sync
- User runs `idlergear sync push` when ready
- Offline-first

## Error Handling

- Failed syncs go to retry queue
- User notification on repeated failures
- Manual resolution: `idlergear sync retry <id>`

## Acceptance Criteria
- [ ] --async flag works on all write operations
- [ ] Daemon queues operations reliably
- [ ] Background worker processes queue
- [ ] Status command shows sync state
- [ ] Failed syncs retry with exponential backoff
- [ ] MCP tools support async mode
- [ ] Config option for default mode
- [ ] Tests for async operations
- [ ] Documentation with examples

## Related
- Note #4 (Goose integration analysis)
- #66 (daemon architecture - dependency)
- #79 (GitHub sync commands)

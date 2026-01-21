---
id: 19
title: Implement daemon-based prompt queue for asynchronous Claude Code task execution
state: closed
created: '2026-01-03T05:44:31.175464Z'
labels:
- enhancement
- 'effort: large'
- 'component: daemon'
- core-v1
priority: high
---
## Summary

Add a daemon-based task queue that allows the CLI to queue prompts for asynchronous execution by Claude Code sessions, with multi-session coordination and result tracking.

## Problem

Analysis of 3,807 Claude Code history entries showed:
- **141 requests** related to session continuity ("continue", "where did we leave off?", "what is next?")
- All Claude Code work is synchronous - no way to queue tasks for later
- No coordination across multiple Claude Code sessions
- No ability to run background analysis while working on other tasks

## Proposed Solution

Transform the IdlerGear daemon into a **task orchestration layer** that:
1. Accepts prompts from CLI and queues them
2. Assigns queued work to available Claude Code sessions
3. Tracks progress and stores results
4. Coordinates across multiple sessions

### Architecture

```
User CLI → Daemon → Prompt Queue → Claude Code Session(s) → Results
```

**Core Components:**
1. **Prompt Queue**: FIFO queue of pending prompts (`.idlergear/daemon/queue.json`)
2. **Session Registry**: Track active Claude Code sessions (`.idlergear/daemon/sessions.json`)
3. **Result Store**: Completed task results (`.idlergear/daemon/results/<task-id>.json`)

### CLI Interface

```bash
# Queue a prompt
idlergear queue add "analyze the codebase and suggest improvements"
# Output: Queued as task q-001

# List queue
idlergear queue list
# Output:
#   q-001 [pending]   "analyze the codebase..."
#   q-002 [active]    "fix critical bug" (session: abc123)

# Check status
idlergear queue status q-001
# Output: Status: in-progress, Assigned to: session-abc123

# Get result (blocking)
idlergear queue result q-001
# Waits until complete, returns result

# Watch queue live
idlergear queue watch
```

### Hook Integration

**SessionStart**: Check daemon for queued prompts, inject into session
```bash
QUEUED_PROMPT=$(idlergear daemon dequeue "$session_id")
# Injects as additionalContext
```

**Stop**: Block session end if pending work
```bash
PENDING=$(idlergear daemon queue-length)
if [ "$PENDING" -gt 0 ]; then
  # Block stop, prompt to pick up next task
fi
```

**PostToolUse**: Send progress updates to daemon
```bash
idlergear daemon update "$task_id" --progress "Modified files"
```

### Daemon API (Unix Socket)

JSON-RPC 2.0 protocol over `.idlergear/daemon/daemon.sock`:

```json
// Request
{
  "jsonrpc": "2.0",
  "method": "queue.add",
  "params": {"prompt": "...", "priority": "normal"},
  "id": 1
}

// Response
{
  "jsonrpc": "2.0",
  "result": {"task_id": "q-001", "status": "queued"},
  "id": 1
}
```

**API Methods:**
- `queue.add(prompt, priority)` - Add to queue
- `queue.list(status)` - List tasks
- `queue.dequeue(session_id)` - Get next task for session
- `queue.status(task_id)` - Get task status
- `queue.result(task_id)` - Get result
- `session.register(session_id)` - Register session
- `session.heartbeat(session_id)` - Keep-alive
- `session.complete(task_id, result)` - Report completion

## Use Cases

### 1. Background Analysis
```bash
# Queue long-running task
idlergear queue add "analyze entire codebase for security vulnerabilities"

# Continue working on other things
# Claude session picks it up automatically
# Check later for results
idlergear queue result q-001
```

### 2. Batch Processing
```bash
# Queue multiple tasks
idlergear queue add "refactor authentication module"
idlergear queue add "add tests for payment processing"
idlergear queue add "update API documentation"

# Let Claude work through the queue
idlergear queue watch
```

### 3. Cross-Session Handoff
```bash
# Terminal 1: Start work
idlergear queue add "implement user authentication"

# Terminal 2: Different Claude session picks it up
# Claude sees: "You have been assigned a queued task: implement user authentication"
```

## Implementation Plan

### Phase 1: Daemon Core
- [ ] Implement queue management (add, list, dequeue, status)
- [ ] Implement session registry (register, heartbeat, monitor)
- [ ] Implement result store (save, retrieve)
- [ ] Unix socket API with JSON-RPC protocol

### Phase 2: CLI Integration
- [ ] `idlergear queue add/list/status/result/watch` commands
- [ ] `idlergear daemon start/stop/status` commands
- [ ] Socket client for CLI ↔ daemon communication

### Phase 3: Hook Integration
- [ ] SessionStart hook: dequeue tasks
- [ ] Stop hook: check for pending work
- [ ] PostToolUse hook: progress updates

### Phase 4: Advanced Features
- [ ] Session monitoring (detect dead sessions, reassign work)
- [ ] Priority queue (high-priority tasks jump ahead)
- [ ] Retry logic (auto-reassign failed tasks)
- [ ] Task timeout handling
- [ ] Result pagination and cleanup

## Technical Details

### Queue Data Structure
```json
{
  "id": "q-001",
  "prompt": "analyze the codebase",
  "priority": "normal",
  "status": "pending",
  "created": "2026-01-03T10:00:00Z",
  "assigned_to": null,
  "started": null,
  "completed": null
}
```

### Session Registry
```json
{
  "session-abc123": {
    "status": "active",
    "started": "2026-01-03T10:00:00Z",
    "last_heartbeat": "2026-01-03T10:05:00Z",
    "current_task": "q-001",
    "pid": 12345
  }
}
```

### Result Store
```json
{
  "task_id": "q-001",
  "status": "completed",
  "started": "2026-01-03T10:00:00Z",
  "completed": "2026-01-03T10:15:00Z",
  "duration_seconds": 900,
  "result": {
    "summary": "Analysis complete. Found 5 improvement areas.",
    "artifacts": {
      "tasks_created": [42, 43, 44],
      "references_added": ["architecture-improvements"],
      "files_modified": ["src/main.py"]
    }
  },
  "session_id": "session-abc123"
}
```

## Advantages

1. **Asynchronous Work** - Queue tasks, get results later
2. **Multi-Session Coordination** - Distribute work across multiple Claude instances
3. **Persistence** - Tasks survive Claude Code restarts
4. **Progress Tracking** - Real-time updates on long-running work
5. **Load Balancing** - Auto-assign to available sessions
6. **Retry Logic** - Auto-reassign failed tasks
7. **Priority Queue** - High-priority tasks jump the line

## Vision Alignment

From DESIGN.md:
> "IdlerGear is structured project management for AI-assisted development"

The daemon queue extends this to **orchestrated AI-assisted development** - coordinating multiple AI sessions working on queued tasks.

## Related Issues

- #114 - Session state persistence (daemon stores session context)
- #113 - Status command (daemon tracks overall status)
- #66 - Unified daemon architecture (this builds on it)
- #80 - Event bus (queue is a specialized event bus)
- #75 - Multi-instance coordination (queue solves this)

## Acceptance Criteria

- [ ] CLI can queue prompts: `idlergear queue add "..."`
- [ ] CLI can list queue: `idlergear queue list`
- [ ] CLI can check status: `idlergear queue status <id>`
- [ ] CLI can get results: `idlergear queue result <id>`
- [ ] SessionStart hook picks up queued tasks
- [ ] Stop hook checks for pending work
- [ ] Daemon monitors sessions (heartbeat, dead session detection)
- [ ] Results are persisted and retrievable
- [ ] Multiple Claude sessions can work on different queued tasks
- [ ] Failed tasks are auto-reassigned
- [ ] MCP tools available for queue operations

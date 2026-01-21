---
id: 18
title: Implement daemon-based task queue for asynchronous prompt execution
state: closed
created: '2026-01-03T05:37:54.904837Z'
labels:
- enhancement
- 'priority: high'
- 'effort: large'
- core-v1
- 'component: daemon'
priority: high
---
## Summary

Add daemon-based task queue that allows queuing prompts from CLI to be executed asynchronously by Claude Code sessions. Enables background work, multi-session coordination, and long-running task management.

## Problem

Currently:
- All work is synchronous - user must wait for Claude to finish
- No way to queue work for later execution
- Can't coordinate work across multiple Claude Code sessions
- Long-running tasks block the terminal
- Tasks don't survive Claude Code restarts

## Proposed Solution

Transform IdlerGear daemon into a **task orchestration layer** with:
- **Prompt Queue**: FIFO queue of pending prompts
- **Session Registry**: Track active Claude Code sessions
- **Result Store**: Completed task results
- **Unix Socket API**: JSON-RPC interface for CLI communication

## Architecture

```
User CLI → Daemon Queue → Claude Code Session → Results → CLI
```

**Flow:**
1. User runs `idlergear queue add "analyze codebase"`
2. Daemon stores prompt in queue
3. SessionStart hook queries daemon for pending work
4. Claude picks up queued prompt and executes
5. PostToolUse hook reports progress to daemon
6. Results stored, CLI can poll for completion

## CLI Interface

```bash
# Queue management
idlergear queue add "analyze the codebase" [--priority high]
idlergear queue list
idlergear queue status <task-id>
idlergear queue result <task-id> [--wait]
idlergear queue watch  # Live view

# Daemon operations
idlergear daemon start [--auto-queue]
idlergear daemon stop
idlergear daemon status
```

## Core Components

### 1. Prompt Queue (`.idlergear/daemon/queue.json`)

```json
{
  "queue": [
    {
      "id": "q-001",
      "prompt": "analyze the codebase",
      "priority": "normal",
      "status": "pending|active|completed|failed",
      "assigned_to": "session-id",
      "created": "2026-01-03T10:00:00Z",
      "metadata": {
        "timeout": 3600,
        "retry_count": 0
      }
    }
  ]
}
```

### 2. Session Registry (`.idlergear/daemon/sessions.json`)

```json
{
  "sessions": {
    "session-abc123": {
      "status": "idle|active|dead",
      "last_heartbeat": "2026-01-03T10:05:00Z",
      "current_task": "q-001",
      "capabilities": ["code", "analysis"]
    }
  }
}
```

### 3. Unix Socket API

**Socket:** `.idlergear/daemon/daemon.sock`

**Protocol:** JSON-RPC 2.0

**Methods:**
- `queue.add(prompt, priority)` - Enqueue prompt
- `queue.dequeue(session_id)` - Get next task for session
- `queue.status(task_id)` - Get task status
- `queue.result(task_id)` - Get result
- `session.register(session_id)` - Register session
- `session.heartbeat(session_id)` - Keep-alive
- `session.complete(task_id, result)` - Report completion

## Hook Integration

### SessionStart Hook

```bash
# Check daemon for queued work
QUEUED_PROMPT=$(idlergear daemon dequeue "$session_id")

if [ -n "$QUEUED_PROMPT" ]; then
  TASK_ID=$(echo "$QUEUED_PROMPT" | jq -r '.id')
  PROMPT=$(echo "$QUEUED_PROMPT" | jq -r '.prompt')
  
  cat <<EOF
{
  "additionalContext": "=== QUEUED TASK: ${TASK_ID} ===\n\n${PROMPT}\n\nReport completion: idlergear daemon report ${TASK_ID}"
}
EOF
fi
```

### Stop Hook

```bash
# Check for more queued work before allowing stop
PENDING_COUNT=$(idlergear daemon queue-length)

if [ "$PENDING_COUNT" -gt 0 ]; then
  echo '{"decision": "block", "reason": "Queue has pending tasks"}'
fi
```

### PostToolUse Hook

```bash
# Send progress updates for queued tasks
CURRENT_TASK=$(idlergear daemon current-task "$session_id")

if [ -n "$CURRENT_TASK" ]; then
  idlergear daemon update "$CURRENT_TASK" --progress "..."
fi
```

## Daemon Implementation

### Core Daemon (Python)

```python
class IdlerGearDaemon:
    def __init__(self):
        self.queue = []
        self.sessions = {}
        self.socket_path = ".idlergear/daemon/daemon.sock"
    
    async def start(self):
        """Start Unix socket server."""
        server = await asyncio.start_unix_server(
            self.handle_client,
            path=self.socket_path
        )
        
        # Background tasks
        asyncio.create_task(self.monitor_sessions())
        asyncio.create_task(self.auto_assign_tasks())
        
        async with server:
            await server.serve_forever()
    
    async def handle_client(self, reader, writer):
        """Handle JSON-RPC requests."""
        data = await reader.read(4096)
        request = json.loads(data.decode())
        
        result = self.dispatch(request["method"], request["params"])
        
        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": request["id"]
        }
        
        writer.write(json.dumps(response).encode())
        await writer.drain()
        writer.close()
    
    def queue_add(self, prompt, priority="normal"):
        """Add to queue."""
        task = {
            "id": f"q-{len(self.queue)+1:03d}",
            "prompt": prompt,
            "priority": priority,
            "status": "pending"
        }
        self.queue.append(task)
        return task["id"]
    
    def queue_dequeue(self, session_id):
        """Assign next task to session."""
        for task in sorted(self.queue, key=lambda t: t["priority"]):
            if task["status"] == "pending":
                task["status"] = "active"
                task["assigned_to"] = session_id
                return task
        return None
    
    async def monitor_sessions(self):
        """Detect dead sessions and reassign tasks."""
        while True:
            await asyncio.sleep(30)
            for sid, session in self.sessions.items():
                if session.is_dead():
                    self.requeue_task(session["current_task"])
```

## Use Cases

### 1. Background Analysis

```bash
# Queue long-running analysis, continue working
idlergear queue add "analyze codebase for security issues" --priority high

# Check later
idlergear queue result q-001
```

### 2. Batch Processing

```bash
# Queue multiple tasks
idlergear queue add "refactor auth module"
idlergear queue add "add tests for payments"
idlergear queue add "update API docs"

# Watch progress
idlergear queue watch
```

### 3. Cross-Session Coordination

```bash
# Terminal 1: Queue work
idlergear queue add "implement feature X"

# Terminal 2: Different Claude session picks it up automatically
```

## Advantages

1. **Async execution** - Queue and forget
2. **Multi-session** - Load balance across Claude instances
3. **Persistence** - Survives restarts
4. **Progress tracking** - Real-time updates
5. **Retry logic** - Auto-reassign failed tasks
6. **Priority queue** - Urgent work first

## Implementation Phases

### Phase 1: Core Daemon
- [ ] Implement queue data structure
- [ ] Create Unix socket server
- [ ] Add JSON-RPC handler
- [ ] Implement queue.add/dequeue methods
- [ ] Add session registry

### Phase 2: CLI Commands
- [ ] `idlergear queue add`
- [ ] `idlergear queue list`
- [ ] `idlergear queue status`
- [ ] `idlergear queue result`
- [ ] `idlergear daemon start/stop/status`

### Phase 3: Hook Integration
- [ ] SessionStart picks up queued tasks
- [ ] Stop hook checks for pending work
- [ ] PostToolUse sends progress updates
- [ ] Session heartbeat mechanism

### Phase 4: Advanced Features
- [ ] Priority queue
- [ ] Task timeout handling
- [ ] Dead session detection
- [ ] Auto-retry failed tasks
- [ ] Result persistence
- [ ] Live queue watching (`idlergear queue watch`)

## Acceptance Criteria

- [ ] Daemon starts and accepts connections
- [ ] CLI can queue prompts via Unix socket
- [ ] SessionStart hook picks up queued prompts
- [ ] Claude executes queued work
- [ ] Results stored and retrievable
- [ ] Stop hook prevents stopping with pending work
- [ ] Dead session detection and task reassignment
- [ ] Multiple sessions can work from same queue
- [ ] Priority queue working (high priority first)
- [ ] Progress updates from hooks

## Related

- Issue #4 (SessionStart hook)
- Issue #6 (Stop hook)
- Issue #8 (PostToolUse hook)
- Reference: "Daemon Queue Architecture - Multi-Session Orchestration"
- Note #1: Exploration of daemon queue concept

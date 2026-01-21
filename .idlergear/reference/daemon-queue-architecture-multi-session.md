---
id: 1
title: Daemon Queue Architecture - Multi-Session Orchestration
created: '2026-01-03T05:37:11.815412Z'
updated: '2026-01-03T05:37:11.815425Z'
---
# IdlerGear Daemon Queue Architecture

## Overview

Transform the IdlerGear daemon into a **task orchestration layer** that queues prompts from CLI and coordinates execution across Claude Code sessions.

## Architecture

```
┌─────────────────┐
│   User CLI      │
│  Terminal 1-N   │
└────────┬────────┘
         │ idlergear queue add "..."
         ↓
┌─────────────────────────────────────┐
│      IdlerGear Daemon               │
│  ┌─────────────────────────────┐   │
│  │   Prompt Queue (FIFO)       │   │
│  │  1. analyze codebase        │   │
│  │  2. refactor auth           │   │
│  │  3. write tests             │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │   Session Registry          │   │
│  │  - session-abc (active)     │   │
│  │  - session-def (idle)       │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │   Result Store              │   │
│  │  task-1: completed          │   │
│  │  task-2: in-progress        │   │
│  └─────────────────────────────┘   │
└──────────┬──────────────────────────┘
           │ SessionStart hook queries
           ↓
┌─────────────────────────────────────┐
│    Claude Code Session(s)           │
│  - Picks up queued prompt           │
│  - Executes work                    │
│  - Reports back to daemon           │
└─────────────────────────────────────┘
```

## Core Components

### 1. Prompt Queue

**Location:** `.idlergear/daemon/queue.json`

```json
{
  "queue": [
    {
      "id": "q-001",
      "prompt": "analyze the codebase and suggest improvements",
      "priority": "normal",
      "created": "2026-01-03T10:00:00Z",
      "status": "pending",
      "assigned_to": null,
      "requester": "cli",
      "metadata": {
        "timeout": 3600,
        "retry_count": 0,
        "tags": ["analysis"]
      }
    }
  ]
}
```

**Operations:**
- `enqueue(prompt, priority)` - Add to queue
- `dequeue(session_id)` - Assign to session
- `peek()` - View next item without removing
- `requeue(id)` - Put failed task back

### 2. Session Registry

**Location:** `.idlergear/daemon/sessions.json`

```json
{
  "sessions": {
    "session-abc123": {
      "status": "active",
      "started": "2026-01-03T10:00:00Z",
      "last_heartbeat": "2026-01-03T10:05:00Z",
      "current_task": "q-001",
      "capabilities": ["code", "analysis"],
      "pid": 12345
    }
  }
}
```

**Session States:**
- `idle` - Session active but no work
- `active` - Currently executing task
- `dead` - No heartbeat (reassign work)

### 3. Result Store

**Location:** `.idlergear/daemon/results/<task-id>.json`

```json
{
  "task_id": "q-001",
  "status": "completed",
  "started": "2026-01-03T10:00:00Z",
  "completed": "2026-01-03T10:15:00Z",
  "duration_seconds": 900,
  "result": {
    "summary": "Analysis complete. Found 5 improvement areas.",
    "details": "...",
    "artifacts": {
      "tasks_created": [42, 43, 44],
      "references_added": ["architecture-improvements"],
      "files_modified": ["src/main.py"]
    }
  },
  "session_id": "session-abc123"
}
```

## CLI Interface

### Queue Management

```bash
# Add prompt to queue
idlergear queue add "analyze the codebase and suggest improvements"
# Output: Queued as task q-001. Run 'idlergear queue status q-001' to check progress.

# Add with priority
idlergear queue add "fix critical bug" --priority high

# List queue
idlergear queue list
# Output:
#   q-001 [pending]   "analyze the codebase..."
#   q-002 [active]    "fix critical bug" (session: abc123)
#   q-003 [completed] "write tests"

# Check specific task
idlergear queue status q-001
# Output:
#   Status: in-progress
#   Assigned to: session-abc123
#   Started: 2 minutes ago
#   Progress: Running analysis... (45% complete)

# Get result (blocking wait)
idlergear queue result q-001
# Waits until complete, then returns result

# Get result (non-blocking)
idlergear queue result q-001 --no-wait
# Returns immediately with status

# Watch queue
idlergear queue watch
# Live-updating view of queue status
```

### Daemon Operations

```bash
# Start daemon with auto-queue enabled
idlergear daemon start --auto-queue

# Stop daemon gracefully
idlergear daemon stop

# Check daemon status
idlergear daemon status
# Output:
#   Daemon: running (PID 12345)
#   Active sessions: 2
#   Queue length: 3
#   Completed today: 15
```

## Hook Integration

### SessionStart Hook - Pick Up Queued Work

```bash
#!/bin/bash
# .claude/hooks/session-start.sh

# Check daemon for queued prompts
QUEUED_PROMPT=$(idlergear daemon dequeue "$session_id" 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$QUEUED_PROMPT" ]; then
  # Got a queued task
  TASK_ID=$(echo "$QUEUED_PROMPT" | jq -r '.id')
  PROMPT=$(echo "$QUEUED_PROMPT" | jq -r '.prompt')
  
  # Inject as additional context
  cat <<EOF
{
  "additionalContext": "=== QUEUED TASK: ${TASK_ID} ===\n\nYou have been assigned a queued task:\n\n${PROMPT}\n\nPlease complete this task. Report results when done using:\n  idlergear daemon report ${TASK_ID} \"<summary>\" --details \"...\"\n\n=== END QUEUED TASK ==="
}
EOF
fi

# Also load regular context
CONTEXT=$(idlergear context --format compact 2>/dev/null)
if [ $? -eq 0 ]; then
  cat <<EOF
{
  "additionalContext": "=== PROJECT CONTEXT ===\n\n$CONTEXT\n\n=== END CONTEXT ==="
}
EOF
fi
```

### Stop Hook - Check for More Work

```bash
#!/bin/bash
# .claude/hooks/stop.sh

# Check if there's more queued work
PENDING_COUNT=$(idlergear daemon queue-length 2>/dev/null || echo 0)

if [ "$PENDING_COUNT" -gt 0 ]; then
  cat <<EOF
{
  "decision": "block",
  "reason": "There are ${PENDING_COUNT} tasks in the queue. Pick up next task before stopping?"
}
EOF
  exit 0
fi

echo '{"decision": "approve"}'
exit 0
```

### PostToolUse Hook - Progress Updates

```bash
#!/bin/bash
# .claude/hooks/post-tool-use.sh

# If working on a queued task, send progress updates
CURRENT_TASK=$(idlergear daemon current-task "$session_id" 2>/dev/null)

if [ -n "$CURRENT_TASK" ]; then
  # Extract progress indicator (heuristic)
  TOOL=$(echo "$INPUT" | jq -r '.tool_name')
  
  if [[ "$TOOL" =~ (Write|Edit) ]]; then
    idlergear daemon update "$CURRENT_TASK" --progress "Modified files"
  elif [[ "$TOOL" == "Bash" ]]; then
    idlergear daemon update "$CURRENT_TASK" --progress "Running commands"
  fi
fi
```

## Daemon API (Unix Socket)

**Socket:** `.idlergear/daemon/daemon.sock`

### Protocol (JSON-RPC over Unix socket)

```json
// Request
{
  "jsonrpc": "2.0",
  "method": "queue.add",
  "params": {
    "prompt": "analyze the codebase",
    "priority": "normal"
  },
  "id": 1
}

// Response
{
  "jsonrpc": "2.0",
  "result": {
    "task_id": "q-001",
    "status": "queued",
    "position": 3
  },
  "id": 1
}
```

### API Methods

| Method | Description |
|--------|-------------|
| `queue.add(prompt, priority)` | Add to queue |
| `queue.list(status)` | List tasks |
| `queue.dequeue(session_id)` | Get next task for session |
| `queue.status(task_id)` | Get task status |
| `queue.result(task_id)` | Get result |
| `session.register(session_id, capabilities)` | Register session |
| `session.heartbeat(session_id)` | Keep-alive |
| `session.complete(task_id, result)` | Report completion |
| `session.list()` | List active sessions |

## Implementation

### Daemon Core (Python)

```python
import asyncio
import json
from pathlib import Path
from datetime import datetime
import socket

class IdlerGearDaemon:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.queue_file = data_dir / "queue.json"
        self.sessions_file = data_dir / "sessions.json"
        self.results_dir = data_dir / "results"
        self.socket_path = data_dir / "daemon.sock"
        
        self.queue = []
        self.sessions = {}
        
    async def start(self):
        """Start the daemon."""
        # Load state
        self.load_state()
        
        # Start Unix socket server
        server = await asyncio.start_unix_server(
            self.handle_client,
            path=str(self.socket_path)
        )
        
        # Start background tasks
        asyncio.create_task(self.monitor_sessions())
        asyncio.create_task(self.auto_assign_tasks())
        
        print(f"Daemon listening on {self.socket_path}")
        async with server:
            await server.serve_forever()
    
    async def handle_client(self, reader, writer):
        """Handle JSON-RPC requests."""
        data = await reader.read(4096)
        request = json.loads(data.decode())
        
        method = request["method"]
        params = request.get("params", {})
        
        # Dispatch to handler
        if method == "queue.add":
            result = self.queue_add(**params)
        elif method == "queue.dequeue":
            result = self.queue_dequeue(params["session_id"])
        # ... other methods ...
        
        response = {
            "jsonrpc": "2.0",
            "result": result,
            "id": request["id"]
        }
        
        writer.write(json.dumps(response).encode())
        await writer.drain()
        writer.close()
    
    def queue_add(self, prompt: str, priority: str = "normal"):
        """Add prompt to queue."""
        task = {
            "id": f"q-{len(self.queue)+1:03d}",
            "prompt": prompt,
            "priority": priority,
            "status": "pending",
            "created": datetime.now().isoformat(),
            "assigned_to": None
        }
        
        self.queue.append(task)
        self.save_queue()
        
        return {"task_id": task["id"], "status": "queued"}
    
    def queue_dequeue(self, session_id: str):
        """Assign next task to session."""
        # Find highest priority pending task
        for task in sorted(self.queue, key=lambda t: t["priority"]):
            if task["status"] == "pending":
                task["status"] = "active"
                task["assigned_to"] = session_id
                task["started"] = datetime.now().isoformat()
                self.save_queue()
                return task
        
        return None  # No tasks available
    
    async def monitor_sessions(self):
        """Check for dead sessions and reassign work."""
        while True:
            await asyncio.sleep(30)  # Every 30s
            
            now = datetime.now()
            for session_id, session in self.sessions.items():
                last_heartbeat = datetime.fromisoformat(session["last_heartbeat"])
                
                # If no heartbeat for 2 minutes, mark dead
                if (now - last_heartbeat).seconds > 120:
                    session["status"] = "dead"
                    
                    # Reassign current task
                    if session.get("current_task"):
                        self.requeue_task(session["current_task"])
            
            self.save_sessions()
    
    async def auto_assign_tasks(self):
        """Auto-assign tasks to idle sessions."""
        while True:
            await asyncio.sleep(5)  # Every 5s
            
            # Find idle sessions
            idle_sessions = [
                sid for sid, s in self.sessions.items()
                if s["status"] == "idle"
            ]
            
            # Assign pending tasks
            for session_id in idle_sessions:
                task = self.queue_dequeue(session_id)
                if task:
                    # Trigger session via signal or file
                    self.notify_session(session_id, task)
```

### CLI Client

```python
def send_daemon_request(method: str, params: dict = None):
    """Send request to daemon via Unix socket."""
    sock_path = Path.home() / ".idlergear/daemon/daemon.sock"
    
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1
    }
    
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(str(sock_path))
        sock.sendall(json.dumps(request).encode())
        response = json.loads(sock.recv(4096).decode())
    
    return response["result"]

# CLI commands
@app.command()
def queue_add(prompt: str, priority: str = "normal"):
    """Add prompt to daemon queue."""
    result = send_daemon_request("queue.add", {
        "prompt": prompt,
        "priority": priority
    })
    print(f"Queued as task {result['task_id']}")
```

## Use Cases

### 1. Background Analysis

```bash
# Queue long-running analysis
idlergear queue add "analyze entire codebase for security vulnerabilities" --priority high

# Continue working on other things
# Claude Code session picks it up automatically
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

## Advantages

1. **Async Work** - Queue tasks, get results later
2. **Multi-Session** - Coordinate across multiple Claude instances
3. **Persistence** - Tasks survive Claude Code restarts
4. **Progress Tracking** - Real-time updates on long-running work
5. **Load Balancing** - Distribute work across available sessions
6. **Retry Logic** - Auto-reassign failed tasks
7. **Priority Queue** - High-priority tasks jump the line

## Integration with Existing Features

- **Tasks (#114)**: Queue can create IdlerGear tasks for tracking
- **Runs (#54)**: Queue can monitor long-running processes
- **SessionStart (#4)**: Hook checks queue automatically
- **Stop (#6)**: Hook prevents stopping if work queued

## Next Steps

1. Implement daemon core with queue management
2. Add Unix socket API
3. Create CLI commands (queue add/list/result)
4. Integrate with SessionStart hook
5. Add progress tracking
6. Build session monitoring
7. Add result persistence

---
id: 1
title: CLI Commands for Multi-Agent Communication
created: '2026-01-07T05:17:11.203559Z'
updated: '2026-01-07T05:17:11.203577Z'
---
# CLI Commands for Multi-Agent Communication

IdlerGear provides CLI commands to interrogate the daemon and pass messages to AI assistants working on the same codebase.

## Available Commands

### `idlergear daemon queue <command>`
Queue a command for execution by any available AI agent.

**Usage:**
```bash
# Queue a command
idlergear daemon queue "implement feature X"

# Queue with priority (1-10, higher = more urgent)
idlergear daemon queue "fix critical bug" --priority 10

# Queue and wait for completion
idlergear daemon queue "run tests" --wait
```

**Workflow:**
1. User runs CLI command → Daemon queues the command
2. Any active AI agent picks it up from the queue
3. Agent executes and stores result
4. User can retrieve result or wait for completion

### `idlergear daemon send <message>`
Broadcast a message to all active AI agents.

**Usage:**
```bash
# Send a message to all agents
idlergear daemon send "Please focus on the authentication module"

# Notify agents of external changes
idlergear daemon send "Database schema updated, refresh your context"
```

**Use cases:**
- Coordinate work across multiple AI sessions
- Notify agents of external changes
- Provide context or instructions to all agents

### `idlergear daemon agents`
List all active AI agents connected to the daemon.

**Usage:**
```bash
idlergear daemon agents
```

**Output:**
```
Active agents (2):

  • Claude Code Session 1
    ID:     abc123
    Status: busy
    Type:   claude-code
    Task:   Implementing auth feature

  • Goose Terminal
    ID:     def456
    Status: idle
    Type:   goose
```

### `idlergear daemon queue-list`
List all queued commands and their status.

**Usage:**
```bash
idlergear daemon queue-list
```

**Output:**
```
Queued commands (3):

  [a1b2c3d4]
    Status:   completed
    Command:  implement feature X
    Priority: 5

  [e5f6g7h8]
    Status:   running
    Command:  run tests
    Priority: 8
    Agent:    abc123

  [i9j0k1l2]
    Status:   pending
    Command:  fix bug in auth
    Priority: 10
```

### `idlergear daemon status`
Check daemon status and see connected agents.

**Usage:**
```bash
idlergear daemon status
```

**Output:**
```
Daemon: running
  PID: 12345
  Socket: /path/to/project/.idlergear/daemon.sock
  Connections: 2
```

## Multi-Agent Workflow Examples

### Example 1: Queue Long-Running Tasks
```bash
# In terminal: queue a task for background execution
idlergear daemon queue "run full test suite and report results" --priority 3

# Claude Code session picks it up automatically
# User continues working while tests run
# Later, check results with queue-list
```

### Example 2: Coordinate Multiple AI Sessions
```bash
# Terminal 1 (Claude Code): working on frontend
# Terminal 2 (Goose): working on backend

# From CLI, send coordination message:
idlergear daemon send "API schema changed, please review TaskService.ts"

# Both agents receive the message and can adjust their work
```

### Example 3: Monitor Agent Activity
```bash
# Check what agents are active
idlergear daemon agents

# Check what's in the queue
idlergear daemon queue-list

# See overall daemon health
idlergear daemon status
```

## Technical Details

- **Transport**: All commands use the daemon's JSON-RPC API over Unix socket
- **Security**: Same-user only (Unix socket permissions 0600)
- **Persistence**: Queued commands survive daemon restarts
- **Event Bus**: Messages trigger real-time notifications to all agents

## Python Module Usage

If the `idlergear` command has cache issues, use the Python module directly:

```bash
python3 -m idlergear.cli daemon queue "your command"
python3 -m idlergear.cli daemon send "your message"
python3 -m idlergear.cli daemon agents
```

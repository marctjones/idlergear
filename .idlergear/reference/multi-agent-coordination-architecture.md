---
id: 1
title: Multi-Agent Coordination Architecture
created: '2026-01-07T05:13:08.947557Z'
updated: '2026-01-07T05:13:08.947572Z'
---
# Multi-Agent Coordination Architecture

## Overview

IdlerGear's daemon provides multi-agent coordination for multiple AI assistants (Claude Code, Goose, Aider, etc.) working on the same codebase simultaneously.

## Core Components

### 1. Agent Session Registry

Tracks all active AI agent sessions with:
- **Agent ID**: Unique identifier (e.g., "claude-code-session-1")
- **Agent Type**: "claude-code", "goose", "aider", etc.
- **Status**: active, idle, busy
- **Heartbeat**: Last activity timestamp (stale after 5 min)
- **Current Task**: What the agent is working on
- **Capabilities**: What the agent can do

**File**: `src/idlergear/daemon/agents.py`

### 2. Command Queue

Async command execution queue with priorities:
- **States**: pending → assigned → running → completed/failed
- **Priority**: Higher numbers = more urgent
- **Assignment**: Auto-assigned to next available agent
- **Results**: Stored with completion status

**File**: `src/idlergear/daemon/queue.py`

### 3. Write Lock Manager

Prevents conflicting writes across agents:
- **Resources**: "task:42", "vision", "plan:auth-system"
- **Timeout**: Auto-release after 30s (default)
- **Re-acquisition**: Same agent can refresh lock
- **Cleanup**: All locks released when agent disconnects

**File**: `src/idlergear/daemon/locks.py`

### 4. Event Bus

Real-time notifications across agents:
- Subscribe to events: "task.updated", "queue.added", etc.
- Broadcast on state changes
- All connected agents receive updates

**Implemented in**: `src/idlergear/daemon/server.py`

## Multi-Agent Workflow

### Scenario: Claude Code + Goose Working Together

```
# Agent 1 (Claude Code - Terminal)
1. Connect to daemon
2. Register: idlergear_agent_register(agent_id="claude-1", agent_type="claude-code")
3. Subscribe to "task.updated" events
4. Working on backend code

# Agent 2 (Goose - GUI)  
1. Connect to daemon
2. Register: idlergear_agent_register(agent_id="goose-1", agent_type="goose")
3. Poll queue: idlergear_queue_poll(agent_id="goose-1")
4. Pick up frontend task from queue
5. Acquire lock: idlergear_lock_acquire(resource="task:42", agent_id="goose-1")
6. Update task
7. Release lock: idlergear_lock_release(resource="task:42", agent_id="goose-1")
8. Claude receives "task.updated" event notification
```

## Command Queue Usage

### From CLI (Human)

```bash
# Add work to queue
idlergear queue add "refactor authentication system" --priority 5

# Check queue status
idlergear queue list

# View specific command
idlergear queue get <command-id>
```

### From AI Agent

```python
# Poll for work
command = idlergear_queue_poll(agent_id="claude-1")

# Start working
idlergear_queue_start(id=command["id"])
idlergear_agent_update_status(agent_id="claude-1", status="busy", current_task=command["id"])

# Complete work
idlergear_queue_complete(
    id=command["id"],
    result={"files_modified": ["auth.py"], "tests_passed": True}
)
idlergear_agent_update_status(agent_id="claude-1", status="idle")
```

## Write Coordination

### Lock Pattern

```python
# Before modifying shared resource
acquired = idlergear_lock_acquire(resource="vision", agent_id="claude-1", timeout=30)

if acquired:
    # Modify vision
    idlergear_vision_edit(content="Updated vision...")
    
    # Release lock
    idlergear_lock_release(resource="vision", agent_id="claude-1")
else:
    # Resource locked by another agent
    lock_info = idlergear_lock_check(resource="vision")
    # Wait or skip
```

### Auto-Release

- Locks auto-release after timeout (default 30s)
- All locks released when agent disconnects
- Same agent can re-acquire to refresh timeout

## Event Notifications

### Subscribe to Events

```python
# Register and subscribe
idlergear_agent_register(agent_id="claude-1", agent_type="claude-code")
# (Subscription happens via daemon subscribe method)

# Events broadcasted:
- "agent.registered" - New agent connected
- "agent.unregistered" - Agent disconnected
- "agent.status_changed" - Agent status update
- "task.updated" - Task modified
- "task.closed" - Task completed
- "queue.added" - New command queued
- "queue.assigned" - Command assigned to agent
- "queue.completed" - Command finished
- "lock.acquired" - Resource locked
- "lock.released" - Resource unlocked
```

## MCP Tools

All coordination features exposed as MCP tools:

### Agent Management
- `idlergear_agent_register` - Register session
- `idlergear_agent_heartbeat` - Keep session alive
- `idlergear_agent_update_status` - Update status
- `idlergear_agent_list` - List active agents

### Queue Operations  
- `idlergear_queue_add` - Add command
- `idlergear_queue_poll` - Get next work
- `idlergear_queue_list` - View queue
- `idlergear_queue_get` - Get command details
- `idlergear_queue_complete` - Mark done

### Lock Coordination
- `idlergear_lock_acquire` - Acquire lock
- `idlergear_lock_release` - Release lock
- `idlergear_lock_check` - Check lock status

## Daemon Protocol

Communication uses JSON-RPC 2.0 over Unix socket:

```json
{
  "jsonrpc": "2.0",
  "method": "queue.add",
  "params": {
    "prompt": "run tests",
    "priority": 1
  },
  "id": 42
}
```

**Socket**: `.idlergear/daemon.sock`
**Protocol**: Length-prefixed framing (4-byte + message)

## Storage

Daemon state persisted in:

```
.idlergear/
├── daemon.sock          # Unix socket
├── daemon.pid           # Process ID
├── queue/
│   └── queue.json       # Command queue state
└── agents/
    └── agents.json      # Active agent sessions
```

## Cleanup & Maintenance

### Automatic
- Stale agents removed after 5 min no heartbeat
- Completed commands cleaned after 7 days
- Expired locks auto-released

### Manual
- `idlergear daemon status` - Check daemon health
- `idlergear daemon restart` - Restart daemon
- `idlergear queue cleanup` - Remove old commands

## Security

- Unix socket permissions: 0600 (owner only)
- Same-user restriction
- No network exposure
- Locks prevent race conditions

## Use Cases

### 1. Background Analysis
```bash
# User queues analysis
idlergear queue add "analyze codebase for performance issues" --priority 3

# Any idle agent can pick it up
# Results stored in queue for later review
```

### 2. Session Handoff
```
# Claude Code finishes session
idlergear_agent_update_status(agent_id="claude-1", status="idle")

# Goose picks up where it left off
command = idlergear_queue_poll(agent_id="goose-1")
```

### 3. Conflict Prevention
```
# Agent A and Agent B both try to update vision
# Agent A acquires lock first
# Agent B sees lock, waits or skips
```

## Future Enhancements

Planned features:
- Cross-machine coordination (Eddi bridge)
- Agent capabilities matching (route work to capable agents)
- Priority queues per agent type
- Persistent event log
- Dashboard UI for queue/agent visualization

## Related

- **Design Doc**: DESIGN.md (Part 3: Architecture, daemon section)
- **Issues**: #66 (Unified daemon architecture), #19 (Prompt queue)
- **Tests**: `tests/test_daemon.py`

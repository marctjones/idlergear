---
id: 1
title: MCP-Server
created: '2026-01-07T00:09:41.525347Z'
updated: '2026-01-07T00:09:41.525361Z'
---
# MCP Server

IdlerGear exposes 90+ tools via the Model Context Protocol (MCP) for AI assistant integration.

## Overview

The MCP server allows AI assistants to:
- Query project knowledge (tasks, notes, references, etc.)
- Create and modify knowledge
- Manage sessions across conversations
- Coordinate with other AI agents

## Setup

### Claude Code

```bash
idlergear install
```

This creates `.mcp.json`:

```json
{
  "mcpServers": {
    "idlergear": {
      "command": "idlergear",
      "args": ["serve"]
    }
  }
}
```

### Other MCP Clients

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "idlergear": {
      "command": "idlergear",
      "args": ["serve"]
    }
  }
}
```

### Manual Start

```bash
idlergear serve
```

## Tool Categories

### Session Management (4 tools)

| Tool | Description |
|------|-------------|
| `session_start` | Start session, load context + previous state |
| `session_save` | Save current session state |
| `session_end` | End session with state and suggestions |
| `session_status` | Show current session state |

**Recommended:** Call `session_start()` at the beginning of every conversation.

### Context & Status (6 tools)

| Tool | Description |
|------|-------------|
| `context` | Get project context (vision, plan, tasks) |
| `status` | Quick status dashboard |
| `vision_show` | Show project vision |
| `vision_edit` | Edit project vision |
| `search` | Search across all knowledge types |
| `backend_show` | Show configured backends |

### Task Management (6 tools)

| Tool | Description |
|------|-------------|
| `task_create` | Create a new task |
| `task_list` | List tasks (with filters) |
| `task_show` | Show a specific task |
| `task_close` | Close a task |
| `task_update` | Update task fields |
| `task_sync` | Sync with GitHub Issues |

### Note Management (5 tools)

| Tool | Description |
|------|-------------|
| `note_create` | Create a quick note |
| `note_list` | List notes (with tag filter) |
| `note_show` | Show a specific note |
| `note_delete` | Delete a note |
| `note_promote` | Promote to task or reference |

### Plan Management (4 tools)

| Tool | Description |
|------|-------------|
| `plan_create` | Create a plan |
| `plan_list` | List all plans |
| `plan_show` | Show a plan |
| `plan_switch` | Switch to a different plan |

### Reference Management (5 tools)

| Tool | Description |
|------|-------------|
| `reference_add` | Add a reference document |
| `reference_list` | List references |
| `reference_show` | Show a reference |
| `reference_search` | Search references |
| `reference_sync` | Sync with GitHub Wiki |

### Run Management (7 tools)

| Tool | Description |
|------|-------------|
| `run_start` | Start a background run |
| `run_list` | List all runs |
| `run_status` | Get run status |
| `run_logs` | Get run logs |
| `run_stop` | Stop a running process |
| `pm_start_run` | Start with process management |
| `pm_list_runs` | List runs with PM metadata |

### Test Management (10 tools)

| Tool | Description |
|------|-------------|
| `test_detect` | Detect test framework |
| `test_run` | Run tests |
| `test_status` | Show last test status |
| `test_history` | Show test run history |
| `test_list` | List all tests |
| `test_coverage` | Show coverage mapping |
| `test_uncovered` | List untested files |
| `test_changed` | Tests for changed files |
| `test_sync` | Import external test runs |
| `test_staleness` | Check result freshness |

### Watch Mode (3 tools)

| Tool | Description |
|------|-------------|
| `watch_check` | One-shot analysis with suggestions |
| `watch_act` | Execute a specific suggestion |
| `watch_stats` | Watch statistics |

### Project Boards (9 tools)

| Tool | Description |
|------|-------------|
| `project_create` | Create a Kanban board |
| `project_list` | List project boards |
| `project_show` | Show board with columns |
| `project_delete` | Delete a project |
| `project_add_task` | Add task to project |
| `project_remove_task` | Remove task from project |
| `project_move_task` | Move task between columns |
| `project_sync` | Sync with GitHub Projects |
| `project_link` | Link to existing GitHub Project |

### Daemon & Multi-Agent (10 tools)

| Tool | Description |
|------|-------------|
| `daemon_register_agent` | Register as an AI agent |
| `daemon_list_agents` | List connected agents |
| `daemon_queue_command` | Queue work for agents |
| `daemon_broadcast` | Send message to all agents |
| `daemon_update_status` | Update agent status |
| `daemon_list_queue` | List queued commands |
| `message_send` | Send message to specific agent |
| `message_list` | Check inbox |
| `message_process` | Process inbox messages |
| `message_mark_read` | Mark messages as read |

### Filesystem (11 tools)

| Tool | Description |
|------|-------------|
| `fs_read_file` | Read file contents |
| `fs_read_multiple` | Read multiple files |
| `fs_write_file` | Write file contents |
| `fs_create_directory` | Create directory |
| `fs_list_directory` | List directory |
| `fs_directory_tree` | Get directory tree |
| `fs_move_file` | Move/rename file |
| `fs_search_files` | Search by glob pattern |
| `fs_file_info` | Get file metadata |
| `fs_file_checksum` | Calculate checksum |
| `fs_allowed_directories` | List accessible directories |

### Git Integration (18 tools)

| Tool | Description |
|------|-------------|
| `git_status` | Repository status |
| `git_diff` | Show changes |
| `git_log` | Commit history |
| `git_add` | Stage files |
| `git_commit` | Create commit |
| `git_reset` | Unstage/reset |
| `git_show` | Show commit details |
| `git_branch_list` | List branches |
| `git_branch_create` | Create branch |
| `git_branch_checkout` | Switch branch |
| `git_branch_delete` | Delete branch |
| `git_commit_task` | Commit linked to task |
| `git_status_for_task` | Status for task files |
| `git_task_commits` | Commits for a task |
| `git_sync_tasks` | Sync task status from commits |

### Environment (4 tools)

| Tool | Description |
|------|-------------|
| `env_info` | Python/Node/Rust versions |
| `env_which` | Find command in PATH |
| `env_detect` | Detect project type |
| `env_find_venv` | Find virtual environments |

### Process Management (6 tools)

| Tool | Description |
|------|-------------|
| `pm_list_processes` | List running processes |
| `pm_get_process` | Get process details |
| `pm_kill_process` | Kill a process |
| `pm_system_info` | CPU, memory, disk usage |
| `pm_quick_start` | Start foreground process |
| `pm_task_runs` | Runs for a specific task |

### Doctor & Utilities (4 tools)

| Tool | Description |
|------|-------------|
| `doctor` | Check installation health |
| `config_get` | Get config value |
| `config_set` | Set config value |
| `version` | Show IdlerGear version |

## Token Efficiency

MCP tools are designed for token-efficient responses:

### Context Modes

```python
# Minimal (~750 tokens) - DEFAULT
context()
context(mode="minimal")

# Standard (~2500 tokens)
context(mode="standard")

# Detailed (~7000 tokens)
context(mode="detailed")

# Full (~17000+ tokens)
context(mode="full")
```

### Task List Efficiency

```python
# Full list (potentially large)
task_list(state="open")

# Efficient: limit results
task_list(state="open", limit=5)

# Most efficient: preview mode
task_list(state="open", limit=5, preview=True)
```

## Best Practices

### Session Start

Always call `session_start()` at the beginning:

```python
# Loads context + previous session state
result = session_start()
# Returns: vision, plan, tasks, previous working files, notes
```

### Session End

Save state before ending:

```python
session_end(
    current_task_id=42,
    working_files=["src/api.py", "src/models.py"],
    notes="Finished auth, need tests"
)
```

### Knowledge Capture

Create notes for discoveries:

```python
note_create("Parser has a quirk with unicode strings")
note_create("Should we support WebSocket?", tags=["explore"])
```

### Task Workflow

```python
# Create task
task = task_create("Fix auth bug", labels=["bug"])

# Work on it...

# Close when done
task_close(task["id"])
```

## Error Handling

All tools return structured JSON:

### Success

```json
{
  "id": 42,
  "title": "Fix auth bug",
  "state": "open",
  ...
}
```

### Error

```json
{
  "error": "Task not found",
  "id": 999
}
```

## Configuration

### Server Options

```bash
# Start with verbose logging
idlergear serve --verbose

# Custom socket path
idlergear serve --socket /tmp/idlergear.sock
```

### Client Configuration

In `.mcp.json`:

```json
{
  "mcpServers": {
    "idlergear": {
      "command": "idlergear",
      "args": ["serve"],
      "env": {
        "IDLERGEAR_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## Troubleshooting

### "MCP server not responding"

Check if IdlerGear is installed:

```bash
idlergear --version
```

### "Tool not found"

Update IdlerGear:

```bash
idlergear update
```

### "Permission denied"

Check file permissions in `.idlergear/`.

### Debug Mode

```bash
IDLERGEAR_LOG_LEVEL=DEBUG idlergear serve
```

## Related

- [[Architecture]] - System design
- [[Commands-Reference]] - CLI equivalents
- [[Getting-Started]] - Installation

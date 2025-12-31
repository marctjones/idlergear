# MCP Server

IdlerGear provides an MCP (Model Context Protocol) server for direct integration with Claude Code and other MCP-compatible AI assistants.

## Overview

The MCP server exposes IdlerGear's functionality as 35 tools that Claude Code can call directly, without going through the CLI.

## Installation

The MCP server is included with IdlerGear. To configure it for Claude Code:

```bash
idlergear install
```

This creates `.mcp.json`:

```json
{
  "mcpServers": {
    "idlergear": {
      "command": "idlergear-mcp"
    }
  }
}
```

## Available Tools

### Task Tools (7)

| Tool | Description |
|------|-------------|
| `task_create` | Create a new task |
| `task_list` | List all tasks |
| `task_show` | Show task details |
| `task_complete` | Mark task complete |
| `task_reopen` | Reopen a closed task |
| `task_update` | Update task properties |
| `task_delete` | Delete a task |

### Note Tools (5)

| Tool | Description |
|------|-------------|
| `note_create` | Create a quick note |
| `note_list` | List all notes |
| `note_show` | Show note details |
| `note_promote` | Promote to task/explore |
| `note_delete` | Delete a note |

### Exploration Tools (6)

| Tool | Description |
|------|-------------|
| `explore_create` | Start exploration |
| `explore_list` | List explorations |
| `explore_show` | Show exploration |
| `explore_update` | Update exploration |
| `explore_close` | Close exploration |
| `explore_delete` | Delete exploration |

### Vision Tools (3)

| Tool | Description |
|------|-------------|
| `vision_show` | Get project vision |
| `vision_update` | Update vision |
| `vision_history` | View vision history |

### Plan Tools (6)

| Tool | Description |
|------|-------------|
| `plan_create` | Create a plan |
| `plan_list` | List all plans |
| `plan_show` | Show plan details |
| `plan_update` | Update plan |
| `plan_switch` | Switch active plan |
| `plan_delete` | Delete a plan |

### Reference Tools (5)

| Tool | Description |
|------|-------------|
| `reference_add` | Add reference doc |
| `reference_list` | List references |
| `reference_show` | Show reference |
| `reference_search` | Search references |
| `reference_delete` | Delete reference |

### Context Tools (3)

| Tool | Description |
|------|-------------|
| `context_show` | Get full context |
| `context_summary` | Get brief summary |
| `config_get` | Get config value |

## Example Usage

When Claude Code has the MCP server configured, it can use tools directly:

```
Claude: I'll create a task to track this bug.
[Calls task_create with description="Fix null pointer in parser"]

Claude: Let me check the project vision before making changes.
[Calls vision_show]

Claude: I'll add a note about this workaround.
[Calls note_create with content="Using retry loop for flaky API"]
```

## Running the Server

The MCP server runs automatically when Claude Code starts a session. You can also run it manually for testing:

```bash
idlergear-mcp
```

The server communicates via JSON-RPC 2.0 over stdin/stdout.

## Protocol

The server implements MCP (Model Context Protocol):

- **Transport**: stdin/stdout
- **Encoding**: JSON-RPC 2.0
- **Capabilities**: tools

### Initialization

```json
{"jsonrpc": "2.0", "method": "initialize", "params": {...}, "id": 1}
```

### Tool Listing

```json
{"jsonrpc": "2.0", "method": "tools/list", "id": 2}
```

### Tool Invocation

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "task_create",
    "arguments": {"description": "Fix bug"}
  },
  "id": 3
}
```

## Troubleshooting

### Server not starting

Check that IdlerGear is installed:
```bash
which idlergear-mcp
```

### Tools not appearing

Verify `.mcp.json` exists and Claude Code has restarted:
```bash
cat .mcp.json
```

### Permission errors

The MCP server needs access to the project's `.idlergear/` directory. Ensure it exists:
```bash
idlergear init
```

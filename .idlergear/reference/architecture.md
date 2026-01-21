---
id: 1
title: Architecture
created: '2026-01-07T00:09:01.272581Z'
updated: '2026-01-07T00:09:01.272604Z'
---
# Architecture

IdlerGear's system design and technical architecture.

## Overview

- **Python** - Installed via pipx, uses official MCP SDK
- **MCP Server** - AI tool integration (90+ tools)
- **Local-first** - Everything works offline, sync when ready
- **Single daemon per project** (optional) - Multi-agent coordination
- **AI-assistant agnostic** - Works with Claude Code, Goose, Aider, Copilot, Gemini CLI

## Design Principles

### 1. Command API, Not File Conventions

IdlerGear provides a structured API, not file naming conventions:

```bash
# IdlerGear way - same command everywhere
idlergear vision show

# File convention way - varies by project
cat docs/VISION.md  # or README.md? or MISSION.md?
```

The backend is configuration. The interface is constant.

### 2. Local-First, Sync-Later

Everything works offline. No external services required:

```bash
idlergear task create "Fix bug"     # Works offline
idlergear task sync                  # Sync when ready
```

### 3. Observable by AI

Every piece of state can be queried. Responses are structured JSON:

```bash
idlergear --output json task list
```

AI assistants get structured data, not prose to parse.

### 4. Lightweight Defaults

Built-in implementations for all knowledge types. External tools optional:

- Local backend works without GitHub
- No database required (uses markdown files)
- Single binary installation

### 5. Deterministic

Regular code, not AI magic. Commands are predictable:

```bash
idlergear task list  # Always returns the same format
```

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Assistants                           │
│   Claude Code  │  Goose  │  Aider  │  Copilot  │  Gemini   │
└────────┬────────────┬────────────────────────────────────────┘
         │            │
         │ MCP        │ CLI
         │            │
┌────────▼────────────▼────────────────────────────────────────┐
│                    IdlerGear Core                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ MCP Server  │  │    CLI      │  │   Daemon    │          │
│  │ (90+ tools) │  │ (typer)     │  │ (optional)  │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │              Knowledge Layer                           │  │
│  │  Tasks │ Notes │ Vision │ Plans │ References │ Runs   │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │                                  │
│  ┌────────────────────────▼──────────────────────────────┐  │
│  │              Backend Abstraction                       │  │
│  │     LocalBackend     │     GitHubBackend              │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐            ┌─────────────────┐
│  .idlergear/    │            │     GitHub      │
│  Local Storage  │            │  Issues/Wiki/   │
│                 │            │  Projects       │
└─────────────────┘            └─────────────────┘
```

## File Structure

```
your-project/
├── .idlergear/              # IdlerGear data directory
│   ├── config.toml          # Configuration
│   ├── vision.md            # Project vision
│   ├── state.json           # Session state
│   ├── tasks/               # Task files (local backend)
│   │   ├── 001-fix-bug.md
│   │   └── 002-add-tests.md
│   ├── notes/               # Note files
│   │   └── 001.md
│   ├── plans/               # Plan files
│   │   └── auth-system.md
│   ├── reference/           # Reference documents
│   │   └── api-design.md
│   └── runs/                # Run logs
│       └── backend/
│           ├── command.txt
│           ├── status.txt
│           ├── stdout.log
│           └── stderr.log
├── .claude/                 # Claude Code integration
│   ├── hooks/               # Shell hooks
│   ├── commands/            # Slash commands
│   ├── rules/               # Instructions
│   └── skills/              # Skill definitions
└── .mcp.json                # MCP server configuration
```

## Backend System

IdlerGear uses a backend abstraction layer. Each knowledge type can use a different backend:

### Local Backend

Stores data in `.idlergear/` as markdown files with YAML frontmatter:

```yaml
---
id: 42
title: Fix parser bug
state: open
priority: high
labels: [bug, urgent]
created: 2026-01-10T10:00:00Z
---
The parser fails on compound words...
```

### GitHub Backend

Syncs with GitHub services:

| Knowledge Type | GitHub Service |
|----------------|----------------|
| Tasks | GitHub Issues |
| Notes | GitHub Issues (with "note" label) |
| Vision | VISION.md file in repo |
| Plans | GitHub Projects |
| References | GitHub Wiki |
| Runs | Local only (no sync) |

### Configuration

```toml
# .idlergear/config.toml
[backend]
task = "github"      # or "local"
note = "local"
vision = "local"
plan = "local"
reference = "github" # syncs to wiki
```

## MCP Server

The MCP server exposes IdlerGear as tools for AI assistants:

```python
# Example tools
task_create(title, body=None, labels=[])
task_list(state="open", limit=None)
note_create(content, tags=[])
vision_show()
context(mode="minimal")
session_start()
```

See [[MCP-Server]] for the complete tool reference.

## Daemon Architecture

The optional daemon enables multi-agent coordination:

```
┌─────────────────────────────────────────────────────────┐
│                    IdlerGear Daemon                     │
│                  (Unix socket server)                   │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Agent     │  │   Message   │  │   Command   │     │
│  │  Registry   │  │    Queue    │  │    Queue    │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Claude Code │    │    Goose    │    │   Script    │
│   Session   │    │   Session   │    │   Runner    │
└─────────────┘    └─────────────┘    └─────────────┘
```

Features:
- **Agent Registry** - Track connected AI assistants
- **Message Queue** - Send messages between agents
- **Command Queue** - Queue work for any available agent
- **Broadcast** - Notify all agents of changes

## Session State

IdlerGear persists session state across AI sessions:

```json
{
  "current_task": 42,
  "working_files": ["src/api.py", "src/models.py"],
  "notes": "Implementing OAuth, next: add tests",
  "timestamp": "2026-01-10T15:30:00Z"
}
```

This enables continuity:
- "Where did we leave off?" → Restored automatically
- "What files were we editing?" → Listed
- "What was the context?" → Preserved

## Token Efficiency

IdlerGear is designed for token-efficient AI interactions:

| Mode | Tokens | Use Case |
|------|--------|----------|
| minimal | ~750 | Session start |
| standard | ~2,500 | General work |
| detailed | ~7,000 | Deep planning |
| full | ~17,000+ | Rare, complete view |

This represents a **95-97% reduction** compared to loading full context.

## Event System

Internal event bus for extensibility:

```python
# Subscribe to events
bus.subscribe("task.created", handler)
bus.subscribe("task.*", wildcard_handler)

# Events emitted automatically
# task.created, task.closed, note.created, etc.
```

Used by:
- Watch mode (detect changes)
- Hooks (trigger actions)
- Daemon (broadcast updates)

## Security Model

- **Local-first** - Data stays on your machine by default
- **No telemetry** - No data sent to external services
- **GitHub auth** - Uses `gh` CLI authentication (no stored tokens)
- **Sandboxed** - MCP server runs in project directory only

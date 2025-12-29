# IdlerGear Design

---

## Part 1: Vision

---

### Mission

**IdlerGear is a knowledge management API that synchronizes AI context management with human project management.**

### The Problem

AI coding assistants are stateless. Every session starts fresh. You constantly re-explain:
- What the project is trying to achieve
- What you learned last session about how something works
- What issues were discovered but deferred
- What the current implementation plan is
- What happened when you ran that script

### The Solution

A **command-based API** that manages knowledge across sessions, machines, and teams.

### Key Insight

Context management is an AI problem. Project management is a human problem. **IdlerGear synchronizes them.**

### Why Not Just AGENTS.md?

AGENTS.md defines **file naming conventions**:
> "Look for the vision in docs/VISION.md"

IdlerGear provides a **command-based API**:
```bash
idlergear vision show    # Returns the vision, wherever it's stored
```

The difference:
- **Consistent interface** - Same command across all projects
- **Backend-agnostic** - Could be local file, GitHub, Jira, or central server
- **Configurable** - Project decides where data lives, command stays the same
- **Deterministic** - No AI interpretation needed, just run the command

### What IdlerGear Is NOT

- **Not an IDE** - It manages context, not editing
- **Not a build system** - Use make, cargo, npm for that
- **Not an AI wrapper** - It provides context TO AI tools
- **Not a cloud service** - Runs locally, your data stays local
- **Not enterprise-only** - Works solo, scales to teams

---

## Part 2: Knowledge Model

---

### Eleven Types of Knowledge

IdlerGear manages eleven distinct types of knowledge:

#### 1. Tasks
Things that need to be done. Have a lifecycle (open → in progress → closed). Can be assigned, prioritized, labeled.

```bash
idlergear task create "Fix parser bug"
idlergear task list
idlergear task close 42
```

#### 2. Reference
Explanations of how things work - design decisions, technical docs, world knowledge. Persists long-term, updated as understanding evolves.

```bash
idlergear reference add "GGUF-Format"
idlergear reference search "quantization"
```

#### 3. Explorations
Open-ended questions being explored with context and reasoning. More thought-out than notes - meant to last and be understandable later. Not yet actionable (tasks) or documented (reference). May become either eventually.

```bash
idlergear explore "Should we support Windows?"
idlergear explore list
idlergear explore show 1
```

#### 4. Vision
The "why" - purpose, mission, long-term direction. Protected, rarely changes. Guides decisions across the project.

```bash
idlergear vision show
idlergear vision edit
```

#### 5. Plans
How to achieve a specific goal. Groups related tasks, defines sequence. More tactical than vision, more structured than explorations.

```bash
idlergear plan show
idlergear plan list
idlergear plan switch "auth-system"
```

#### 6. Notes
Quick capture - the post-it note. Unstructured, temporary. Use when you don't want to get distracted or lose context on what you're doing. May become tasks, reference, or explorations later.

```bash
idlergear note "Parser quirk with compound words"
idlergear note list
idlergear note promote 1 --to task
```

#### 7. Outputs
Results from executed processes. Logs, test results, script output. Queryable history of what happened.

```bash
idlergear run ./train.sh --name training
idlergear run status
idlergear run logs training --tail 50
```

#### 8. Contexts
The current state of an AI session - conversation history, model configuration, system prompts. Multiple contexts can exist (different sessions, different agents). Contexts are flat text data that can be saved, restored, and shared.

```bash
idlergear context save "before-refactor"
idlergear context list
idlergear context restore "before-refactor"
```

#### 9. Configuration
Instance-specific settings. API keys, passwords, local paths. Not shared across instances. Persistent but per-machine.

```bash
idlergear config set github.token "..."
idlergear config get github.token
```

#### 10. Resources
Files and data the project operates on - tracked with labels and purpose. Not documentation, not code - the "stuff" being processed or used. Helps remember what files are for and where they are.

```bash
idlergear resource add ./assets/logo.png --label "approved-logo"
idlergear resource add ./data/book.txt --label "source-text"
idlergear resource list
idlergear resource list --label "approved-logo"
```

#### 11. Codebase
Source code, tests, the implementation - everything managed by git. IdlerGear assumes git and GitHub (other git hosts may be supported later). This is the traditional version-controlled codebase, not a new abstraction.

```bash
idlergear code status          # git status with context
idlergear code changed         # files changed since last commit
idlergear code recent          # recent commit history
```

### Four Quadrants

Knowledge exists across two dimensions: **scope** (local vs shared) and **persistence** (volatile vs persistent):

```
                VOLATILE                      PERSISTENT
          ┌─────────────────────────┬─────────────────────────┐
          │                         │                         │
          │  LOCAL VOLATILE         │  LOCAL PERSISTENT       │
  LOCAL   │                         │                         │
          │  • Contexts             │  • .idlergear/ storage  │
          │  • Live outputs         │  • Local config         │
          │  • In-memory state      │  • Saved contexts       │
          │                         │                         │
          ├─────────────────────────┼─────────────────────────┤
          │                         │                         │
          │  SHARED VOLATILE        │  SHARED PERSISTENT      │
  SHARED  │                         │                         │
          │  • Multi-agent coord    │  • GitHub repo          │
          │  • Running process info │  • GitHub/Jira issues   │
          │  • Locks, file changes  │  • Shared wikis         │
          │                         │                         │
          └─────────────────────────┴─────────────────────────┘
```

IdlerGear operates across all four quadrants:
- **Local Volatile** - Context management, live process output
- **Local Persistent** - `.idlergear/` stores knowledge locally
- **Shared Volatile** - Daemon coordinates multiple agents
- **Shared Persistent** - Sync to GitHub, Jira, etc. when ready

---

## Part 3: Architecture

---

### Overview

- **Python** - installed via pipx, uses official MCP SDK
- **Single daemon per project** listening on `.idlergear/daemon.sock`
- **MCP server** for AI tool integration
- **Local-first** - everything works offline, sync when ready
- **Multi-agent coordination** - multiple Claude Code instances share the same daemon
- **Eddi bridge** (later) - cross-machine coordination for distributed teams
- Project state lives in `.idlergear/` directory
- Assumes **git and GitHub** for version control (other git hosts later)
- **AI-tool agnostic** - works with Claude Code, Goose, Aider, Copilot, Gemini CLI, Codex

### Design Principles

#### 1. Command API, Not File Conventions
Same commands everywhere. Backend is configuration.

#### 2. Local-First, Sync-Later
Works offline. No external services required. Sync when ready.

#### 3. Observable by AI
Every piece of state can be queried. Structured responses.

#### 4. Lightweight Defaults
Built-in implementations for all knowledge types. External tools optional.

#### 5. Deterministic
Regular code, not AI magic. Commands are predictable.

---

## Part 4: v1 / MVP

---

### Scope

v1 includes everything with a GitHub analog, plus core infrastructure.

| Type | Local Storage | GitHub Sync |
|------|---------------|-------------|
| Tasks | Markdown + frontmatter | GitHub Issues |
| Notes | Markdown + frontmatter | GitHub Issues (with label) |
| Explorations | Markdown + frontmatter | GitHub Discussions |
| Vision | Single markdown file | Repo file (VISION.md) |
| Plans | Markdown + frontmatter | GitHub Projects |
| Reference | Markdown + frontmatter | GitHub Wiki |
| Outputs | Log files | *(no sync)* |

### Infrastructure

- **Daemon** - socket IPC, process management, serves CLI and MCP
- **MCP Server** - AI tool integration (structured JSON responses)
- **CLI** - human interface (same commands, text output)
- **Config** - `.idlergear/config.toml`

### Commands

```bash
# Setup
idlergear init
idlergear daemon start|stop|status
idlergear config get|set

# Tasks (→ GitHub Issues)
idlergear task create|list|show|close|edit
idlergear task sync github

# Notes (→ GitHub Issues with label)
idlergear note create|list|show|delete
idlergear note promote --to task
idlergear note sync github

# Explorations (→ GitHub Discussions)
idlergear explore create|list|show|close
idlergear explore sync github

# Vision (→ repo VISION.md)
idlergear vision show|edit
idlergear vision sync github

# Plans (→ GitHub Projects)
idlergear plan create|list|show|switch
idlergear plan sync github

# Reference (→ GitHub Wiki)
idlergear reference add|list|show|edit|search
idlergear reference sync github

# Outputs (no sync)
idlergear run ./script.sh --name X
idlergear run list|status|logs
```

### MCP Tools

Same functionality exposed as MCP tools:

```python
# Tasks
idlergear_task_create(title, body=None, labels=[], assignees=[])
idlergear_task_list(state="open")
idlergear_task_show(id)
idlergear_task_close(id)

# Notes
idlergear_note_create(content)
idlergear_note_list()
idlergear_note_promote(id, to="task")

# Explorations
idlergear_explore_create(title, body)
idlergear_explore_list(state="open")

# Vision
idlergear_vision_show()
idlergear_vision_edit(content)

# Plans
idlergear_plan_list()
idlergear_plan_show(name)
idlergear_plan_switch(name)

# Reference
idlergear_reference_add(title, body)
idlergear_reference_list()
idlergear_reference_search(query)

# Runs
idlergear_run_start(command, name=None)
idlergear_run_list()
idlergear_run_status(name)
idlergear_run_logs(name, tail=None)

# Config
idlergear_config_get(key)
idlergear_config_set(key, value)
```

### File Structure

```
.idlergear/
├── config.toml
├── daemon.sock
├── daemon.pid
├── vision.md
├── tasks/
│   ├── 001-fix-parser-bug.md
│   └── 002-add-tests.md
├── notes/
│   └── 001.md
├── explorations/
│   └── 001-windows-support.md
├── plans/
│   └── auth-system.md
├── reference/
│   └── gguf-format.md
└── runs/
    └── training/
        ├── command.txt
        ├── status.txt
        ├── stdout.log
        └── stderr.log
```

### Deferred to Later

- Contexts (AI session state management)
- Resources (file registry with labels)
- Codebase (git wrapper commands)
- Eddi bridge (cross-machine coordination)
- Non-GitHub sync backends (Jira, GitLab, etc.)

---

## Part 5: Implementation Status

---

### Completed (v1 Core)

#### CLI Commands
All core CLI commands are implemented:

| Command Group | Status | Notes |
|---------------|--------|-------|
| `idlergear init` | ✅ Done | Initializes `.idlergear/` directory |
| `idlergear new` | ✅ Done | Creates new projects with full Claude Code integration |
| `idlergear install/uninstall` | ✅ Done | Manages `.mcp.json` and `AGENTS.md` |
| `idlergear task *` | ✅ Done | create, list, show, close, edit |
| `idlergear note *` | ✅ Done | create, list, show, delete, promote |
| `idlergear explore *` | ✅ Done | create, list, show, close |
| `idlergear reference *` | ✅ Done | add, list, show, edit, search |
| `idlergear vision *` | ✅ Done | show, edit |
| `idlergear plan *` | ✅ Done | create, list, show, switch |
| `idlergear run *` | ✅ Done | start, list, status, logs |
| `idlergear config *` | ✅ Done | get, set |

#### MCP Server
- ✅ 30+ tools implemented matching CLI functionality
- ✅ Stdio transport using official MCP SDK
- ✅ Structured JSON responses for AI consumption

#### Project Templates
- ✅ Base template with Claude Code integration
- ✅ Python template with venv auto-activation
- ✅ Protected files (`.idlergear/`, `.claude/`, `.mcp.json`)
- ✅ `CLAUDE.md` and `AGENTS.md` generation

#### Claude Code Integration
The `idlergear new` command creates projects with:
- `.mcp.json` - Registers `idlergear-mcp` server
- `.claude/settings.json` - Permission rules protecting IdlerGear files
- `.claude/rules/` - Modular instructions for Claude
- `CLAUDE.md` - Project instructions
- `AGENTS.md` - Universal agent instructions

Python projects additionally get:
- Virtual environment creation
- `env` settings for PATH and VIRTUAL_ENV
- SessionStart hook for venv activation

#### Tests
- ✅ 25 passing tests covering core functionality

### In Progress

#### Daemon Architecture
Design complete, implementation pending. The daemon provides:

1. **Multi-agent coordination** - Multiple Claude Code instances share state
2. **File locking** - Prevent concurrent modifications
3. **Event pub/sub** - Notify agents of changes
4. **Process management** - Track running scripts

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────────┐
│                         IdlerGear Daemon                            │
│                    (.idlergear/daemon.sock)                         │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │ Connection  │  │    File     │  │   Event     │  │  Process   │ │
│  │  Manager    │  │   Locks     │  │    Bus      │  │  Manager   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
         ↑                                       ↑
         │           Unix Socket IPC             │
         ↓                                       ↓
┌─────────────────┐                    ┌─────────────────┐
│   MCP Server    │                    │   MCP Server    │
│  (Claude #1)    │                    │  (Claude #2)    │
└─────────────────┘                    └─────────────────┘
```

**Protocol:** JSON-RPC 2.0 over Unix domain socket

**Implementation Tasks:**
1. Daemon core (socket server, connection handling)
2. Daemon protocol (JSON-RPC messages)
3. Daemon client library
4. Daemon auto-start and lifecycle
5. Event pub/sub system
6. File locking coordination
7. Migrate MCP server to use daemon client
8. Add daemon status/start/stop CLI commands

### Not Started

- GitHub sync (Issues, Discussions, Wiki, Projects)
- Contexts (AI session state management)
- Resources (file registry with labels)
- Codebase (git wrapper commands)

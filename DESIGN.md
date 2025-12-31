# IdlerGear Design

---

## Part 1: Vision

---

### Mission

**IdlerGear is structured project management for AI-assisted development.**

It provides a command-based API that both humans and AI assistants can use to track work, capture knowledge, and maintain project context across sessions.

### The Problem

AI coding assistants are stateless. Every session starts fresh. You constantly re-explain:
- What the project is trying to achieve
- What you learned last session about how something works
- What issues were discovered but deferred
- What the current implementation plan is
- What happened when you ran that script

### The Solution

A **command-based API** that manages project knowledge across sessions, machines, and teams.

Six knowledge types. Backend-agnostic. Works across all AI assistants.

### Key Insight

Project management benefits both humans and AI. A structured API serves both better than unstructured markdown files.

### IdlerGear vs AGENTS.md

AGENTS.md defines **file naming conventions** in natural language:
> "Look for the vision in docs/VISION.md"

IdlerGear provides a **structured command-based API**:
```bash
idlergear vision show    # Returns the vision, wherever it's stored
```

The difference:
- **Consistent interface** - Same command across all projects
- **Backend-agnostic** - Could be local file, GitHub, Jira, or central server
- **Configurable** - Project decides where data lives, command stays the same
- **Deterministic** - No AI interpretation needed, just run the command
- **Write capability** - AI can store knowledge, not just read it

**IdlerGear IS the structured version of AGENTS.md**, implemented as an API instead of prose.

**Compatibility:** AGENTS.md can reference IdlerGear: "Use `idlergear task list` for issues, `idlergear vision show` for project direction."

### The Adoption Challenge

IdlerGear works, but getting AI assistants to use it consistently requires:

| Direction | Challenge | Solution |
|-----------|-----------|----------|
| **Read** | AI prefers file search | MCP tools appear as native |
| **Write** | AI doesn't think to store discoveries | Hooks, slash commands, training |

**The goal:** A virtuous cycle where AI queries IdlerGear for context, stores discoveries via API, and knowledge accumulates across sessions instead of resetting.

See issue #94 for adoption strategies.

### What IdlerGear Is NOT

- **Not an IDE** - It manages project knowledge, not editing
- **Not a build system** - Use make, cargo, npm for that
- **Not an AI wrapper** - It provides context TO AI tools
- **Not a cloud service** - Runs locally, your data stays local
- **Not enterprise-only** - Works solo, scales to teams

### Cross-Assistant Strategy

IdlerGear is **AI-assistant agnostic**. It works identically across:
- Claude Code
- Gemini CLI
- GitHub Copilot CLI
- OpenAI Codex CLI
- Aider
- Block's Goose

**Why this matters:** Developers use multiple AI assistants. Project knowledge should persist regardless of which assistant is active.

**How it works:**
1. **MCP-first** - Universal tool protocol supported by all major assistants
2. **CLI fallback** - Same commands work via shell when MCP isn't available
3. **Project instructions** - Generate appropriate files for each assistant

---

## Part 2: Knowledge Model

---

### Six Types of Knowledge

IdlerGear manages six types of project knowledge:

#### 1. Tasks
Things that need to be done. Have a lifecycle (open → in progress → closed). Can be assigned, prioritized, labeled.

```bash
idlergear task create "Fix parser bug"
idlergear task list
idlergear task close 42
```

**GitHub sync:** Issues

#### 2. Notes
Quick capture - the post-it note. Unstructured, flexible. Use for:
- Quick observations you don't want to forget
- Explorations and open questions (`--tag explore`)
- Vague ideas to flesh out later (`--tag idea`)
- Discoveries that might become tasks or references later

```bash
idlergear note create "Parser quirk with compound words"
idlergear note create "Should we support Windows?" --tag explore
idlergear note create "What if we cached the AST?" --tag idea
idlergear note list
idlergear note list --tag idea
idlergear note promote 1 --to task
```

**GitHub sync:** Issues with "note" label

#### 3. Vision
The "why" - purpose, mission, long-term direction. Protected, rarely changes. Guides decisions across the project.

```bash
idlergear vision show
idlergear vision edit
```

**GitHub sync:** VISION.md in repo root

#### 4. Plans
How to achieve a specific goal. Groups related tasks, defines sequence. More tactical than vision, more structured than notes.

```bash
idlergear plan show
idlergear plan list
idlergear plan switch "auth-system"
```

**GitHub sync:** GitHub Projects

#### 5. References
Explanations of how things work - design decisions, technical docs, world knowledge. Persists long-term, updated as understanding evolves.

```bash
idlergear reference add "GGUF-Format"
idlergear reference search "quantization"
```

**GitHub sync:** Wiki pages

#### 6. Runs
Results from executed processes. Logs, test results, script output. Queryable history of what happened.

```bash
idlergear run start ./train.sh --name training
idlergear run status
idlergear run logs training --tail 50
```

**GitHub sync:** None (local only)

### Knowledge Flow

```
Quick thought → Note
                  ↓
    ┌─────────────┼─────────────┐
    ↓             ↓             ↓
  Task         Reference     (discard)
    ↓
  Plan (groups tasks)
```

Notes are the inbox. They get promoted to Tasks (actionable work), References (permanent documentation), or deleted when no longer relevant.

### Configuration

Not a knowledge type, but essential infrastructure:

```bash
idlergear config set backend.task github
idlergear config get backend.task
```

Stored in `.idlergear/config.toml`.

---

## Part 3: Architecture

---

### Overview

- **Python** - installed via pipx, uses official MCP SDK
- **MCP server** for AI tool integration
- **Local-first** - everything works offline, sync when ready
- **Single daemon per project** (optional) for multi-agent coordination
- Project state lives in `.idlergear/` directory
- Assumes **git and GitHub** for version control (other git hosts later)
- **AI-assistant agnostic** - works with Claude Code, Goose, Aider, Copilot, Gemini CLI, Codex

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

## Part 4: Implementation

---

### Core Scope

| Type | Local Storage | GitHub Sync |
|------|---------------|-------------|
| Tasks | Markdown + frontmatter | GitHub Issues |
| Notes | Markdown + frontmatter | GitHub Issues (with label) |
| Vision | Single markdown file | Repo file (VISION.md) |
| Plans | Markdown + frontmatter | GitHub Projects |
| References | Markdown + frontmatter | GitHub Wiki |
| Runs | Log files | *(no sync)* |

### Infrastructure

- **MCP Server** - AI tool integration (structured JSON responses)
- **CLI** - Human interface (same commands, text output)
- **Config** - `.idlergear/config.toml`
- **Daemon** (optional) - Multi-agent coordination via Unix socket

### CLI Commands

```bash
# Setup
idlergear init
idlergear install
idlergear config get|set

# Tasks (→ GitHub Issues)
idlergear task create|list|show|close|edit

# Notes (→ GitHub Issues with label)
idlergear note create|list|show|delete|promote

# Vision (→ repo VISION.md)
idlergear vision show|edit

# Plans (→ GitHub Projects)
idlergear plan create|list|show|switch

# References (→ GitHub Wiki)
idlergear reference add|list|show|edit|search

# Runs (no sync)
idlergear run start|list|status|logs|stop
```

### MCP Tools

Same functionality exposed as MCP tools:

```python
# Tasks
task_create(title, body=None, labels=[])
task_list(state="open")
task_show(id)
task_close(id)

# Notes
note_create(content, tags=[])
note_list()
note_promote(id, to="task")

# Vision
vision_show()
vision_edit(content)

# Plans
plan_list()
plan_show(name)
plan_switch(name)

# References
reference_add(title, body)
reference_list()
reference_search(query)

# Runs
run_start(command, name=None)
run_list()
run_status(name)
run_logs(name, tail=None)

# Config
config_get(key)
config_set(key, value)
```

### File Structure

```
.idlergear/
├── config.toml
├── vision.md
├── tasks/
│   ├── 001-fix-parser-bug.md
│   └── 002-add-tests.md
├── notes/
│   └── 001.md
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

---

## Part 5: Implementation Status

---

### Completed

| Component | Status |
|-----------|--------|
| CLI (all 6 knowledge types) | ✅ Done |
| MCP Server (30+ tools) | ✅ Done |
| Local backend | ✅ Done |
| GitHub backend | ✅ Done |
| Project templates | ✅ Done |
| Claude Code integration | ✅ Done |
| Daemon architecture | ✅ Done |
| Tests (46 passing) | ✅ Done |

### In Progress

- GitHub sync commands
- Multi-agent coordination via daemon

### Deferred

The following were considered but deferred to maintain focus:

| Feature | Reason for Deferral |
|---------|---------------------|
| Contexts (session state) | Solve adoption problem first |
| Resources (file registry) | Out of scope - use git |
| Codebase (git wrapper) | Out of scope - use git directly |
| Memory (preferences) | Can use References with tags |
| Sessions (save/restore) | Solve adoption problem first |
| Usage (token tracking) | Tangential to project management |
| Eddi bridge | Later - cross-machine coordination |
| Non-GitHub backends | Later - Jira, GitLab, etc. |

---

## Part 6: What Success Looks Like

---

### For Users

1. Start a new session, run `idlergear context` - immediately have full project context
2. Discover something, run `idlergear note create` - knowledge persists
3. Switch AI assistants - same commands, same knowledge
4. Come back next week - nothing lost, everything queryable

### For AI Assistants

1. Query `task_list()` - get structured, current task data
2. Store discoveries via `note_create()` - persist for future sessions
3. Check `vision_show()` - understand project direction
4. Reference `reference_search()` - find documented decisions

### Metrics

- AI uses IdlerGear queries instead of file searches
- Knowledge accumulates across sessions
- Less re-explaining in new sessions
- Consistent experience across Claude, Gemini, Copilot, etc.

# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**IdlerGear is a knowledge management API that synchronizes AI context management with human project management.**

It provides a **command-based API** (not file conventions like AGENTS.md):
- `idlergear vision show` - not "look for VISION.md in docs/"
- `idlergear task list` - not "check GitHub Issues or TODO.md"
- Same commands everywhere, configurable backends

See `DESIGN.md` for the full vision, knowledge model (6 types), and architecture.

## Development

```bash
source venv/bin/activate
./run.sh  # format, lint, test
```

See DEVELOPMENT.md for practices.

## CRITICAL: IdlerGear Usage Rules

### Session Start

**ALWAYS run this command at the start of EVERY conversation:**

```bash
idlergear context
```

This provides the project vision, current plan, and open tasks. Do NOT skip this step.

### FORBIDDEN: File-Based Knowledge

**DO NOT create any of these files:**
- `TODO.md`, `TODO.txt`, `TASKS.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `FEATURE_IDEAS.md`, `RESEARCH.md`, `BACKLOG.md`
- Any markdown file for tracking work or capturing thoughts

**ALWAYS use IdlerGear commands instead.**

### FORBIDDEN: Inline TODOs

**DO NOT write inline TODO comments:**
- `// TODO: ...`
- `# FIXME: ...`
- `/* HACK: ... */`

**INSTEAD:** Create a task with `idlergear task create "..." --label technical-debt`

### REQUIRED: Use IdlerGear Commands

| Instead of... | Use this command |
|---------------|------------------|
| Creating TODO.md | `idlergear task create "description"` |
| Writing notes to files | `idlergear note create "content"` |
| Adding TODO comments | `idlergear task create "..." --label technical-debt` |
| Creating VISION.md | `idlergear vision edit` |
| Documenting findings | `idlergear reference add "title" --body "..."` |

### During Development

| Action | Command |
|--------|---------|
| Found a bug | `idlergear task create "..." --label bug` |
| Had an idea | `idlergear note create "..."` |
| Research question | `idlergear note create "..." --tag explore` |
| Completed work | `idlergear task close <id>` |
| Check project goals | `idlergear vision show` |
| View open tasks | `idlergear task list` |

### Knowledge Flow

```
note → task or reference
```
- Quick thoughts go to notes (capture now, review later)
- Use `--tag explore` for research questions, `--tag idea` for ideas
- Actionable work goes to tasks (clear completion criteria)
- Use `idlergear note promote <id> --to task` to convert notes to tasks

### Data Protection

**NEVER modify `.idlergear/` files directly** - Use CLI commands only

## Multi-Agent Coordination (Daemon)

**IdlerGear daemon enables multiple AI assistants to work together on the same codebase.**

### Starting the Daemon

```bash
# Start daemon (required for multi-agent coordination)
idlergear daemon start

# Check daemon status
idlergear daemon status

# Stop daemon
idlergear daemon stop
```

### Coordination Features

**Message Passing:**
```bash
# Send message to all active AI agents
idlergear daemon send "API changed, review TaskService.ts"

# Queue command for any available agent to pick up
idlergear daemon queue "run full test suite" --priority 5

# List queued commands
idlergear daemon queue-list

# See active AI agents
idlergear daemon agents
```

**Agent Registration (Automatic via MCP):**
When using IdlerGear via Claude Code or other AI tools:
- Agent automatically registers with daemon
- Receives broadcasts from other agents
- Can pick up queued commands
- Status visible to all other agents

**Use Cases:**
1. **Long-running tasks**: Queue work while you continue on other things
2. **Multi-terminal coordination**: Claude Code + Goose + Aider all see same state
3. **Background execution**: Queue tests/builds to run asynchronously
4. **Team coordination**: Share context across multiple AI sessions

### Script Generation

Generate shell scripts that auto-register with daemon:

```bash
# Generate script that sets up dev environment
idlergear run generate-script backend "python manage.py runserver" \
    --venv ./venv \
    --requirement django \
    --env FLASK_ENV=development \
    --stream-logs

# Run the generated script (auto-registers with daemon)
./scripts/backend.sh

# Script automatically:
# - Activates venv
# - Installs dependencies
# - Registers with daemon as an agent
# - Streams logs visible to all agents
# - Unregisters on exit
```

**Pre-built templates:**
- `pytest` - Test runner
- `django-dev` - Django dev server
- `flask-dev` - Flask dev server
- `jupyter` - Jupyter Lab
- `fastapi-dev` - FastAPI with uvicorn

### Multi-Agent Workflow Example

```bash
# Terminal 1: Start daemon
idlergear daemon start

# Terminal 2: Claude Code (auto-registers)
# (Claude Code MCP automatically registers as agent)

# Terminal 3: Run backend script
./scripts/backend.sh  # Auto-registers as "backend-server"

# Terminal 4: Run frontend script
./scripts/frontend.sh  # Auto-registers as "frontend-dev"

# Now from any terminal:
idlergear daemon agents
# Shows: Claude Code, backend-server, frontend-dev

idlergear daemon send "Database schema updated"
# All three agents receive the message

idlergear daemon queue "rebuild migrations" --priority 10
# Any available agent can pick this up
```

### Token-Efficient Context

**Always use `--mode` flag for token efficiency:**

```bash
# Minimal mode (~750 tokens) - DEFAULT
idlergear context
idlergear context --mode minimal

# Standard mode (~2,500 tokens) - General dev work
idlergear context --mode standard

# Detailed mode (~7,000 tokens) - Deep planning
idlergear context --mode detailed

# Full mode (~17,000+ tokens) - Rare, comprehensive view
idlergear context --mode full
```

**Token savings on task lists:**

```bash
# Limit results
idlergear task list --limit 5

# Strip bodies (titles only)
idlergear task list --preview

# Combine for maximum efficiency (~200 tokens)
idlergear task list --preview --limit 10
```

## IdlerGear Usage Quick Reference

**ALWAYS run at session start:**
```bash
idlergear context --mode minimal
```

**FORBIDDEN files:** `TODO.md`, `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
**FORBIDDEN comments:** `// TODO:`, `# FIXME:`, `/* HACK: */`

**Use instead:**
- `idlergear task create "..."` - Create actionable tasks
- `idlergear note create "..."` - Capture quick thoughts
- `idlergear note create "..." --tag explore` - Research questions
- `idlergear vision show` - Check project goals

See AGENTS.md for full command reference.

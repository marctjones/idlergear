# AI Agent Instructions for IdlerGear Projects

This document provides instructions for AI coding assistants working on projects that use IdlerGear.

## About IdlerGear

This project uses **IdlerGear** for knowledge management - a structured system that replaces ad-hoc files like TODO.md and NOTES.md with a command-based API.

## CRITICAL: Session Start

**ALWAYS run this command at the start of EVERY session:**

```bash
idlergear context
```

This provides:
- Project vision and goals
- Current plan (if any)
- Open tasks and priorities
- Recent notes and explorations
- Reference documentation

**DO NOT skip this step** - it's the foundation of effective AI-assisted development.

## Core Commands

### Task Management
```bash
idlergear task create "description"  # Create a new task
idlergear task list                  # View all open tasks
idlergear task close <id>            # Close completed task
idlergear task show <id>             # View task details
```

### Notes & Insights
```bash
idlergear note create "content"      # Capture quick thought
idlergear note list                  # View all notes
idlergear note promote <id> --to task  # Convert note to task
```

### Project Context
```bash
idlergear vision show                # View project vision
idlergear plan show                  # View current plan
idlergear reference list             # List documentation
idlergear search "query"             # Search all knowledge
```

### File Registry (Token-Efficient)
```bash
idlergear file deprecate old.py --successor new.py  # Mark file as deprecated
idlergear file annotate file.py --description "..." # Annotate for search
idlergear file search --query "authentication"      # Search files (93% savings!)
idlergear file status file.py                       # Check file status
```

### Background Runs
```bash
idlergear run start "command" --name <name>  # Start background process
idlergear run list                           # List all runs
idlergear run status <name>                  # Check run status
idlergear run logs <name>                    # View output
idlergear run stop <name>                    # Stop process
```

## FORBIDDEN Patterns

### NEVER Create These Files
- `TODO.md`, `TASKS.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `BACKLOG.md`, `FEATURE_IDEAS.md`
- Any markdown file for tracking work or capturing thoughts

### NEVER Write These Comments
- `# TODO: ...`
- `# FIXME: ...`
- `// HACK: ...`
- `/* NOTE: ... */`

### ALWAYS Use IdlerGear Commands Instead

| Instead of... | Use this command |
|---------------|------------------|
| `# TODO: Add validation` | `idlergear task create "Add validation" --label tech-debt` |
| `# NOTE: API requires auth` | `idlergear note create "API requires auth header"` |
| `# FIXME: Memory leak` | `idlergear task create "Fix memory leak" --label bug` |
| Creating TODO.md | `idlergear task create "description"` |
| Writing to NOTES.md | `idlergear note create "content"` |

## Development Workflow

1. **Start session**: `idlergear context`
2. **Check open tasks**: `idlergear task list`
3. **Work on task**: Make changes, commit
4. **Capture insights**: `idlergear note create "..."`
5. **Create new tasks**: `idlergear task create "..."`
6. **Save session**: `idlergear session-save` (optional)

## Token Efficiency

IdlerGear provides massive token savings:
- **Context**: 97% savings (15K → 570 tokens via `idlergear context --mode minimal`)
- **File Search**: 93% savings (15K → 200 tokens via file annotations)
- **Task List**: 90% savings with `--preview` flag

### Context Modes
```bash
idlergear context                 # minimal mode (~570 tokens)
idlergear context --mode standard # ~2,500 tokens
idlergear context --mode detailed # ~7,000 tokens
idlergear context --mode full     # ~17,000 tokens
```

## MCP Server (146 Tools)

IdlerGear provides 146 MCP tools for direct integration. If your AI assistant supports MCP, these tools are available:

**Session Management:**
- `idlergear_session_start` - Load context + previous state
- `idlergear_session_save` - Save current work state
- `idlergear_session_end` - End with suggestions

**Knowledge:**
- `idlergear_task_create`, `idlergear_task_list`, `idlergear_task_close`
- `idlergear_note_create`, `idlergear_note_list`
- `idlergear_context` - Get project context
- `idlergear_search` - Search all knowledge

**File Registry:**
- `idlergear_file_deprecate`, `idlergear_file_status`
- `idlergear_file_annotate`, `idlergear_file_search`

...and 138 more tools. See `.mcp.json` or run `idlergear --help` for complete list.

## Multi-Agent Coordination

If multiple AI agents work on the project:

```bash
# Start daemon for coordination
idlergear daemon start

# All agents automatically receive:
# - Registry updates (deprecated files)
# - Task changes
# - Broadcast messages
```

This ensures all agents stay synchronized on project state.

## Knowledge Promotion Flow

```
note → task
note → reference (via promote)
```

- **Quick thoughts**: `idlergear note create "..."` (capture now, review later)
- **Actionable work**: `idlergear task create "..."` (clear completion criteria)
- **Documentation**: `idlergear reference add "title" --body "..."` (permanent knowledge)
- **Promote notes**: `idlergear note promote <id> --to task` (convert)

## Best Practices

1. ✅ **Run `idlergear context` at session start** - Always get current state
2. ✅ **Search file annotations before grep** - Save 93% tokens
3. ✅ **Create tasks immediately** - Don't defer with TODO comments
4. ✅ **Link deprecated files to successors** - Help future AI agents
5. ✅ **Annotate files proactively** - Describe purpose, tags, components

## Troubleshooting

**"Command not found: idlergear"**
- Install: `pipx install idlergear`
- Or: `pip install idlergear`

**"IdlerGear not initialized"**
- Run: `idlergear init`
- Then: `idlergear install`

**"How do I access MCP tools?"**
- MCP tools are automatically available if your AI assistant supports MCP
- Check `.mcp.json` in the project root
- For Claude Code: Tools auto-register via MCP
- For other assistants: See assistant-specific documentation

## Protected Files

**DO NOT modify directly:**
- `.idlergear/` - Data files (use CLI commands only)
- `.mcp.json` - MCP server configuration
- `.claude/hooks/` - Lifecycle hooks

## Documentation

- [Full Documentation](https://github.com/marctjones/idlergear)
- [File Registry Guide](docs/guides/file-registry.md)
- [MCP Tools Reference](docs/mcp-tools.md)
- [Roadmap](ROADMAP.md)

---

**Remember**: Use IdlerGear commands, not files. It's the command-based API for AI-assisted development.

## IdlerGear

This project uses [IdlerGear](https://github.com/marctjones/idlergear) for knowledge management.

### CRITICAL: Session Start

**ALWAYS run this command at the start of EVERY session:**

```bash
idlergear context
```

This shows the project vision, current plan, open tasks, and recent notes. Do NOT skip this step.

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
| Research question | `idlergear explore create "..."` |
| Completed work | `idlergear task close <id>` |
| Check project goals | `idlergear vision show` |
| View open tasks | `idlergear task list` |

### Knowledge Promotion Flow

```
note → explore → task
```
- Quick thoughts: `idlergear note create "..."` (capture now, review later)
- Research threads: `idlergear explore create "..."` (open questions)
- Actionable work: `idlergear task create "..."` (clear completion criteria)
- Promote notes: `idlergear note promote <id>` (convert to task/explore)

### Reference Documentation

- `idlergear reference list` - View reference documents
- `idlergear reference show "title"` - Read a specific reference
- `idlergear reference add "title" --body "..."` - Add documentation
- `idlergear search "query"` - Search across all knowledge types

### Protected Files

**DO NOT modify directly:**
- `.idlergear/` - Data files (use CLI commands)
- `.mcp.json` - MCP configuration

The IdlerGear MCP server is configured in `.mcp.json` and provides these tools directly.

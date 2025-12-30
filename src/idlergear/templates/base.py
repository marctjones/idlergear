"""Base project template - common files for all project types."""

# .gitignore content
GITIGNORE = """\
# IdlerGear (local files only)
.idlergear/daemon.sock
.idlergear/daemon.pid
.idlergear/runs/

# Claude Code local settings
.claude/settings.local.json
CLAUDE.local.md

# OS files
.DS_Store
Thumbs.db

# Editor files
*.swp
*.swo
*~
.idea/
.vscode/
"""

# Additional gitignore for hooks (they're part of the project, not ignored)
# But we do want to protect them from modification

# CLAUDE.md content - project instructions for Claude
CLAUDE_MD = """\
# {project_name}

{vision}

## IdlerGear Integration

This project uses IdlerGear for knowledge management. IdlerGear provides:
- **Tasks** - Track work items (syncs to GitHub Issues)
- **Notes** - Quick capture for later
- **Explorations** - Open questions being investigated
- **Reference** - Technical documentation
- **Plans** - Implementation roadmaps
- **Vision** - Project goals and direction

### Before Starting Work

Always check context first:
```bash
idlergear vision show    # Understand project goals
idlergear plan show      # See current plan
idlergear task list      # Review open tasks
idlergear explore list   # Check open questions
```

### During Development

Capture knowledge as you work:
```bash
idlergear note create "discovered X while working on Y"
idlergear task create "need to fix Z" --label bug
idlergear reference add "API Design" --body "..."
```

### MCP Tools Available

The IdlerGear MCP server provides direct tool access. Use tools like:
- `idlergear_task_list` - List tasks
- `idlergear_note_create` - Create notes
- `idlergear_vision_show` - Get project vision

## Protected Files

Do NOT modify files in `.idlergear/` directly. Use idlergear commands instead.
The `.claude/` directory contains Claude Code settings - avoid modifying these too.
"""

# .claude/settings.json - project settings with protections
CLAUDE_SETTINGS = {
    "permissions": {
        "deny": [
            # Protect idlergear data files from direct modification
            "Write(.idlergear/**)",
            "Edit(.idlergear/**)",
            # Protect claude settings from modification
            "Write(.claude/settings.json)",
            "Edit(.claude/settings.json)",
            "Write(.claude/rules/**)",
            "Edit(.claude/rules/**)",
            "Write(.claude/hooks/**)",
            "Edit(.claude/hooks/**)",
            # Protect MCP config
            "Write(.mcp.json)",
            "Edit(.mcp.json)",
        ],
        "allow": [
            # Allow reading idlergear files
            "Read(.idlergear/**)",
            # Allow reading claude config
            "Read(.claude/**)",
            # Allow idlergear CLI commands
            "Bash(idlergear:*)",
        ],
    },
}

# .claude/rules/idlergear.md - rules for idlergear usage
CLAUDE_RULES_IDLERGEAR = """\
---
description: REQUIRED rules for IdlerGear knowledge management
alwaysApply: true
---

# IdlerGear Usage Rules

## CRITICAL: Session Start

**ALWAYS run this command at the start of EVERY conversation:**

```bash
idlergear context
```

This provides the project vision, current plan, and open tasks. Do NOT skip this step.

## FORBIDDEN: File-Based Knowledge

**DO NOT create any of these files:**
- `TODO.md`, `TODO.txt`, `TASKS.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `FEATURE_IDEAS.md`, `RESEARCH.md`, `BACKLOG.md`
- Any markdown file for tracking work or capturing thoughts

**ALWAYS use IdlerGear commands instead.**

## FORBIDDEN: Inline TODOs

**DO NOT write inline TODO comments:**
- `// TODO: ...`
- `# FIXME: ...`
- `/* HACK: ... */`

**INSTEAD:** Create a task with `idlergear task create "..." --label technical-debt`

## REQUIRED: Use IdlerGear Commands

| Instead of... | Use this command |
|---------------|------------------|
| Creating TODO.md | `idlergear task create "description"` |
| Writing notes to files | `idlergear note create "content"` |
| Adding TODO comments | `idlergear task create "..." --label technical-debt` |
| Creating VISION.md | `idlergear vision edit` |
| Documenting findings | `idlergear reference add "title" --body "..."` |

## Data Protection

1. **NEVER modify `.idlergear/` files directly** - Use CLI commands only
2. **NEVER modify `.claude/` or `.mcp.json`** - These are protected

## Workflow

1. **Session start**: Run `idlergear context`
2. **Found a bug**: `idlergear task create "..." --label bug`
3. **Had an idea**: `idlergear note create "..."`
4. **Research question**: `idlergear explore create "..."`
5. **Completed work**: `idlergear task close <id>`
6. **Document finding**: `idlergear reference add "..."`

## Knowledge Promotion Flow

```
note → explore → task
```
- Quick thoughts go to notes (capture now, review later)
- Research questions go to explorations (open-ended investigation)
- Actionable work goes to tasks (clear completion criteria)
- Use `idlergear note promote <id>` to convert notes to tasks/explorations

## MCP Tools

The IdlerGear MCP server provides direct tool access. Use these when available.
"""

# .mcp.json content
MCP_CONFIG = {
    "mcpServers": {
        "idlergear": {
            "command": "idlergear-mcp",
            "args": [],
            "type": "stdio",
        }
    }
}

# AGENTS.md content (for compatibility with other AI tools)
AGENTS_MD = """\
# Agent Instructions

## Project Overview

{vision}

## IdlerGear Knowledge Management

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
- `.claude/` - Claude Code settings
- `.mcp.json` - MCP configuration
"""

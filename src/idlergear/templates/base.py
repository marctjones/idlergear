"""Base project template - common files for all project types."""

# .claude/commands/ig_context.md - slash command for getting context
CLAUDE_COMMAND_CONTEXT = """\
Run `idlergear context` to get the current project context, then summarize:
1. The project vision (1-2 sentences)
2. What tasks are open and their priorities
3. Any recent notes that might be relevant

After reviewing, ask what I'd like to work on.
"""

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
- **Notes** - Quick capture (use `--tag explore` for research, `--tag idea` for ideas)
- **Reference** - Technical documentation
- **Plans** - Implementation roadmaps
- **Vision** - Project goals and direction
- **Runs** - Process output tracking

### Before Starting Work

Always check context first:
```bash
idlergear vision show    # Understand project goals
idlergear plan show      # See current plan
idlergear task list      # Review open tasks
idlergear note list      # Check recent notes
```

### During Development

Capture knowledge as you work:
```bash
idlergear note create "discovered X while working on Y"
idlergear note create "should we try Z?" --tag explore
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

**ALWAYS run this at the start of EVERY conversation:**

```bash
idlergear context
```

This provides vision, current plan, and open tasks. Do NOT skip this step.

## CRITICAL: Persist Your Discoveries

**When you learn something, STORE IT:**

```bash
# Discovered API behavior
idlergear note create "Auth endpoint requires Bearer token prefix"

# Found a quirk or gotcha
idlergear note create "Parser fails on empty input - needs null check" --tag bug

# Had an architectural idea
idlergear note create "Could cache AST to improve performance" --tag idea
```

**This note WILL be available in your next session.** Without this, your learnings are lost.

## FORBIDDEN: File-Based Knowledge

**DO NOT create any of these files:**
- `TODO.md`, `TODO.txt`, `TASKS.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `FEATURE_IDEAS.md`, `RESEARCH.md`, `BACKLOG.md`

**ALWAYS use IdlerGear commands instead.**

## FORBIDDEN: Inline TODOs

**DO NOT write inline TODO comments:**
- `// TODO: ...`
- `# FIXME: ...`
- `/* HACK: ... */`

**INSTEAD:** `idlergear task create "..." --label technical-debt`

## PREFER: IdlerGear Search Over File Search

**Before searching files for project context, try:**

```bash
idlergear search "authentication"
```

This searches tasks, notes, references, and plans - structured knowledge that persists.

## REQUIRED: Use IdlerGear Commands

| Instead of... | Use this command |
|---------------|------------------|
| Creating TODO.md | `idlergear task create "description"` |
| Writing notes to files | `idlergear note create "content"` |
| Adding TODO comments | `idlergear task create "..." --label technical-debt` |
| Creating VISION.md | `idlergear vision edit` |
| Documenting findings | `idlergear reference add "title" --body "..."` |

## Workflow

1. **Session start**: Run `idlergear context`
2. **Discovered something**: `idlergear note create "..."`
3. **Found a bug**: `idlergear task create "..." --label bug`
4. **Had an idea**: `idlergear note create "..." --tag idea`
5. **Research question**: `idlergear note create "..." --tag explore`
6. **Completed work**: `idlergear task close <id>`
7. **Session end**: Consider what should be noted for next time

## Knowledge Promotion Flow

```
note → task or reference
```
- Quick thoughts go to notes (capture now, review later)
- Use `--tag explore` for research questions, `--tag idea` for ideas
- Actionable work goes to tasks (clear completion criteria)
- Use `idlergear note promote <id> --to task` to convert notes to tasks

## MCP Tools

The IdlerGear MCP server provides direct tool access. PREFER these over file operations when available.
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

**ALWAYS run this at the start of EVERY session:**

```bash
idlergear context
```

This shows vision, current plan, open tasks, and recent notes. Do NOT skip this step.

### CRITICAL: Persist Your Discoveries

**When you learn something, STORE IT for future sessions:**

```bash
# Discovered API behavior
idlergear note create "Auth endpoint requires Bearer token prefix"

# Found a quirk or gotcha
idlergear note create "Parser fails on empty input - needs null check" --tag bug

# Had an architectural idea
idlergear note create "Could cache AST to improve performance" --tag idea
```

**This note WILL be available in your next session.** Without this, your learnings are lost.

### PREFER: IdlerGear Search Over File Search

**Before searching files for project context, try:**

```bash
idlergear search "authentication"
```

This searches tasks, notes, references, and plans - structured knowledge that persists.

### FORBIDDEN: File-Based Knowledge

**DO NOT create any of these files:**
- `TODO.md`, `TODO.txt`, `TASKS.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `FEATURE_IDEAS.md`, `RESEARCH.md`, `BACKLOG.md`

**ALWAYS use IdlerGear commands instead.**

### FORBIDDEN: Inline TODOs

**DO NOT write inline TODO comments:**
- `// TODO: ...`
- `# FIXME: ...`
- `/* HACK: ... */`

**INSTEAD:** `idlergear task create "..." --label technical-debt`

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
| Discovered something | `idlergear note create "..."` |
| Found a bug | `idlergear task create "..." --label bug` |
| Had an idea | `idlergear note create "..." --tag idea` |
| Research question | `idlergear note create "..." --tag explore` |
| Completed work | `idlergear task close <id>` |
| Session end | Consider what to note for next time |

### Knowledge Promotion Flow

```
note → task or reference
```
- Quick thoughts: `idlergear note create "..."` (capture now, review later)
- Research threads: `idlergear note create "..." --tag explore` (open questions)
- Ideas: `idlergear note create "..." --tag idea` (future possibilities)
- Actionable work: `idlergear task create "..."` (clear completion criteria)
- Promote notes: `idlergear note promote <id> --to task` (convert to task or reference)

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

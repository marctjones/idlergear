"""Install IdlerGear into a project for Claude Code integration."""

import json
import sys
from pathlib import Path

import typer

from idlergear.config import find_idlergear_root


def get_idlergear_mcp_config() -> dict:
    """Get the MCP server configuration for idlergear."""
    # Find the idlergear-mcp executable
    # When installed via pip/pipx, it's in the PATH
    return {
        "command": "idlergear-mcp",
        "args": [],
        "type": "stdio",
    }


def install_mcp_server(project_path: Path | None = None) -> bool:
    """Add idlergear to .mcp.json for Claude Code integration.

    Returns True if installed, False if already present.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    mcp_path = project_path / ".mcp.json"

    # Load existing config or create new
    if mcp_path.exists():
        with open(mcp_path) as f:
            config = json.load(f)
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Check if already installed
    if "idlergear" in config["mcpServers"]:
        return False

    # Add idlergear server
    config["mcpServers"]["idlergear"] = get_idlergear_mcp_config()

    # Write config
    with open(mcp_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    return True


def uninstall_mcp_server(project_path: Path | None = None) -> bool:
    """Remove idlergear from .mcp.json.

    Returns True if removed, False if not present.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return False

    mcp_path = project_path / ".mcp.json"

    if not mcp_path.exists():
        return False

    with open(mcp_path) as f:
        config = json.load(f)

    if "mcpServers" not in config or "idlergear" not in config["mcpServers"]:
        return False

    del config["mcpServers"]["idlergear"]

    # Remove mcpServers if empty
    if not config["mcpServers"]:
        del config["mcpServers"]

    # Write config or remove file if empty
    if config:
        with open(mcp_path, "w") as f:
            json.dump(config, f, indent=2)
            f.write("\n")
    else:
        mcp_path.unlink()

    return True


AGENTS_MD_SECTION = """\
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
"""


def add_agents_md_section(project_path: Path | None = None) -> bool:
    """Add IdlerGear section to AGENTS.md.

    Returns True if added, False if already present.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    agents_path = project_path / "AGENTS.md"

    if agents_path.exists():
        content = agents_path.read_text()
        if "## IdlerGear" in content:
            return False
        # Append section
        content = content.rstrip() + "\n\n" + AGENTS_MD_SECTION
    else:
        content = "# Agent Instructions\n\n" + AGENTS_MD_SECTION

    agents_path.write_text(content)
    return True


def remove_agents_md_section(project_path: Path | None = None) -> bool:
    """Remove IdlerGear section from AGENTS.md.

    Returns True if removed, False if not present.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return False

    agents_path = project_path / "AGENTS.md"

    if not agents_path.exists():
        return False

    content = agents_path.read_text()

    if "## IdlerGear" not in content:
        return False

    # Remove the IdlerGear section
    import re

    # Match from "## IdlerGear" to the next "## " heading or end of file
    pattern = r"\n*## IdlerGear\n.*?(?=\n## |\Z)"
    new_content = re.sub(pattern, "", content, flags=re.DOTALL)

    if new_content.strip():
        agents_path.write_text(new_content)
    else:
        agents_path.unlink()

    return True


# CLAUDE.md section content - shorter than AGENTS.md, focuses on Claude Code specifics
CLAUDE_MD_SECTION = """\
## IdlerGear Usage

**ALWAYS run at session start:**
```bash
idlergear context
```

**FORBIDDEN files:** `TODO.md`, `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
**FORBIDDEN comments:** `// TODO:`, `# FIXME:`, `/* HACK: */`

**Use instead:**
- `idlergear task create "..."` - Create actionable tasks
- `idlergear note create "..."` - Capture quick thoughts
- `idlergear explore create "..."` - Research questions
- `idlergear vision show` - Check project goals

See AGENTS.md for full command reference.
"""


def add_claude_md_section(project_path: Path | None = None) -> bool:
    """Add IdlerGear section to CLAUDE.md.

    Returns True if added, False if already present.
    """
    import re

    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    claude_path = project_path / "CLAUDE.md"

    if claude_path.exists():
        content = claude_path.read_text()
        if "## IdlerGear Usage" in content:
            return False
        # Append section
        content = content.rstrip() + "\n\n" + CLAUDE_MD_SECTION
    else:
        content = "# CLAUDE.md\n\n" + CLAUDE_MD_SECTION

    claude_path.write_text(content)
    return True


def remove_claude_md_section(project_path: Path | None = None) -> bool:
    """Remove IdlerGear section from CLAUDE.md.

    Returns True if removed, False if not present.
    """
    import re

    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return False

    claude_path = project_path / "CLAUDE.md"

    if not claude_path.exists():
        return False

    content = claude_path.read_text()

    if "## IdlerGear Usage" not in content:
        return False

    # Remove the IdlerGear Usage section
    pattern = r"\n*## IdlerGear Usage\n.*?(?=\n## |\Z)"
    new_content = re.sub(pattern, "", content, flags=re.DOTALL)

    if new_content.strip():
        claude_path.write_text(new_content)
    else:
        claude_path.unlink()

    return True


# Claude Code rules file content - stronger enforcement language
RULES_FILE_CONTENT = """\
---
description: MANDATORY IdlerGear knowledge management rules - MUST follow
alwaysApply: true
---

# IdlerGear Usage Rules (MANDATORY)

## CRITICAL: Session Start (REQUIRED)

**Before responding to ANY user request, you MUST run:**

```bash
idlergear context
```

This is NOT optional. Do NOT skip this step. Do NOT proceed without running this command first.
If you have not run `idlergear context` in this session, STOP and run it now.

## MANDATORY: Bug Discovery

When you identify ANY bug, error, or issue, you MUST IMMEDIATELY run:

```bash
idlergear task create "Bug: <description>" --label bug
```

Do NOT continue working until the task is created. Do NOT just mention the bug in conversation.

## MANDATORY: Design Decisions

When making ANY architectural choice or design decision, you MUST IMMEDIATELY run:

```bash
idlergear task create "Decision: <what you decided>" --label decision
```

Record the decision BEFORE implementing it.

## MANDATORY: Technical Debt

When you write code that could be improved later, you MUST run:

```bash
idlergear task create "<what needs improvement>" --label tech-debt
```

Do NOT write `// TODO:` comments. Do NOT skip this step.

## FORBIDDEN: File-Based Knowledge (WILL BE BLOCKED)

You are PROHIBITED from creating these files:
- `TODO.md`, `TODO.txt`, `TASKS.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `FEATURE_IDEAS.md`, `RESEARCH.md`, `BACKLOG.md`
- Any markdown file for tracking work or capturing thoughts

These files will be REJECTED by hooks. Use IdlerGear commands instead.

## FORBIDDEN: Inline TODOs (WILL BE BLOCKED)

You are PROHIBITED from writing these comments:
- `// TODO: ...`
- `# TODO: ...`
- `# FIXME: ...`
- `/* HACK: ... */`
- `<!-- TODO: ... -->`

These comments will be REJECTED by hooks. Create tasks instead:
`idlergear task create "..." --label tech-debt`

## REQUIRED: Use IdlerGear Commands

| When you... | You MUST run... |
|-------------|-----------------|
| Find a bug | `idlergear task create "Bug: ..." --label bug` |
| Have an idea | `idlergear note create "..."` |
| Make a decision | `idlergear task create "Decision: ..." --label decision` |
| Leave tech debt | `idlergear task create "..." --label tech-debt` |
| Complete work | `idlergear task close <id>` |
| Research something | `idlergear explore create "..."` |
| Document findings | `idlergear reference add "..." --body "..."` |

## Data Protection

**NEVER modify `.idlergear/` files directly** - Use CLI commands only
**NEVER modify `.claude/` or `.mcp.json`** - These are protected

## Enforcement

Hooks are configured to:
1. Block commits with TODO comments
2. Block creation of forbidden files
3. Remind you to run `idlergear context` at session start
"""


# Hooks configuration for enforcement
HOOKS_CONFIG = {
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "Write|Edit",
                "command": "idlergear check --file \"$TOOL_INPUT_PATH\" --quiet",
            }
        ],
        "UserPromptSubmit": [
            {
                "command": "idlergear check --context-reminder",
            }
        ],
    }
}

# Slash command for session start
START_COMMAND_CONTENT = """\
---
description: Start IdlerGear session - run context and show project state
---

Run `idlergear context` to show the project vision, current plan, open tasks, and recent notes.

After running the command, summarize:
1. The project vision (what is this project for?)
2. Current plan if any
3. Number of open tasks and their priorities
4. Any open explorations

This gives you the full context to start working effectively.
"""


def add_rules_file(project_path: Path | None = None) -> bool:
    """Create .claude/rules/idlergear.md for Claude Code.

    Returns True if created, False if already exists.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    rules_dir = project_path / ".claude" / "rules"
    rules_file = rules_dir / "idlergear.md"

    if rules_file.exists():
        return False

    rules_dir.mkdir(parents=True, exist_ok=True)
    rules_file.write_text(RULES_FILE_CONTENT)
    return True


def add_hooks_config(project_path: Path | None = None) -> bool:
    """Create .claude/hooks.json for enforcement.

    Returns True if created, False if already exists.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    hooks_dir = project_path / ".claude"
    hooks_file = hooks_dir / "hooks.json"

    if hooks_file.exists():
        # Check if idlergear hooks already present
        with open(hooks_file) as f:
            existing = json.load(f)
        if "hooks" in existing:
            for hook_type in HOOKS_CONFIG["hooks"]:
                if hook_type in existing["hooks"]:
                    for hook in existing["hooks"][hook_type]:
                        if "idlergear" in hook.get("command", ""):
                            return False
        # Merge hooks
        if "hooks" not in existing:
            existing["hooks"] = {}
        for hook_type, hooks in HOOKS_CONFIG["hooks"].items():
            if hook_type not in existing["hooks"]:
                existing["hooks"][hook_type] = []
            existing["hooks"][hook_type].extend(hooks)
        with open(hooks_file, "w") as f:
            json.dump(existing, f, indent=2)
            f.write("\n")
        return True

    hooks_dir.mkdir(parents=True, exist_ok=True)
    with open(hooks_file, "w") as f:
        json.dump(HOOKS_CONFIG, f, indent=2)
        f.write("\n")
    return True


def add_start_command(project_path: Path | None = None) -> bool:
    """Create .claude/commands/start.md slash command.

    Returns True if created, False if already exists.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    commands_dir = project_path / ".claude" / "commands"
    command_file = commands_dir / "start.md"

    if command_file.exists():
        return False

    commands_dir.mkdir(parents=True, exist_ok=True)
    command_file.write_text(START_COMMAND_CONTENT)
    return True


def remove_rules_file(project_path: Path | None = None) -> bool:
    """Remove .claude/rules/idlergear.md.

    Returns True if removed, False if not present.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return False

    rules_file = project_path / ".claude" / "rules" / "idlergear.md"

    if not rules_file.exists():
        return False

    rules_file.unlink()

    # Clean up empty directories
    rules_dir = rules_file.parent
    claude_dir = rules_dir.parent
    try:
        if rules_dir.exists() and not any(rules_dir.iterdir()):
            rules_dir.rmdir()
        if claude_dir.exists() and not any(claude_dir.iterdir()):
            claude_dir.rmdir()
    except OSError:
        pass  # Directory not empty, that's fine

    return True

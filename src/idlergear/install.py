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


# Claude Code rules file content
RULES_FILE_CONTENT = """\
---
description: IdlerGear knowledge management rules
alwaysApply: true
---

# IdlerGear Usage Rules

## Session Start

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

## Knowledge Flow

```
note → explore → task
```
- Quick thoughts go to notes (capture now, review later)
- Research questions go to explorations (open-ended investigation)
- Actionable work goes to tasks (clear completion criteria)
- Use `idlergear note promote <id>` to convert notes to tasks/explorations

## Data Protection

**NEVER modify `.idlergear/` files directly** - Use CLI commands only
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

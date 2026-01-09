"""Install IdlerGear into a project for Claude Code integration."""

import json
import os
import stat
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


# Rules and commands are stored as files in src/idlergear/rules/ and src/idlergear/commands/
# They are read at install time using importlib.resources


# Hooks configuration for enforcement
# All IdlerGear hooks use ig_ prefix for identification
HOOKS_CONFIG = {
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "Write|Edit",
                "command": "idlergear check --file \"$TOOL_INPUT_PATH\" --quiet",
            },
            {
                "matcher": "Bash|Write|Edit",
                "command": "./.claude/hooks/ig_post-tool-use.sh",
            },
        ],
        "UserPromptSubmit": [
            {
                "command": "idlergear check --context-reminder",
            },
            {
                "command": "./.claude/hooks/ig_user-prompt-submit.sh",
            },
        ],
        "Notification": [
            {
                "command": "./.claude/hooks/ig_notification.sh",
            },
        ],
    }
}

# Slash commands are stored in src/idlergear/commands/ and read at install time


def add_rules_file(project_path: Path | None = None) -> str:
    """Create or update .claude/rules/idlergear.md for Claude Code.

    Copies the rules file from src/idlergear/rules/.
    Returns 'created', 'updated', or 'unchanged'.
    """
    from importlib.resources import files

    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    rules_dir = project_path / ".claude" / "rules"
    rules_file = rules_dir / "idlergear.md"

    # Read from package source
    package_rules = files("idlergear") / "rules" / "idlergear.md"
    if not package_rules.is_file():
        raise RuntimeError("idlergear rules file not found in package")

    src_content = package_rules.read_text()
    rules_dir.mkdir(parents=True, exist_ok=True)

    if rules_file.exists():
        if rules_file.read_text() == src_content:
            return "unchanged"
        else:
            rules_file.write_text(src_content)
            return "updated"
    else:
        rules_file.write_text(src_content)
        return "created"


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


# List of hook scripts to install from the package
# All hooks use ig_ prefix for identification and to avoid name conflicts
HOOK_SCRIPTS = [
    "ig_pre-tool-use.sh",
    "ig_post-tool-use.sh",
    "ig_session-start.sh",
    "ig_stop.sh",
    "ig_user-prompt-submit.sh",
    "ig_notification.sh",
]


def install_hook_scripts(project_path: Path | None = None) -> dict[str, str]:
    """Install Claude Code hook scripts from the idlergear package.

    Copies hook scripts from src/idlergear/hooks/ to .claude/hooks/.
    Returns dict of {script_name: action} where action is 'created', 'updated', or 'unchanged'.
    """
    from importlib.resources import files

    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    hooks_dir = project_path / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    package_hooks_dir = files("idlergear") / "hooks"
    results = {}

    for script_name in HOOK_SCRIPTS:
        src_file = package_hooks_dir / script_name
        dst_file = hooks_dir / script_name

        if not src_file.is_file():
            continue

        src_content = src_file.read_text()

        if dst_file.exists():
            if dst_file.read_text() == src_content:
                results[script_name] = "unchanged"
            else:
                dst_file.write_text(src_content)
                dst_file.chmod(0o755)
                results[script_name] = "updated"
        else:
            dst_file.write_text(src_content)
            dst_file.chmod(0o755)
            results[script_name] = "created"

    return results


def remove_hook_scripts(project_path: Path | None = None) -> bool:
    """Remove Claude Code hook scripts installed by idlergear.

    Returns True if any scripts were removed, False if none existed.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return False

    hooks_dir = project_path / ".claude" / "hooks"
    removed_any = False

    for script_name in HOOK_SCRIPTS:
        script_file = hooks_dir / script_name
        if script_file.exists():
            script_file.unlink()
            removed_any = True

    # Clean up empty hooks directory
    try:
        if hooks_dir.exists() and not any(hooks_dir.iterdir()):
            hooks_dir.rmdir()
    except OSError:
        pass

    return removed_any


def add_commands(project_path: Path | None = None) -> dict[str, str]:
    """Install all IdlerGear slash commands.

    Copies command files from src/idlergear/commands/.
    Returns dict of {command_name: action} where action is 'created', 'updated', or 'unchanged'.
    """
    from importlib.resources import files

    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    commands_dir = project_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    package_commands = files("idlergear") / "commands"
    results = {}

    # Install all .md files from the commands directory
    for item in package_commands.iterdir():
        if item.is_file() and item.name.endswith(".md"):
            dest_file = commands_dir / item.name
            src_content = item.read_text()

            if dest_file.exists():
                if dest_file.read_text() == src_content:
                    results[item.name] = "unchanged"
                else:
                    dest_file.write_text(src_content)
                    results[item.name] = "updated"
            else:
                dest_file.write_text(src_content)
                results[item.name] = "created"

    return results


def add_start_command(project_path: Path | None = None) -> bool:
    """Create .claude/commands/ig_start.md slash command (legacy wrapper)."""
    results = add_commands(project_path)
    return results.get("ig_start.md", False)


def add_skill(project_path: Path | None = None) -> dict[str, str]:
    """Create or update .claude/skills/idlergear/ skill directory.

    Copies the skill files from the idlergear package.
    Returns dict of {file_path: action} where action is 'created', 'updated', or 'unchanged'.
    """
    from importlib.resources import files

    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    skill_dir = project_path / ".claude" / "skills" / "idlergear"
    package_skill_dir = files("idlergear") / "skills" / "idlergear"
    results = {}

    def copy_file(src, dst, executable=False):
        """Copy file and return action taken."""
        if not src.is_file():
            return None
        src_content = src.read_text()
        if dst.exists():
            if dst.read_text() == src_content:
                return "unchanged"
            else:
                dst.write_text(src_content)
                if executable:
                    dst.chmod(0o755)
                return "updated"
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src_content)
            if executable:
                dst.chmod(0o755)
            return "created"

    # Copy SKILL.md
    action = copy_file(package_skill_dir / "SKILL.md", skill_dir / "SKILL.md")
    if action:
        results["SKILL.md"] = action

    # Copy references/
    refs_src = package_skill_dir / "references"
    refs_dst = skill_dir / "references"
    for ref_file in ["knowledge-types.md", "mcp-tools.md", "multi-agent.md"]:
        action = copy_file(refs_src / ref_file, refs_dst / ref_file)
        if action:
            results[f"references/{ref_file}"] = action

    # Copy scripts/
    scripts_src = package_skill_dir / "scripts"
    scripts_dst = skill_dir / "scripts"
    for script_file in ["context.sh", "status.sh", "session-start.sh"]:
        action = copy_file(scripts_src / script_file, scripts_dst / script_file, executable=True)
        if action:
            results[f"scripts/{script_file}"] = action

    return results


def remove_skill(project_path: Path | None = None) -> bool:
    """Remove .claude/skills/idlergear/ skill directory.

    Returns True if removed, False if not present.
    """
    import shutil

    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return False

    skill_dir = project_path / ".claude" / "skills" / "idlergear"

    if not skill_dir.exists():
        return False

    shutil.rmtree(skill_dir)

    # Clean up empty parent directories
    skills_dir = skill_dir.parent
    claude_dir = skills_dir.parent
    try:
        if skills_dir.exists() and not any(skills_dir.iterdir()):
            skills_dir.rmdir()
    except OSError:
        pass

    return True


def add_auto_version_hook(project_path: Path | None = None) -> bool:
    """Install git pre-commit hook for automatic version bumping.

    The hook increments the patch version in pyproject.toml on each commit.
    Manual major/minor version bumps are detected and respected.
    Use [skip-version] in commit message to bypass.

    Returns True if installed, False if already exists or not a git repo.
    """
    from importlib.resources import files

    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    # Check if this is a git repository
    git_dir = project_path / ".git"
    if not git_dir.exists():
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    pre_commit = hooks_dir / "pre-commit"

    # Check if pre-commit hook already exists
    if pre_commit.exists():
        content = pre_commit.read_text()
        if "IdlerGear auto-version" in content:
            return False  # Already installed
        # Append to existing hook
        hook_source = files("idlergear") / "hooks" / "auto_version.sh"
        hook_content = hook_source.read_text()
        # Add as a separate section
        with open(pre_commit, "a") as f:
            f.write("\n\n# --- IdlerGear auto-version hook ---\n")
            # Skip the shebang if appending
            lines = hook_content.split("\n")
            if lines[0].startswith("#!"):
                lines = lines[1:]
            f.write("\n".join(lines))
        return True

    # Create new pre-commit hook
    hook_source = files("idlergear") / "hooks" / "auto_version.sh"
    pre_commit.write_text(hook_source.read_text())
    pre_commit.chmod(0o755)

    return True


def remove_auto_version_hook(project_path: Path | None = None) -> bool:
    """Remove the auto-version pre-commit hook.

    Returns True if removed, False if not present.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return False

    pre_commit = project_path / ".git" / "hooks" / "pre-commit"

    if not pre_commit.exists():
        return False

    content = pre_commit.read_text()

    if "IdlerGear auto-version" not in content:
        return False

    # Check if the entire file is our hook or if we appended to existing
    if content.strip().startswith("#!/bin/bash\n# IdlerGear auto-version"):
        # Entire file is our hook, remove it
        pre_commit.unlink()
    else:
        # We appended to an existing hook, remove our section
        marker = "\n\n# --- IdlerGear auto-version hook ---\n"
        if marker in content:
            new_content = content.split(marker)[0]
            pre_commit.write_text(new_content)
        else:
            # Can't cleanly remove, leave it
            return False

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

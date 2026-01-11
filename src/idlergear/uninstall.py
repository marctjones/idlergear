"""Uninstall IdlerGear from a project.

Removes IdlerGear configuration and optionally data from a project.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path


def remove_mcp_config(project_path: Path) -> bool:
    """Remove IdlerGear from .mcp.json.

    Args:
        project_path: Path to the project

    Returns:
        True if removed, False if not present
    """
    mcp_file = project_path / ".mcp.json"

    if not mcp_file.exists():
        return False

    try:
        with open(mcp_file) as f:
            config = json.load(f)
    except (json.JSONDecodeError, IOError):
        return False

    if "mcpServers" not in config:
        return False

    if "idlergear" not in config["mcpServers"]:
        return False

    del config["mcpServers"]["idlergear"]

    # If no servers left, remove the file
    if not config["mcpServers"]:
        mcp_file.unlink()
    else:
        with open(mcp_file, "w") as f:
            json.dump(config, f, indent=2)

    return True


def remove_agents_md_section(project_path: Path) -> bool:
    """Remove IdlerGear section from AGENTS.md.

    Args:
        project_path: Path to the project

    Returns:
        True if removed, False if not present
    """
    agents_file = project_path / "AGENTS.md"

    if not agents_file.exists():
        return False

    content = agents_file.read_text()

    # Look for IdlerGear section markers
    start_marker = "## IdlerGear"
    if start_marker not in content:
        return False

    lines = content.split("\n")
    new_lines = []
    in_idlergear_section = False
    removed = False

    for line in lines:
        if line.startswith("## IdlerGear"):
            in_idlergear_section = True
            removed = True
            continue
        elif in_idlergear_section and line.startswith("## "):
            # Hit next section
            in_idlergear_section = False

        if not in_idlergear_section:
            new_lines.append(line)

    if removed:
        # Clean up extra blank lines
        new_content = "\n".join(new_lines)
        while "\n\n\n" in new_content:
            new_content = new_content.replace("\n\n\n", "\n\n")
        new_content = new_content.strip() + "\n"

        if new_content.strip():
            agents_file.write_text(new_content)
        else:
            # File is empty, remove it
            agents_file.unlink()

    return removed


def remove_claude_settings(project_path: Path) -> bool:
    """Remove IdlerGear-specific Claude settings.

    Args:
        project_path: Path to the project

    Returns:
        True if removed, False if not present
    """
    settings_file = project_path / ".claude" / "settings.json"

    if not settings_file.exists():
        return False

    try:
        with open(settings_file) as f:
            settings = json.load(f)
    except (json.JSONDecodeError, IOError):
        return False

    modified = False

    # Remove idlergear from protectedPaths
    if "protectedPaths" in settings:
        original_count = len(settings["protectedPaths"])
        settings["protectedPaths"] = [
            p for p in settings["protectedPaths"] if not p.startswith(".idlergear")
        ]
        if len(settings["protectedPaths"]) < original_count:
            modified = True

        if not settings["protectedPaths"]:
            del settings["protectedPaths"]

    if modified:
        if settings:
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)
        else:
            settings_file.unlink()
            # Remove .claude dir if empty
            claude_dir = project_path / ".claude"
            if claude_dir.exists() and not any(claude_dir.iterdir()):
                claude_dir.rmdir()

    return modified


def remove_idlergear_data(project_path: Path) -> bool:
    """Remove the .idlergear directory.

    Args:
        project_path: Path to the project

    Returns:
        True if removed, False if not present
    """
    idlergear_dir = project_path / ".idlergear"

    if not idlergear_dir.exists():
        return False

    shutil.rmtree(idlergear_dir)
    return True


def uninstall_idlergear(
    project_path: Path | None = None,
    remove_data: bool = False,
    dry_run: bool = False,
) -> dict[str, bool]:
    """Uninstall IdlerGear from a project.

    Args:
        project_path: Path to the project (defaults to cwd)
        remove_data: If True, also remove .idlergear directory with all data
        dry_run: If True, only report what would be done

    Returns:
        Dict with keys for each component and whether it was/would be removed
    """
    if project_path is None:
        project_path = Path.cwd()

    results = {
        "mcp_config": False,
        "agents_md": False,
        "claude_md": False,
        "rules_file": False,
        "skill": False,
        "hook_scripts": False,
        "claude_settings": False,
        "idlergear_data": False,
    }

    # Check what exists
    mcp_file = project_path / ".mcp.json"
    agents_file = project_path / "AGENTS.md"
    claude_file = project_path / "CLAUDE.md"
    rules_file = project_path / ".claude" / "rules" / "idlergear.md"
    skill_dir = project_path / ".claude" / "skills" / "idlergear"
    hooks_dir = project_path / ".claude" / "hooks"
    settings_file = project_path / ".claude" / "settings.json"
    idlergear_dir = project_path / ".idlergear"

    if mcp_file.exists():
        try:
            with open(mcp_file) as f:
                config = json.load(f)
            if "mcpServers" in config and "idlergear" in config["mcpServers"]:
                results["mcp_config"] = True
        except (json.JSONDecodeError, IOError):
            pass

    if agents_file.exists():
        content = agents_file.read_text()
        if "## IdlerGear" in content:
            results["agents_md"] = True

    if claude_file.exists():
        content = claude_file.read_text()
        if "## IdlerGear Usage" in content:
            results["claude_md"] = True

    if rules_file.exists():
        results["rules_file"] = True

    if skill_dir.exists():
        results["skill"] = True

    # Check for hook scripts installed by idlergear
    from idlergear.install import HOOK_SCRIPTS

    if hooks_dir.exists():
        for script_name in HOOK_SCRIPTS:
            if (hooks_dir / script_name).exists():
                results["hook_scripts"] = True
                break

    if settings_file.exists():
        try:
            with open(settings_file) as f:
                settings = json.load(f)
            if "protectedPaths" in settings:
                if any(p.startswith(".idlergear") for p in settings["protectedPaths"]):
                    results["claude_settings"] = True
        except (json.JSONDecodeError, IOError):
            pass

    if remove_data and idlergear_dir.exists():
        results["idlergear_data"] = True

    if dry_run:
        return results

    # Actually remove
    if results["mcp_config"]:
        results["mcp_config"] = remove_mcp_config(project_path)

    if results["agents_md"]:
        results["agents_md"] = remove_agents_md_section(project_path)

    if results["claude_md"]:
        from idlergear.install import remove_claude_md_section

        results["claude_md"] = remove_claude_md_section(project_path)

    if results["rules_file"]:
        from idlergear.install import remove_rules_file

        results["rules_file"] = remove_rules_file(project_path)

    if results["skill"]:
        from idlergear.install import remove_skill

        results["skill"] = remove_skill(project_path)

    if results["hook_scripts"]:
        from idlergear.install import remove_hook_scripts

        results["hook_scripts"] = remove_hook_scripts(project_path)

    if results["claude_settings"]:
        results["claude_settings"] = remove_claude_settings(project_path)

    if results["idlergear_data"]:
        results["idlergear_data"] = remove_idlergear_data(project_path)

    return results

"""Auto-upgrade functionality for IdlerGear projects.

Detects when IdlerGear has been upgraded and updates project files.
"""

from pathlib import Path
from typing import Tuple

from idlergear import __version__
from idlergear.config import get_config_value, set_config_value, find_idlergear_root


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse a version string like '0.3.17' into a tuple (0, 3, 17).

    Handles versions with or without 'v' prefix.
    """
    version_str = version_str.lstrip("v")
    parts = version_str.split(".")

    # Pad with zeros if needed
    while len(parts) < 3:
        parts.append("0")

    try:
        return (int(parts[0]), int(parts[1]), int(parts[2].split("-")[0]))
    except (ValueError, IndexError):
        return (0, 0, 0)


def get_project_version(project_path: Path | None = None) -> str | None:
    """Get the IdlerGear version stored in the project config."""
    return get_config_value("idlergear_version", project_path=project_path)


def set_project_version(version: str, project_path: Path | None = None) -> None:
    """Store the IdlerGear version in the project config."""
    set_config_value("idlergear_version", version, project_path=project_path)


def needs_upgrade(project_path: Path | None = None) -> bool:
    """Check if the project needs an upgrade.

    Returns True if installed IdlerGear version > project version.
    """
    project_version = get_project_version(project_path)

    if project_version is None:
        # No version stored - needs upgrade to store version
        return True

    installed = parse_version(__version__)
    project = parse_version(project_version)

    return installed > project


def get_upgrade_info(project_path: Path | None = None) -> dict:
    """Get information about available upgrade.

    Returns dict with:
        - needs_upgrade: bool
        - installed_version: str
        - project_version: str | None
    """
    project_version = get_project_version(project_path)

    return {
        "needs_upgrade": needs_upgrade(project_path),
        "installed_version": __version__,
        "project_version": project_version,
    }


def do_upgrade(project_path: Path | None = None, quiet: bool = False) -> dict:
    """Perform the upgrade - reinstall files and update version.

    Args:
        project_path: Path to project root
        quiet: If True, don't print output

    Returns:
        Dict with upgrade results
    """
    from idlergear.install import (
        add_rules_file,
        add_hooks_config,
        install_hook_scripts,
        add_commands,
        add_skill,
    )

    if project_path is None:
        project_path = find_idlergear_root()

    if project_path is None:
        return {"error": "Not in an IdlerGear project"}

    results = {
        "upgraded_from": get_project_version(project_path),
        "upgraded_to": __version__,
        "files": {},
    }

    # Update all files
    results["files"]["rules"] = add_rules_file(project_path)
    results["files"]["hooks_config"] = (
        "updated" if add_hooks_config(project_path) else "unchanged"
    )
    results["files"]["hook_scripts"] = install_hook_scripts(project_path)
    results["files"]["commands"] = add_commands(project_path)
    results["files"]["skill"] = add_skill(project_path)

    # Store new version
    set_project_version(__version__, project_path)

    return results


def check_and_prompt_upgrade(project_path: Path | None = None) -> bool:
    """Check if upgrade needed and prompt user.

    Returns True if upgrade was performed, False otherwise.
    """

    if project_path is None:
        project_path = find_idlergear_root()

    if project_path is None:
        return False

    info = get_upgrade_info(project_path)

    if not info["needs_upgrade"]:
        return False

    # Print upgrade notice
    old_version = info["project_version"] or "unknown"
    new_version = info["installed_version"]

    print(f"\n[IdlerGear] Upgrade available: {old_version} -> {new_version}")

    # Auto-upgrade (can be made interactive later)
    # For now, just upgrade automatically and notify
    results = do_upgrade(project_path, quiet=True)

    # Count what was updated
    updated_count = 0
    for key, value in results["files"].items():
        if isinstance(value, dict):
            updated_count += sum(
                1 for v in value.values() if v in ("created", "updated")
            )
        elif value in ("created", "updated"):
            updated_count += 1

    if updated_count > 0:
        print(f"[IdlerGear] Upgraded {updated_count} file(s) in .claude/")
    else:
        print("[IdlerGear] Version updated (files already current)")

    print()

    return True

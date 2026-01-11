"""Self-update capability for IdlerGear.

Detects install method and provides commands to upgrade IdlerGear itself.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Tuple
import urllib.request
import json
import time

from idlergear import __version__


class InstallMethod(str, Enum):
    """How IdlerGear was installed."""

    PIPX = "pipx"
    PIP_USER = "pip-user"
    PIP_VENV = "pip-venv"
    PIP_SYSTEM = "pip-system"
    EDITABLE = "editable"
    UNKNOWN = "unknown"


@dataclass
class InstallInfo:
    """Information about how IdlerGear is installed."""

    method: InstallMethod
    path: Path | None
    can_upgrade: bool
    upgrade_command: str
    requires_sudo: bool = False
    message: str = ""


@dataclass
class VersionInfo:
    """Version comparison result."""

    current: str
    latest: str | None
    update_available: bool
    error: str | None = None


# Cache file for rate limiting GitHub API calls
CACHE_FILE = Path.home() / ".cache" / "idlergear" / "version_cache.json"
CACHE_TTL_SECONDS = 86400  # 24 hours


def get_github_repo() -> str:
    """Get the GitHub repository for IdlerGear."""
    return "marctjones/idlergear"


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse a version string like '0.3.17' into a tuple (0, 3, 17)."""
    version_str = version_str.lstrip("v")
    parts = version_str.split(".")

    while len(parts) < 3:
        parts.append("0")

    try:
        return (int(parts[0]), int(parts[1]), int(parts[2].split("-")[0]))
    except (ValueError, IndexError):
        return (0, 0, 0)


def compare_versions(current: str, latest: str) -> bool:
    """Return True if latest > current."""
    return parse_version(latest) > parse_version(current)


def _load_cache() -> dict | None:
    """Load cached version info if still valid."""
    if not CACHE_FILE.exists():
        return None

    try:
        data = json.loads(CACHE_FILE.read_text())
        if time.time() - data.get("timestamp", 0) < CACHE_TTL_SECONDS:
            return data
    except (json.JSONDecodeError, KeyError):
        pass

    return None


def _save_cache(version: str) -> None:
    """Save version info to cache."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(
            {
                "version": version,
                "timestamp": time.time(),
            }
        )
    )


def get_latest_version(use_cache: bool = True) -> VersionInfo:
    """Get the latest version from GitHub releases.

    Args:
        use_cache: If True, use cached result if available

    Returns:
        VersionInfo with current and latest versions
    """
    current = __version__

    # Check cache first
    if use_cache:
        cached = _load_cache()
        if cached:
            latest = cached["version"]
            return VersionInfo(
                current=current,
                latest=latest,
                update_available=compare_versions(current, latest),
            )

    # Query GitHub API
    repo = get_github_repo()
    url = f"https://api.github.com/repos/{repo}/releases/latest"

    try:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode())
            latest = data.get("tag_name", "").lstrip("v")

            if latest:
                _save_cache(latest)
                return VersionInfo(
                    current=current,
                    latest=latest,
                    update_available=compare_versions(current, latest),
                )
            else:
                return VersionInfo(
                    current=current,
                    latest=None,
                    update_available=False,
                    error="No releases found",
                )

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return VersionInfo(
                current=current,
                latest=None,
                update_available=False,
                error="Repository not found or no releases",
            )
        elif e.code == 403:
            return VersionInfo(
                current=current,
                latest=None,
                update_available=False,
                error="GitHub API rate limited. Try again later.",
            )
        else:
            return VersionInfo(
                current=current,
                latest=None,
                update_available=False,
                error=f"GitHub API error: {e.code}",
            )
    except urllib.error.URLError as e:
        return VersionInfo(
            current=current,
            latest=None,
            update_available=False,
            error=f"Network error: {e.reason}",
        )
    except Exception as e:
        return VersionInfo(
            current=current,
            latest=None,
            update_available=False,
            error=str(e),
        )


def detect_install_method() -> InstallInfo:
    """Detect how IdlerGear was installed and return upgrade instructions."""
    import idlergear

    pkg_path = Path(idlergear.__file__).parent

    # Check for editable install (.egg-link or no dist-info in site-packages)
    # Editable installs have the source directly, not in site-packages
    if _is_editable_install(pkg_path):
        return InstallInfo(
            method=InstallMethod.EDITABLE,
            path=pkg_path,
            can_upgrade=False,
            upgrade_command="git pull && pip install -e .",
            message="Editable install detected. Use git to update the source.",
        )

    # Check for pipx install
    pipx_venv = Path.home() / ".local" / "pipx" / "venvs" / "idlergear"
    if pipx_venv.exists() or str(pkg_path).startswith(str(pipx_venv)):
        return InstallInfo(
            method=InstallMethod.PIPX,
            path=pipx_venv,
            can_upgrade=True,
            upgrade_command="pipx upgrade idlergear",
        )

    # Check if in a virtualenv
    if sys.prefix != sys.base_prefix:
        return InstallInfo(
            method=InstallMethod.PIP_VENV,
            path=Path(sys.prefix),
            can_upgrade=True,
            upgrade_command=f"pip install --upgrade git+https://github.com/{get_github_repo()}.git",
        )

    # Check for user install (~/.local/lib/python*/site-packages/)
    user_site = Path.home() / ".local" / "lib"
    if str(pkg_path).startswith(str(user_site)):
        return InstallInfo(
            method=InstallMethod.PIP_USER,
            path=pkg_path,
            can_upgrade=True,
            upgrade_command=f"pip install --user --upgrade git+https://github.com/{get_github_repo()}.git",
        )

    # Check for system install
    if _is_system_install(pkg_path):
        can_write = os.access(pkg_path, os.W_OK)
        return InstallInfo(
            method=InstallMethod.PIP_SYSTEM,
            path=pkg_path,
            can_upgrade=can_write,
            upgrade_command=f"sudo pip install --upgrade git+https://github.com/{get_github_repo()}.git",
            requires_sudo=not can_write,
            message=""
            if can_write
            else "System install requires elevated permissions.",
        )

    # Unknown install method
    return InstallInfo(
        method=InstallMethod.UNKNOWN,
        path=pkg_path,
        can_upgrade=False,
        upgrade_command="pip install --upgrade idlergear",
        message="Could not determine install method.",
    )


def _is_editable_install(pkg_path: Path) -> bool:
    """Check if this is an editable (development) install."""
    # Editable installs typically have a pyproject.toml or setup.py nearby
    # Check parent and grandparent (for src/ layout)
    for ancestor in [pkg_path.parent, pkg_path.parent.parent]:
        if (ancestor / "pyproject.toml").exists() or (ancestor / "setup.py").exists():
            # Also verify this looks like a source directory, not site-packages
            if "site-packages" not in str(pkg_path):
                return True

    # Also check for .egg-link in site-packages
    try:
        import site

        for sp in site.getsitepackages() + [site.getusersitepackages()]:
            egg_link = Path(sp) / "idlergear.egg-link"
            if egg_link.exists():
                return True
    except Exception:
        pass

    return False


def _is_system_install(pkg_path: Path) -> bool:
    """Check if installed in system site-packages."""
    system_prefixes = ["/usr", "/usr/local", sys.base_prefix]
    return any(str(pkg_path).startswith(p) for p in system_prefixes)


def do_self_update(
    version: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Perform self-update.

    Args:
        version: Specific version to install (None for latest)
        dry_run: If True, just return what would be done

    Returns:
        Dict with update results
    """
    install_info = detect_install_method()
    version_info = get_latest_version()

    result = {
        "current_version": version_info.current,
        "target_version": version or version_info.latest,
        "install_method": install_info.method.value,
        "upgrade_command": install_info.upgrade_command,
        "can_upgrade": install_info.can_upgrade,
        "requires_sudo": install_info.requires_sudo,
        "dry_run": dry_run,
        "success": False,
        "message": "",
    }

    if not install_info.can_upgrade:
        result["message"] = (
            install_info.message or "Cannot auto-upgrade with this install method."
        )
        return result

    if not version_info.update_available and version is None:
        result["message"] = "Already at latest version."
        result["success"] = True
        return result

    if dry_run:
        result["message"] = f"Would run: {install_info.upgrade_command}"
        result["success"] = True
        return result

    # Build the actual command
    cmd = install_info.upgrade_command

    # If specific version requested, modify command
    if version:
        repo = get_github_repo()
        if install_info.method == InstallMethod.PIPX:
            # pipx doesn't support version pinning easily, use pip url
            cmd = f"pipx runpip idlergear install git+https://github.com/{repo}.git@v{version}"
        else:
            cmd = cmd.replace(
                f"git+https://github.com/{repo}.git",
                f"git+https://github.com/{repo}.git@v{version}",
            )

    try:
        # Run the upgrade command
        subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
        result["success"] = True
        result["message"] = f"Successfully upgraded to {result['target_version']}"

        # Clear version cache
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()

    except subprocess.CalledProcessError as e:
        result["success"] = False
        result["message"] = f"Upgrade failed: {e.stderr or e.stdout or str(e)}"
    except Exception as e:
        result["success"] = False
        result["message"] = f"Upgrade failed: {e}"

    return result

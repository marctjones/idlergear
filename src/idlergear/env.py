"""Environment detection and management for IdlerGear.

This module provides MCP tools for detecting and managing development environments:
- Python/Node/etc version detection
- Virtual environment detection (venv, conda, poetry)
- PATH analysis
- Consolidated environment info
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any


def detect_python_env() -> Dict[str, Any]:
    """Detect Python environment information.

    Returns:
        Dictionary with Python version, executable path, venv info, etc.
    """
    result = {
        "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "executable": sys.executable,
        "prefix": sys.prefix,
        "base_prefix": sys.base_prefix,
        "in_virtualenv": sys.prefix != sys.base_prefix,
        "venv_type": None,
        "venv_path": None,
    }

    # Detect venv type
    if result["in_virtualenv"]:
        if "CONDA_DEFAULT_ENV" in os.environ:
            result["venv_type"] = "conda"
            result["venv_path"] = os.environ.get("CONDA_PREFIX")
        elif "POETRY_ACTIVE" in os.environ or (Path(sys.prefix) / "poetry.lock").exists():
            result["venv_type"] = "poetry"
            result["venv_path"] = sys.prefix
        elif "VIRTUAL_ENV" in os.environ:
            result["venv_type"] = "venv"
            result["venv_path"] = os.environ.get("VIRTUAL_ENV")
        else:
            result["venv_type"] = "unknown"
            result["venv_path"] = sys.prefix

    return result


def detect_node_env() -> Optional[Dict[str, Any]]:
    """Detect Node.js environment information.

    Returns:
        Dictionary with Node version, npm version, etc., or None if not available.
    """
    node_path = shutil.which("node")
    if not node_path:
        return None

    try:
        node_version = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()

        npm_version = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()

        return {
            "node_version": node_version,
            "npm_version": npm_version,
            "node_path": node_path,
        }
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return {"node_path": node_path, "error": "Could not get version"}


def detect_rust_env() -> Optional[Dict[str, Any]]:
    """Detect Rust environment information.

    Returns:
        Dictionary with Rust/Cargo version, or None if not available.
    """
    cargo_path = shutil.which("cargo")
    if not cargo_path:
        return None

    try:
        cargo_version = subprocess.run(
            ["cargo", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()

        rustc_version = subprocess.run(
            ["rustc", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()

        return {
            "cargo_version": cargo_version,
            "rustc_version": rustc_version,
            "cargo_path": cargo_path,
        }
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return {"cargo_path": cargo_path, "error": "Could not get version"}


def detect_dotnet_env() -> Optional[Dict[str, Any]]:
    """Detect .NET environment information.

    Returns:
        Dictionary with .NET version, or None if not available.
    """
    dotnet_path = shutil.which("dotnet")
    if not dotnet_path:
        return None

    try:
        dotnet_version = subprocess.run(
            ["dotnet", "--version"],
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()

        return {
            "dotnet_version": dotnet_version,
            "dotnet_path": dotnet_path,
        }
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return {"dotnet_path": dotnet_path, "error": "Could not get version"}


def get_environment_info() -> Dict[str, Any]:
    """Get consolidated environment information.

    Returns:
        Dictionary with all detected environment info.
        ~60% token savings vs running multiple commands!
    """
    info = {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "python": detect_python_env(),
        "node": detect_node_env(),
        "rust": detect_rust_env(),
        "dotnet": detect_dotnet_env(),
        "shell": os.environ.get("SHELL", "unknown"),
        "cwd": os.getcwd(),
        "path_dirs": os.environ.get("PATH", "").split(os.pathsep),
    }

    return info


def which_enhanced(command: str) -> Dict[str, Any]:
    """Enhanced 'which' command showing ALL matches and their sources.

    Args:
        command: The command to search for

    Returns:
        Dictionary with all matches, their paths, and additional info
    """
    result = {
        "command": command,
        "matches": [],
        "primary": None,
    }

    # Get primary match
    primary_path = shutil.which(command)
    if primary_path:
        result["primary"] = primary_path

    # Search all PATH directories
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    for path_dir in path_dirs:
        path_obj = Path(path_dir)
        if not path_obj.exists():
            continue

        potential_match = path_obj / command
        if potential_match.exists() and os.access(potential_match, os.X_OK):
            match_info = {
                "path": str(potential_match),
                "is_primary": str(potential_match) == primary_path,
                "is_symlink": potential_match.is_symlink(),
            }

            if potential_match.is_symlink():
                match_info["symlink_target"] = str(potential_match.resolve())

            result["matches"].append(match_info)

    return result


def detect_project_type(path: Optional[Path] = None) -> Dict[str, Any]:
    """Detect the project type based on files present in the directory.

    Args:
        path: Directory to analyze (default: current directory)

    Returns:
        Dictionary with detected project types and markers
    """
    if path is None:
        path = Path.cwd()
    else:
        path = Path(path)

    markers = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        "node": ["package.json", "package-lock.json", "yarn.lock"],
        "rust": ["Cargo.toml", "Cargo.lock"],
        "dotnet": ["*.csproj", "*.sln", "*.fsproj"],
        "go": ["go.mod", "go.sum"],
        "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "ruby": ["Gemfile", "Gemfile.lock"],
    }

    detected = {
        "project_types": [],
        "markers_found": {},
        "path": str(path),
    }

    for project_type, marker_files in markers.items():
        found_markers = []
        for marker in marker_files:
            # Handle glob patterns for .csproj, .sln, etc.
            if "*" in marker:
                matches = list(path.glob(marker))
                if matches:
                    found_markers.extend([m.name for m in matches])
            else:
                if (path / marker).exists():
                    found_markers.append(marker)

        if found_markers:
            detected["project_types"].append(project_type)
            detected["markers_found"][project_type] = found_markers

    return detected


def find_virtualenv(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Find and identify virtual environments in the project directory.

    Args:
        path: Directory to search (default: current directory)

    Returns:
        Dictionary with venv info, or None if not found
    """
    if path is None:
        path = Path.cwd()
    else:
        path = Path(path)

    # Common venv directory names
    venv_names = ["venv", ".venv", "env", ".env", "virtualenv"]

    for venv_name in venv_names:
        venv_path = path / venv_name
        if not venv_path.exists():
            continue

        # Check for Python venv markers
        if (venv_path / "bin" / "python").exists() or (venv_path / "Scripts" / "python.exe").exists():
            return {
                "type": "venv",
                "path": str(venv_path),
                "name": venv_name,
                "python": str(venv_path / "bin" / "python") if (venv_path / "bin" / "python").exists() else str(venv_path / "Scripts" / "python.exe"),
            }

    # Check for poetry.lock
    if (path / "poetry.lock").exists():
        return {
            "type": "poetry",
            "path": None,  # Poetry manages venv elsewhere
            "name": "poetry",
            "command": "poetry run python",
        }

    # Check for Pipfile (pipenv)
    if (path / "Pipfile").exists():
        return {
            "type": "pipenv",
            "path": None,  # Pipenv manages venv elsewhere
            "name": "pipenv",
            "command": "pipenv run python",
        }

    return None

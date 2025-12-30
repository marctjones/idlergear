"""Configuration management for IdlerGear."""

import os
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w


def find_idlergear_root(start_path: str = ".") -> Path | None:
    """Find the nearest .idlergear directory by walking up from start_path."""
    current = Path(start_path).resolve()

    while current != current.parent:
        idlergear_path = current / ".idlergear"
        if idlergear_path.is_dir():
            return current
        current = current.parent

    # Check root
    idlergear_path = current / ".idlergear"
    if idlergear_path.is_dir():
        return current

    return None


def get_config_path(project_path: Path | None = None) -> Path | None:
    """Get path to config.toml, or None if not initialized."""
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None
    return project_path / ".idlergear" / "config.toml"


def load_config(project_path: Path | None = None) -> dict[str, Any]:
    """Load configuration from config.toml."""
    config_path = get_config_path(project_path)
    if config_path is None or not config_path.exists():
        return {}

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def save_config(config: dict[str, Any], project_path: Path | None = None) -> None:
    """Save configuration to config.toml."""
    config_path = get_config_path(project_path)
    if config_path is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    with open(config_path, "wb") as f:
        tomli_w.dump(config, f)


def get_config_value(key: str, project_path: Path | None = None) -> Any:
    """Get a configuration value by dot-notation key (e.g., 'github.token')."""
    config = load_config(project_path)

    # Handle environment variable fallbacks
    env_mappings = {
        "github.token": "GITHUB_TOKEN",
    }

    parts = key.split(".")
    value = config
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            # Try environment variable fallback
            if key in env_mappings:
                return os.environ.get(env_mappings[key])
            return None

    # Return env var if config value is empty
    if value in (None, "") and key in env_mappings:
        return os.environ.get(env_mappings[key])

    return value


def set_config_value(key: str, value: str, project_path: Path | None = None) -> None:
    """Set a configuration value by dot-notation key."""
    config = load_config(project_path)

    parts = key.split(".")
    current = config

    # Navigate/create nested structure
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set the value
    current[parts[-1]] = value

    save_config(config, project_path)

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


# Configuration schemas with defaults and validation
TEST_CONFIG_SCHEMA = {
    "test": {
        "warn_stale_on_commit": {
            "type": "boolean",
            "default": True,
            "description": "Warn about stale tests when committing",
        },
        "stale_threshold_seconds": {
            "type": "integer",
            "default": 3600,
            "description": "Seconds before tests are considered stale",
        },
        "block_on_failure": {
            "type": "boolean",
            "default": False,
            "description": "Block commits if tests are failing",
        },
    }
}

PROJECTS_CONFIG_SCHEMA = {
    "projects": {
        "default_project": {
            "type": "string",
            "default": None,
            "description": "Default project board for new tasks",
        },
        "default_column": {
            "type": "string",
            "default": "Backlog",
            "description": "Default column for auto-added tasks",
        },
        "auto_add": {
            "type": "boolean",
            "default": False,
            "description": "Automatically add new tasks to default project",
        },
    }
}

# Combined schema registry
CONFIG_SCHEMAS = {
    "test": TEST_CONFIG_SCHEMA["test"],
    "projects": PROJECTS_CONFIG_SCHEMA["projects"],
}


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


def _get_schema_default(key: str) -> Any:
    """Get default value from schema for a config key."""
    parts = key.split(".")
    if len(parts) < 2:
        return None

    category = parts[0]
    if category not in CONFIG_SCHEMAS:
        return None

    # Navigate schema to find the field
    schema = CONFIG_SCHEMAS[category]
    field_path = parts[1:]

    current = schema
    for part in field_path:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    # Return default value if available
    if isinstance(current, dict) and "default" in current:
        return current["default"]

    return None


def _validate_config_type(key: str, value: Any) -> bool:
    """Validate that a config value matches its schema type."""
    parts = key.split(".")
    if len(parts) < 2:
        return True  # No schema, allow any value

    category = parts[0]
    if category not in CONFIG_SCHEMAS:
        return True  # No schema, allow any value

    # Navigate schema to find the field
    schema = CONFIG_SCHEMAS[category]
    field_path = parts[1:]

    current = schema
    for part in field_path:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return True  # No schema for this field

    # Check type if specified
    if isinstance(current, dict) and "type" in current:
        expected_type = current["type"]

        type_validators = {
            "boolean": lambda v: isinstance(v, bool),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "string": lambda v: isinstance(v, str),
            "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        }

        validator = type_validators.get(expected_type)
        if validator:
            return validator(value)

    return True


def get_config_value(key: str, project_path: Path | None = None) -> Any:
    """Get a configuration value by dot-notation key (e.g., 'github.token').

    Returns the value from config file, environment variable, or schema default.
    """
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
                env_value = os.environ.get(env_mappings[key])
                if env_value is not None:
                    return env_value

            # Try schema default
            default_value = _get_schema_default(key)
            if default_value is not None:
                return default_value

            return None

    # Return env var if config value is empty
    if value in (None, "") and key in env_mappings:
        env_value = os.environ.get(env_mappings[key])
        if env_value is not None:
            return env_value

    # Return schema default if value is None
    if value is None:
        default_value = _get_schema_default(key)
        if default_value is not None:
            return default_value

    return value


def set_config_value(
    key: str, value: str | bool | int | float, project_path: Path | None = None
) -> None:
    """Set a configuration value by dot-notation key.

    Args:
        key: Dot-notation config key (e.g., 'test.block_on_failure')
        value: Value to set (type will be validated against schema if available)
        project_path: Optional project path

    Raises:
        ValueError: If value type doesn't match schema
    """
    # Validate type if schema exists
    if not _validate_config_type(key, value):
        parts = key.split(".")
        category = parts[0]
        if category in CONFIG_SCHEMAS:
            schema = CONFIG_SCHEMAS[category]
            field_path = parts[1:]
            current = schema
            for part in field_path:
                if isinstance(current, dict) and part in current:
                    current = current[part]
            expected_type = current.get("type", "unknown") if isinstance(current, dict) else "unknown"
            actual_type = type(value).__name__
            raise ValueError(
                f"Invalid type for {key}: expected {expected_type}, got {actual_type}"
            )

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

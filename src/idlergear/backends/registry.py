"""Backend registry for IdlerGear.

Manages backend instances and configuration. The registry allows different
knowledge types to use different backends.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from idlergear.backends.github import (
    GitHubExploreBackend,
    GitHubNoteBackend,
    GitHubPlanBackend,
    GitHubReferenceBackend,
    GitHubTaskBackend,
    GitHubVisionBackend,
)
from idlergear.backends.local import (
    LocalExploreBackend,
    LocalNoteBackend,
    LocalPlanBackend,
    LocalReferenceBackend,
    LocalTaskBackend,
    LocalVisionBackend,
)

# Type alias for backend types
BackendType = Literal["task", "note", "explore", "reference", "plan", "vision"]

# Backend class registry (for built-in backends)
_backend_classes: dict[str, dict[str, type]] = {
    "task": {"local": LocalTaskBackend, "github": GitHubTaskBackend},
    "note": {"local": LocalNoteBackend, "github": GitHubNoteBackend},
    "explore": {"local": LocalExploreBackend, "github": GitHubExploreBackend},
    "reference": {"local": LocalReferenceBackend, "github": GitHubReferenceBackend},
    "plan": {"local": LocalPlanBackend, "github": GitHubPlanBackend},
    "vision": {"local": LocalVisionBackend, "github": GitHubVisionBackend},
}

# Shell backend class mapping
_shell_backend_classes: dict[str, type] = {}

# Cached backend instances per project
_backend_instances: dict[str, dict[str, Any]] = {}


def register_backend(
    backend_type: BackendType,
    backend_name: str,
    backend_class: type,
) -> None:
    """Register a new backend class.

    Args:
        backend_type: Type of backend (task, note, etc.)
        backend_name: Name of the backend (local, github, etc.)
        backend_class: The backend class to register
    """
    if backend_type not in _backend_classes:
        _backend_classes[backend_type] = {}
    _backend_classes[backend_type][backend_name] = backend_class


def get_backend(
    backend_type: BackendType,
    project_path: Path | None = None,
) -> Any:
    """Get a backend instance for the given type.

    Args:
        backend_type: Type of backend to get
        project_path: Optional project path override

    Returns:
        A backend instance implementing the appropriate protocol
    """
    from idlergear.config import find_idlergear_root, get_config_value

    # Resolve project path
    if project_path is None:
        project_path = find_idlergear_root()

    # Create cache key
    cache_key = str(project_path) if project_path else "default"

    # Check cache
    if cache_key not in _backend_instances:
        _backend_instances[cache_key] = {}

    if backend_type in _backend_instances[cache_key]:
        return _backend_instances[cache_key][backend_type]

    # Get configured backend name (default to "local")
    backend_name = get_config_value(
        f"backends.{backend_type}", project_path=project_path
    )
    if backend_name is None:
        backend_name = "local"

    # Get backend class
    if backend_type not in _backend_classes:
        raise ValueError(f"Unknown backend type: {backend_type}")

    instance = None

    # Check built-in backends first
    if backend_name in _backend_classes[backend_type]:
        backend_class = _backend_classes[backend_type][backend_name]
        instance = backend_class(project_path=project_path)
    else:
        # Try loading as a shell backend
        instance = _try_load_shell_backend(backend_type, backend_name, project_path)

    if instance is None:
        raise ValueError(f"Unknown backend '{backend_name}' for type '{backend_type}'")

    # Cache it
    _backend_instances[cache_key][backend_type] = instance

    return instance


def _try_load_shell_backend(
    backend_type: BackendType,
    backend_name: str,
    project_path: Path | None,
) -> Any | None:
    """Try to load a shell-based backend from TOML configuration.

    Args:
        backend_type: Type of backend (task, note, etc.)
        backend_name: Name of the backend (github, jira, etc.)
        project_path: Optional project path

    Returns:
        A shell backend instance, or None if config not found
    """
    from idlergear.backends.shell import (
        ShellExploreBackend,
        ShellReferenceBackend,
        ShellTaskBackend,
        load_shell_backend_config,
    )

    # Map backend types to shell backend classes
    shell_backend_classes: dict[str, type] = {
        "task": ShellTaskBackend,
        "explore": ShellExploreBackend,
        "reference": ShellReferenceBackend,
    }

    # Only certain types support shell backends currently
    if backend_type not in shell_backend_classes:
        return None

    # Try to load configuration
    config = load_shell_backend_config(backend_name, backend_type, project_path)
    if config is None:
        return None

    # Create instance
    backend_class = shell_backend_classes[backend_type]
    return backend_class(config=config, project_path=project_path)


def clear_backend_cache() -> None:
    """Clear the backend instance cache."""
    _backend_instances.clear()


def get_configured_backend_name(
    backend_type: BackendType,
    project_path: Path | None = None,
) -> str:
    """Get the configured backend name for a type."""
    from idlergear.config import get_config_value

    backend_name = get_config_value(
        f"backends.{backend_type}", project_path=project_path
    )
    return backend_name if backend_name else "local"


def list_available_backends(
    backend_type: BackendType,
    project_path: Path | None = None,
) -> list[str]:
    """List available backends for a type.

    Includes both built-in backends and shell backends from TOML config.
    """
    backends = set()

    # Add built-in backends
    if backend_type in _backend_classes:
        backends.update(_backend_classes[backend_type].keys())

    # Discover shell backends from TOML files
    shell_backends = _discover_shell_backends(backend_type, project_path)
    backends.update(shell_backends)

    return sorted(backends)


def _discover_shell_backends(
    backend_type: BackendType,
    project_path: Path | None = None,
) -> list[str]:
    """Discover available shell backends from TOML configuration files.

    Searches for .toml files in:
    1. .idlergear/backends/ in project
    2. ~/.config/idlergear/backends/

    Returns:
        List of backend names that support the given type
    """
    import sys

    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    from idlergear.config import find_idlergear_root

    if project_path is None:
        project_path = find_idlergear_root()

    backends = []

    # Search paths for backend TOML files
    search_dirs = []
    if project_path:
        search_dirs.append(project_path / ".idlergear" / "backends")

    home = Path.home()
    search_dirs.append(home / ".config" / "idlergear" / "backends")

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for toml_file in search_dir.glob("*.toml"):
            backend_name = toml_file.stem

            # Skip if already found (project takes precedence)
            if backend_name in backends:
                continue

            # Check if this backend supports the requested type
            try:
                with open(toml_file, "rb") as f:
                    config = tomllib.load(f)

                if backend_type in config:
                    backends.append(backend_name)
            except Exception:
                # Skip invalid config files
                pass

    return backends

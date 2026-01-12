"""Generator registry for discovering and managing generators.

This module provides functions for:
- Registering generators (built-in, shell, custom)
- Discovering available generators on the system
- Managing generator configuration (enable/disable)
- Loading generator config from TOML files
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from idlergear.generators.base import Generator, GeneratorConfig

# Registry of available generators
_generators: dict[str, type["Generator"]] = {}

# Cached config
_config_cache: dict[str, "GeneratorConfig"] = {}


def register_generator(name: str, generator_class: type["Generator"]) -> None:
    """Register a generator class.

    Args:
        name: Generator name
        generator_class: Generator class to register
    """
    _generators[name] = generator_class


def get_generator(name: str, project_path: Path | None = None) -> "Generator | None":
    """Get a generator instance by name.

    Args:
        name: Generator name
        project_path: Optional project path for loading config

    Returns:
        Generator instance or None if not found
    """
    if name not in _generators:
        # Try to load as custom generator from config
        config = _load_generator_config(name, project_path)
        if config:
            from idlergear.generators.base import ShellGenerator

            class CustomShellGenerator(ShellGenerator):
                pass

            CustomShellGenerator.name = name
            CustomShellGenerator.requires = config.requires
            return CustomShellGenerator(config)
        return None

    generator_class = _generators[name]
    config = _load_generator_config(name, project_path)
    return generator_class(config)


def list_generators(project_path: Path | None = None) -> list[dict[str, Any]]:
    """List all known generators with their status.

    Args:
        project_path: Optional project path for loading config

    Returns:
        List of generator status dicts
    """
    results = []

    # Built-in generators
    for name, gen_class in _generators.items():
        config = _load_generator_config(name, project_path)
        gen = gen_class(config)
        results.append(gen.get_status())

    # Custom generators from config
    custom_gens = _discover_custom_generators(project_path)
    for name, config in custom_gens.items():
        if name not in _generators:
            from idlergear.generators.base import ShellGenerator

            gen = ShellGenerator(config)
            gen.name = name
            gen.requires = config.requires
            results.append(gen.get_status())

    return sorted(results, key=lambda g: g["name"])


def get_enabled_generators(project_path: Path | None = None) -> list[str]:
    """Get list of enabled generator names.

    Args:
        project_path: Optional project path

    Returns:
        List of enabled generator names
    """
    enabled = []
    for name in _generators:
        config = _load_generator_config(name, project_path)
        if config and config.enabled:
            enabled.append(name)
    return enabled


def detect_available_generators(project_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Detect which generators can run on this system.

    Args:
        project_path: Optional project path

    Returns:
        Dict mapping generator name to detection result
    """
    results = {}

    for name, gen_class in _generators.items():
        config = _load_generator_config(name, project_path)
        gen = gen_class(config)
        available = gen.detect()
        missing = gen.get_missing_deps() if not available else {"shell": [], "python": []}

        results[name] = {
            "available": available,
            "missing": missing,
            "type": gen.generator_type.value,
        }

    return results


def enable_generator(name: str, project_path: Path | None = None) -> bool:
    """Enable a generator.

    Args:
        name: Generator name
        project_path: Optional project path

    Returns:
        True if successful
    """
    return _set_generator_enabled(name, True, project_path)


def disable_generator(name: str, project_path: Path | None = None) -> bool:
    """Disable a generator.

    Args:
        name: Generator name
        project_path: Optional project path

    Returns:
        True if successful
    """
    return _set_generator_enabled(name, False, project_path)


def _set_generator_enabled(name: str, enabled: bool, project_path: Path | None = None) -> bool:
    """Set generator enabled state.

    Args:
        name: Generator name
        enabled: Whether to enable or disable
        project_path: Optional project path

    Returns:
        True if successful
    """
    from idlergear.config import find_idlergear_root, set_config_value

    if project_path is None:
        project_path = find_idlergear_root()

    if project_path is None:
        return False

    # Update config
    set_config_value(f"generators.{name}.enabled", enabled, project_path=project_path)

    # Clear cache
    cache_key = f"{project_path}:{name}"
    if cache_key in _config_cache:
        del _config_cache[cache_key]

    return True


def _load_generator_config(
    name: str, project_path: Path | None = None
) -> "GeneratorConfig | None":
    """Load generator configuration from project config.

    Args:
        name: Generator name
        project_path: Optional project path

    Returns:
        GeneratorConfig or None
    """
    from idlergear.config import find_idlergear_root, get_config_value
    from idlergear.generators.base import GeneratorConfig, GeneratorType

    if project_path is None:
        project_path = find_idlergear_root()

    # Check cache
    cache_key = f"{project_path}:{name}"
    if cache_key in _config_cache:
        return _config_cache[cache_key]

    # Get config
    config_data = get_config_value(f"generators.{name}", project_path=project_path)

    if config_data is None:
        # Return default config for known generators
        if name in _generators:
            gen_class = _generators[name]
            config = GeneratorConfig(
                name=name,
                generator_type=gen_class.generator_type,
                requires=getattr(gen_class, "requires", []),
                python_deps=getattr(gen_class, "python_deps", []),
            )
            _config_cache[cache_key] = config
            return config
        return None

    # Parse config
    if isinstance(config_data, dict):
        config_data["name"] = name
        config = GeneratorConfig.from_dict(config_data)
    else:
        # Simple enabled/disabled value
        config = GeneratorConfig(name=name, enabled=bool(config_data))

    _config_cache[cache_key] = config
    return config


def _discover_custom_generators(
    project_path: Path | None = None,
) -> dict[str, "GeneratorConfig"]:
    """Discover custom generators from config.

    Args:
        project_path: Optional project path

    Returns:
        Dict of generator name to config
    """
    from idlergear.config import find_idlergear_root, get_config_value
    from idlergear.generators.base import GeneratorConfig

    if project_path is None:
        project_path = find_idlergear_root()

    generators_config = get_config_value("generators", project_path=project_path)
    if not generators_config or not isinstance(generators_config, dict):
        return {}

    result = {}
    for name, config_data in generators_config.items():
        if name == "enabled":  # Skip the enabled list
            continue
        if name in _generators:  # Skip built-in generators
            continue
        if not isinstance(config_data, dict):
            continue

        config_data["name"] = name
        result[name] = GeneratorConfig.from_dict(config_data)

    return result


def _load_toml_config(path: Path) -> dict[str, Any]:
    """Load TOML configuration file.

    Args:
        path: Path to TOML file

    Returns:
        Parsed configuration dict
    """
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    with open(path, "rb") as f:
        return tomllib.load(f)


# Register built-in generators
def _register_builtin_generators() -> None:
    """Register the built-in generators."""
    from idlergear.generators.builtin import (
        PdocGenerator,
        RustGenerator,
        DotNetGenerator,
    )

    register_generator("pdoc", PdocGenerator)
    register_generator("rust", RustGenerator)
    register_generator("dotnet", DotNetGenerator)


# Defer registration to avoid circular imports
def _ensure_registered() -> None:
    """Ensure built-in generators are registered."""
    if not _generators:
        try:
            _register_builtin_generators()
        except ImportError:
            pass  # Generators not available yet

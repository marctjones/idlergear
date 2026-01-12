"""Generator configuration system for IdlerGear.

This module provides a configuration and discovery system for documentation
generators that create "generated" references from source code, API specs,
and other sources.

Generator Types:
- built-in: Pure Python generators (pdoc, typer, click)
- shell: External command generators (rustdoc, dotnet, protobuf)
- custom: User-defined generators via TOML config

Example Configuration:
    [generators]
    enabled = ["pdoc", "rustdoc"]

    [generators.rustdoc]
    enabled = true
    requires = ["cargo"]
    output = "target/doc/{crate}.json"
"""

from idlergear.generators.base import (
    Generator,
    GeneratorConfig,
    GeneratorResult,
    GeneratorType,
)
from idlergear.generators.registry import (
    detect_available_generators,
    disable_generator,
    enable_generator,
    get_enabled_generators,
    get_generator,
    list_generators,
    register_generator,
)

__all__ = [
    # Base classes
    "Generator",
    "GeneratorConfig",
    "GeneratorResult",
    "GeneratorType",
    # Registry functions
    "register_generator",
    "get_generator",
    "list_generators",
    "get_enabled_generators",
    "detect_available_generators",
    "enable_generator",
    "disable_generator",
]

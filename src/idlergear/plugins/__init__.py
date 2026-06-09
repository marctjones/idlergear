"""Plugin system for IdlerGear integrations.

The plugin system allows IdlerGear to integrate with external tools while
maintaining its core value proposition: structured, backend-agnostic knowledge.

Plugin Types:
- Observability: Export logs/metrics (Langfuse, Helicone)
"""

from .base import IdlerGearPlugin, PluginCapability, PluginRegistry
from .langfuse import LangfusePlugin

__all__ = [
    "IdlerGearPlugin",
    "PluginCapability",
    "PluginRegistry",
    "LangfusePlugin",
]

"""Plugin system for IdlerGear integrations.

The plugin system allows IdlerGear to integrate with external tools while
maintaining its core value proposition: structured, backend-agnostic knowledge.

Plugin Types:
- Observability: Export logs/metrics (Langfuse, Helicone)
- Memory: Experiential learning (Mem0)
"""

from .base import IdlerGearPlugin, PluginCapability, PluginRegistry
from .langfuse import LangfusePlugin
from .mem0 import Mem0Plugin

__all__ = [
    "IdlerGearPlugin",
    "PluginCapability",
    "PluginRegistry",
    "LangfusePlugin",
    "Mem0Plugin",
]

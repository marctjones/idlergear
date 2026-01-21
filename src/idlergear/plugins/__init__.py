"""Plugin system for IdlerGear integrations.

The plugin system allows IdlerGear to integrate with external tools while
maintaining its core value proposition: structured, backend-agnostic knowledge.

Plugin Types:
- Observability: Export logs/metrics (Langfuse, Helicone)
- Vector Search: Semantic retrieval (LlamaIndex)
- Memory: Experiential learning (Mem0)
- Storage: Vector databases (Milvus, Qdrant)
"""

from .base import IdlerGearPlugin, PluginCapability, PluginRegistry
from .langfuse import LangfusePlugin
from .llamaindex import LlamaIndexPlugin
from .mem0 import Mem0Plugin

__all__ = [
    "IdlerGearPlugin",
    "PluginCapability",
    "PluginRegistry",
    "LangfusePlugin",
    "LlamaIndexPlugin",
    "Mem0Plugin",
]

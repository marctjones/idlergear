"""Backend abstraction for IdlerGear.

This module provides the backend protocol interfaces and factory functions
for creating backends based on configuration.
"""

from idlergear.backends.protocols import (
    ExploreBackend,
    NoteBackend,
    PlanBackend,
    ReferenceBackend,
    TaskBackend,
    VisionBackend,
)
from idlergear.backends.registry import (
    clear_backend_cache,
    get_backend,
    get_configured_backend_name,
    list_available_backends,
    register_backend,
)

__all__ = [
    "TaskBackend",
    "NoteBackend",
    "ExploreBackend",
    "PlanBackend",
    "ReferenceBackend",
    "VisionBackend",
    "get_backend",
    "register_backend",
    "clear_backend_cache",
    "get_configured_backend_name",
    "list_available_backends",
]

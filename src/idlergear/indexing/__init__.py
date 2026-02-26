"""Opportunistic background indexing for IdlerGear.

Automatically indexes files and populates knowledge graph during idle time.
"""

from .background import (
    get_indexing_status,
    index_next_batch,
    should_run_indexing,
    pause_indexing,
    resume_indexing,
)

__all__ = [
    "get_indexing_status",
    "index_next_batch",
    "should_run_indexing",
    "pause_indexing",
    "resume_indexing",
]

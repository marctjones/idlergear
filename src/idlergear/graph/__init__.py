"""Knowledge graph module for IdlerGear.

Provides token-efficient context retrieval through Kuzu graph database.

Example:
    >>> from idlergear.graph import get_database, query_task_context
    >>> db = get_database()
    >>> context = query_task_context(db, task_id=278)
    >>> print(context)  # Token-efficient task context
"""

from .database import get_database, GraphDatabase
from .schema import initialize_schema
from .queries import (
    query_task_context,
    query_file_context,
    query_recent_changes,
    query_related_files,
)

__all__ = [
    "get_database",
    "GraphDatabase",
    "initialize_schema",
    "query_task_context",
    "query_file_context",
    "query_recent_changes",
    "query_related_files",
]

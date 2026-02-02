"""Vector-based semantic code search.

Provides semantic code search capabilities using vector embeddings,
enabling natural language queries to find relevant code.
"""

from .code_index import VectorCodeIndex

__all__ = ["VectorCodeIndex"]

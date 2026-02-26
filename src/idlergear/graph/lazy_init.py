"""Lazy initialization for knowledge graph population.

Automatically populates graph on first query if empty.
"""

from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .database import GraphDatabase

_graph_initialized = False


def ensure_graph_populated(
    db: Optional["GraphDatabase"] = None,
    project_path: Optional[Path] = None,
    max_commits: int = 100,
    verbose: bool = False,
) -> bool:
    """Populate graph on first query if empty.

    Checks if graph has minimal data. If not, runs populate_all once.
    Uses global flag to avoid repeated checks.

    Args:
        db: Optional database instance (if not provided, gets default database)
        project_path: Path to project (defaults to current directory)
        max_commits: Maximum commits to index (default: 100)
        verbose: Print progress messages (default: False)

    Returns:
        True if graph was populated, False if already populated or error

    Example:
        >>> from idlergear.graph.lazy_init import ensure_graph_populated
        >>> ensure_graph_populated()  # Populates if empty
        >>> ensure_graph_populated()  # No-op on subsequent calls
    """
    global _graph_initialized

    if _graph_initialized:
        return False

    # If db is provided, we're in a test or explicit context - skip lazy init
    if db is not None:
        return False

    from .database import get_database

    # Check if graph has data
    db = get_database(project_path=project_path)
    conn = db.get_connection()

    try:
        result = conn.execute("MATCH (n) RETURN count(n) as count")
        count = result.get_next()[0] if result.has_next() else 0

        if count < 10:  # Graph is empty/minimal
            if verbose:
                print("📊 Knowledge graph empty, populating (one-time)...")

            # NOTE: This will still hit lock issue if called from MCP server
            # since get_database() above already acquired the lock.
            # Full solution requires MCP server to release lock before calling this.
            # For CLI usage, this works fine.
            from .populate_all import populate_all

            try:
                populate_all(
                    project_path=project_path,
                    max_commits=max_commits,
                    incremental=True,
                    verbose=verbose,
                )
                if verbose:
                    print("✅ Graph populated")
                _graph_initialized = True
                return True
            except Exception as e:
                if verbose:
                    print(f"⚠️ Graph populate failed: {e}")
                    print("   Use idlergear_graph_populate_all() when possible")
                _graph_initialized = True  # Don't retry on error
                return False

        _graph_initialized = True
        return False
    except Exception as e:
        if verbose:
            print(f"⚠️ Could not check graph status: {e}")
        _graph_initialized = True  # Don't retry on error
        return False


def reset_initialization_flag():
    """Reset initialization flag (for testing).

    Allows ensure_graph_populated() to run again.
    """
    global _graph_initialized
    _graph_initialized = False

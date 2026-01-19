"""Kuzu graph database connection management."""

from pathlib import Path
from typing import Optional

try:
    import kuzu
except ImportError:
    kuzu = None  # Handle gracefully if not installed


class GraphDatabase:
    """Manages connection to Kuzu graph database.

    The database is stored at ~/.idlergear/graph.db and contains:
    - Tasks, Files, Commits, Symbols (nodes)
    - Relationships between them (edges)

    Example:
        >>> db = GraphDatabase()
        >>> conn = db.get_connection()
        >>> result = conn.execute("MATCH (t:Task) RETURN t LIMIT 5")
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize graph database connection.

        Args:
            db_path: Path to database directory. Defaults to ~/.idlergear/graph.db
        """
        if kuzu is None:
            raise ImportError(
                "Kuzu is not installed. Install with: pip install kuzu>=0.11.3"
            )

        # Default path: ~/.idlergear/graph.db
        if db_path is None:
            db_path = Path.home() / ".idlergear" / "graph.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create database
        self.db = kuzu.Database(str(self.db_path))
        self.conn = kuzu.Connection(self.db)

    def get_connection(self) -> "kuzu.Connection":
        """Get database connection.

        Returns:
            Active Kuzu connection
        """
        return self.conn

    def execute(self, query: str, parameters: Optional[dict] = None) -> "kuzu.QueryResult":
        """Execute a Cypher query.

        Args:
            query: Cypher query string
            parameters: Optional query parameters

        Returns:
            Query result object

        Example:
            >>> result = db.execute("MATCH (t:Task {id: $id}) RETURN t", {"id": 278})
        """
        # TODO: Add parameter support when Kuzu supports it
        return self.conn.execute(query)

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Global database instance (lazy-loaded)
_db_instance: Optional[GraphDatabase] = None


def get_database(db_path: Optional[Path] = None) -> GraphDatabase:
    """Get or create global database instance.

    Args:
        db_path: Optional custom database path

    Returns:
        GraphDatabase instance

    Example:
        >>> db = get_database()
        >>> conn = db.get_connection()
    """
    global _db_instance

    if _db_instance is None:
        _db_instance = GraphDatabase(db_path)

    return _db_instance


def reset_database():
    """Reset global database instance (for testing)."""
    global _db_instance
    if _db_instance is not None:
        _db_instance.close()
        _db_instance = None

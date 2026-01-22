"""Kuzu graph schema initialization.

Defines node types and relationships for IdlerGear knowledge graph.
Based on research from docs/research/knowledge-graph-schema.md
"""

from pathlib import Path
from typing import Optional

from .database import GraphDatabase


def initialize_schema(db: GraphDatabase, drop_existing: bool = False) -> None:
    """Initialize graph schema (node and relationship tables).

    Args:
        db: Graph database instance
        drop_existing: If True, drop existing tables first (WARNING: deletes data!)

    Example:
        >>> from idlergear.graph import get_database, initialize_schema
        >>> db = get_database()
        >>> initialize_schema(db)
    """
    conn = db.get_connection()

    if drop_existing:
        _drop_tables(conn)

    _create_node_tables(conn)
    _create_relationship_tables(conn)


def _drop_tables(conn):
    """Drop all existing tables (for clean rebuild)."""
    # Drop relationships first (due to dependencies)
    rel_tables = [
        "DEPENDS_ON",
        "BLOCKS",
        "PROMOTED_TO_TASK",
        "PROMOTED_TO_REFERENCE",
        "PART_OF_PLAN",
        "MODIFIES",
        "CONTAINS",
        "IMPORTS",
        "CALLS",
        "IMPLEMENTED_IN",
        "CHANGES",
        "ON_BRANCH",
        "PARENT_OF",
        "DOCUMENTS",
        "DOCUMENTS_FILE",
        "DOC_DOCUMENTS_FILE",
        "DOC_DOCUMENTS_SYMBOL",
        "DOC_REFERENCES_TASK",
        "RELATED_TO",
    ]

    # Then drop nodes
    node_tables = [
        "Task",
        "Note",
        "Reference",
        "Plan",
        "File",
        "Symbol",
        "Commit",
        "Branch",
        "Documentation",
    ]

    for table in rel_tables + node_tables:
        try:
            conn.execute(f"DROP TABLE {table}")
        except Exception:
            pass  # Table doesn't exist


def _create_node_tables(conn):
    """Create all node tables."""

    # Task nodes
    conn.execute("""
        CREATE NODE TABLE Task(
            id INT64 PRIMARY KEY,
            title STRING,
            body STRING,
            state STRING,
            priority STRING,
            labels STRING[],
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            closed_at TIMESTAMP,
            source STRING
        )
    """)

    # Note nodes
    conn.execute("""
        CREATE NODE TABLE Note(
            id INT64 PRIMARY KEY,
            content STRING,
            tags STRING[],
            created_at TIMESTAMP,
            promoted BOOLEAN
        )
    """)

    # Reference nodes
    conn.execute("""
        CREATE NODE TABLE Reference(
            id INT64 PRIMARY KEY,
            title STRING,
            body STRING,
            tags STRING[],
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            pinned BOOLEAN
        )
    """)

    # Plan nodes
    conn.execute("""
        CREATE NODE TABLE Plan(
            id INT64 PRIMARY KEY,
            name STRING,
            title STRING,
            body STRING,
            state STRING,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)

    # File nodes
    conn.execute("""
        CREATE NODE TABLE File(
            path STRING PRIMARY KEY,
            language STRING,
            size INT64,
            lines INT32,
            last_modified TIMESTAMP,
            file_exists BOOLEAN,
            hash STRING
        )
    """)

    # Symbol nodes (functions, classes, methods)
    conn.execute("""
        CREATE NODE TABLE Symbol(
            id STRING PRIMARY KEY,
            name STRING,
            type STRING,
            file_path STRING,
            line_start INT32,
            line_end INT32,
            docstring STRING
        )
    """)

    # Commit nodes
    conn.execute("""
        CREATE NODE TABLE Commit(
            hash STRING PRIMARY KEY,
            short_hash STRING,
            message STRING,
            author STRING,
            timestamp TIMESTAMP,
            branch STRING
        )
    """)

    # Branch nodes
    conn.execute("""
        CREATE NODE TABLE Branch(
            name STRING PRIMARY KEY,
            current BOOLEAN,
            head_commit STRING,
            created_at TIMESTAMP
        )
    """)

    # Documentation nodes (wiki, references, README, docstrings)
    conn.execute("""
        CREATE NODE TABLE Documentation(
            path STRING PRIMARY KEY,
            title STRING,
            body STRING,
            source STRING,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)


def _create_relationship_tables(conn):
    """Create all relationship tables."""

    # Task relationships
    conn.execute("""
        CREATE REL TABLE DEPENDS_ON(
            FROM Task TO Task,
            created_at TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE REL TABLE BLOCKS(
            FROM Task TO Task,
            reason STRING
        )
    """)

    conn.execute("""
        CREATE REL TABLE PROMOTED_TO_TASK(
            FROM Note TO Task,
            promoted_at TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE REL TABLE PROMOTED_TO_REFERENCE(
            FROM Note TO Reference,
            promoted_at TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE REL TABLE PART_OF_PLAN(
            FROM Task TO Plan,
            task_order INT32
        )
    """)

    # Code relationships
    conn.execute("""
        CREATE REL TABLE MODIFIES(
            FROM Task TO File,
            change_type STRING
        )
    """)

    conn.execute("""
        CREATE REL TABLE CONTAINS(
            FROM File TO Symbol
        )
    """)

    conn.execute("""
        CREATE REL TABLE IMPORTS(
            FROM File TO File,
            import_type STRING,
            line INT32
        )
    """)

    conn.execute("""
        CREATE REL TABLE CALLS(
            FROM Symbol TO Symbol,
            call_count INT32
        )
    """)

    # Git relationships
    conn.execute("""
        CREATE REL TABLE IMPLEMENTED_IN(
            FROM Task TO Commit
        )
    """)

    conn.execute("""
        CREATE REL TABLE CHANGES(
            FROM Commit TO File,
            insertions INT32,
            deletions INT32,
            status STRING
        )
    """)

    conn.execute("""
        CREATE REL TABLE ON_BRANCH(
            FROM Commit TO Branch
        )
    """)

    conn.execute("""
        CREATE REL TABLE PARENT_OF(
            FROM Commit TO Commit
        )
    """)

    # Documentation relationships
    conn.execute("""
        CREATE REL TABLE DOCUMENTS(
            FROM Reference TO Symbol
        )
    """)

    conn.execute("""
        CREATE REL TABLE DOCUMENTS_FILE(
            FROM Reference TO File
        )
    """)

    # Documentation relationships (wiki, references)
    conn.execute("""
        CREATE REL TABLE DOC_DOCUMENTS_FILE(
            FROM Documentation TO File
        )
    """)

    conn.execute("""
        CREATE REL TABLE DOC_DOCUMENTS_SYMBOL(
            FROM Documentation TO Symbol
        )
    """)

    conn.execute("""
        CREATE REL TABLE DOC_REFERENCES_TASK(
            FROM Documentation TO Task
        )
    """)

    # Generic relationship
    conn.execute("""
        CREATE REL TABLE RELATED_TO(
            FROM Task TO File,
            FROM Note TO File,
            FROM Reference TO Task,
            relationship_type STRING
        )
    """)


def get_schema_info(db: GraphDatabase) -> dict:
    """Get information about current schema.

    Returns:
        Dictionary with node types, relationship types, counts

    Example:
        >>> info = get_schema_info(db)
        >>> print(f"Node types: {info['node_types']}")
    """
    conn = db.get_connection()

    # Get node counts
    node_counts = {}
    for table in ["Task", "File", "Commit", "Symbol", "Note", "Reference", "Plan", "Branch"]:
        try:
            result = conn.execute(f"MATCH (n:{table}) RETURN COUNT(n) AS count")
            count = result.get_next()[0] if result.has_next() else 0
            node_counts[table] = count
        except Exception:
            node_counts[table] = 0

    # Get relationship counts
    rel_counts = {}
    for table in ["MODIFIES", "IMPORTS", "CHANGES", "IMPLEMENTED_IN", "CONTAINS"]:
        try:
            result = conn.execute(f"MATCH ()-[r:{table}]->() RETURN COUNT(r) AS count")
            count = result.get_next()[0] if result.has_next() else 0
            rel_counts[table] = count
        except Exception:
            rel_counts[table] = 0

    return {
        "node_types": list(node_counts.keys()),
        "relationship_types": list(rel_counts.keys()),
        "node_counts": node_counts,
        "relationship_counts": rel_counts,
        "total_nodes": sum(node_counts.values()),
        "total_relationships": sum(rel_counts.values()),
    }

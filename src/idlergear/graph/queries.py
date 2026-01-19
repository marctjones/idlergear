"""Common query patterns for IdlerGear knowledge graph.

Provides token-efficient queries for context retrieval.
"""

from typing import Any, Optional, List, Dict

from .database import GraphDatabase


def query_task_context(db: GraphDatabase, task_id: int) -> Dict[str, Any]:
    """Get token-efficient context for a task.

    Returns task info with related files, commits, and symbols.

    Args:
        db: Graph database instance
        task_id: Task ID

    Returns:
        Dictionary with task context

    Example:
        >>> context = query_task_context(db, 278)
        >>> print(context['title'])
        >>> print(context['files'])
    """
    conn = db.get_connection()

    # Get full task context (multi-hop query)
    result = conn.execute(f"""
        MATCH (t:Task {{id: {task_id}}})
        OPTIONAL MATCH (t)-[:MODIFIES]->(f:File)
        OPTIONAL MATCH (t)-[:IMPLEMENTED_IN]->(c:Commit)
        OPTIONAL MATCH (f)-[:CONTAINS]->(s:Symbol)
        RETURN t.title AS title,
               t.state AS state,
               COLLECT(DISTINCT f.path) AS files,
               COLLECT(DISTINCT c.short_hash) AS commits,
               COLLECT(DISTINCT s.name) AS symbols
    """)

    if not result.has_next():
        return {}

    row = result.get_next()
    return {
        "task_id": task_id,
        "title": row[0],
        "state": row[1],
        "files": row[2] if row[2] else [],
        "commits": row[3] if row[3] else [],
        "symbols": row[4] if row[4] else [],
    }


def query_file_context(db: GraphDatabase, file_path: str) -> Dict[str, Any]:
    """Get token-efficient context for a file.

    Returns file info with related tasks, imports, and symbols.

    Args:
        db: Graph database instance
        file_path: Relative file path

    Returns:
        Dictionary with file context
    """
    conn = db.get_connection()

    # Get file context
    result = conn.execute(f"""
        MATCH (f:File {{path: '{file_path}'}})
        OPTIONAL MATCH (t:Task)-[:MODIFIES]->(f)
        OPTIONAL MATCH (f)-[:IMPORTS]->(imported:File)
        OPTIONAL MATCH (f)-[:CONTAINS]->(s:Symbol)
        RETURN f.language AS language,
               f.lines AS lines,
               COLLECT(DISTINCT t.id) AS tasks,
               COLLECT(DISTINCT imported.path) AS imports,
               COLLECT(DISTINCT s.name) AS symbols
    """)

    if not result.has_next():
        return {}

    row = result.get_next()
    return {
        "file_path": file_path,
        "language": row[0],
        "lines": row[1],
        "tasks": row[2] if row[2] else [],
        "imports": row[3] if row[3] else [],
        "symbols": row[4] if row[4] else [],
    }


def query_recent_changes(db: GraphDatabase, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent commits and changed files.

    Args:
        db: Graph database instance
        limit: Max number of commits to return

    Returns:
        List of commit dictionaries

    Example:
        >>> changes = query_recent_changes(db, limit=5)
        >>> for change in changes:
        >>>     print(f"{change['hash']}: {change['message']}")
    """
    conn = db.get_connection()

    # First get recent commits
    result = conn.execute(f"""
        MATCH (c:Commit)
        RETURN c.short_hash AS hash,
               c.message AS message,
               c.timestamp AS timestamp,
               c.hash AS commit_hash
        ORDER BY c.timestamp DESC
        LIMIT {limit}
    """)

    changes = []
    while result.has_next():
        row = result.get_next()
        commit_hash = row[3]

        # Get files for this commit
        files_result = conn.execute(f"""
            MATCH (c:Commit {{hash: '{commit_hash}'}})-[:CHANGES]->(f:File)
            RETURN f.path
        """)

        files = []
        while files_result.has_next():
            files.append(files_result.get_next()[0])

        changes.append({
            "hash": row[0],
            "message": row[1],
            "timestamp": row[2],
            "files": files,
        })

    return changes


def query_related_files(db: GraphDatabase, file_path: str, max_hops: int = 2) -> List[str]:
    """Find files related to a given file (via imports).

    Args:
        db: Graph database instance
        file_path: Source file path
        max_hops: Max relationship hops (default: 2)

    Returns:
        List of related file paths

    Example:
        >>> related = query_related_files(db, "src/idlergear/cli.py")
        >>> print(related)  # ['src/idlergear/tasks.py', 'src/idlergear/backends/...']
    """
    conn = db.get_connection()

    # Find files within N hops via IMPORTS
    result = conn.execute(f"""
        MATCH (f1:File {{path: '{file_path}'}})-[:IMPORTS*1..{max_hops}]->(f2:File)
        RETURN DISTINCT f2.path AS path
    """)

    related = []
    while result.has_next():
        row = result.get_next()
        related.append(row[0])

    return related


def query_symbols_by_name(db: GraphDatabase, name_pattern: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search symbols by name pattern.

    Args:
        db: Graph database instance
        name_pattern: Symbol name pattern (case-insensitive contains)
        limit: Max results

    Returns:
        List of symbol dictionaries

    Example:
        >>> symbols = query_symbols_by_name(db, "milestone")
        >>> for sym in symbols:
        >>>     print(f"{sym['name']} in {sym['file']} at line {sym['line']}")
    """
    conn = db.get_connection()

    # Case-insensitive search
    result = conn.execute(f"""
        MATCH (s:Symbol)
        WHERE toLower(s.name) CONTAINS toLower('{name_pattern}')
        RETURN s.name AS name,
               s.type AS type,
               s.file_path AS file,
               s.line_start AS line
        LIMIT {limit}
    """)

    symbols = []
    while result.has_next():
        row = result.get_next()
        symbols.append({
            "name": row[0],
            "type": row[1],
            "file": row[2],
            "line": row[3],
        })

    return symbols

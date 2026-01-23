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


# ============================================================================
# Advanced Query Functions (Issue #335)
# ============================================================================


def query_impact_analysis(db: GraphDatabase, symbol_name: str) -> Dict[str, Any]:
    """Analyze what would be affected if a symbol breaks or changes.

    Returns all files, symbols, and tasks that depend on this symbol.

    Args:
        db: Graph database instance
        symbol_name: Name of symbol to analyze

    Returns:
        Dictionary with impact analysis

    Example:
        >>> impact = query_impact_analysis(db, "process_task")
        >>> print(f"Would affect {len(impact['files'])} files")
    """
    conn = db.get_connection()

    # Find the symbol(s) and trace their impact
    result = conn.execute(f"""
        MATCH (s:Symbol {{name: '{symbol_name}'}})
        OPTIONAL MATCH (f:File)-[:CONTAINS]->(s)
        OPTIONAL MATCH (caller:Symbol)-[:CALLS]->(s)
        OPTIONAL MATCH (caller_file:File)-[:CONTAINS]->(caller)
        OPTIONAL MATCH (t:Task)-[:MODIFIES]->(f)
        RETURN DISTINCT
            s.file_path AS symbol_file,
            s.type AS symbol_type,
            COLLECT(DISTINCT caller.name) AS callers,
            COLLECT(DISTINCT caller_file.path) AS affected_files,
            COLLECT(DISTINCT t.id) AS related_tasks
    """)

    if not result.has_next():
        return {"symbol": symbol_name, "found": False}

    row = result.get_next()
    return {
        "symbol": symbol_name,
        "found": True,
        "defined_in": row[0],
        "type": row[1],
        "callers": [c for c in row[2] if c] if row[2] else [],
        "affected_files": [f for f in row[3] if f] if row[3] else [],
        "related_tasks": [t for t in row[4] if t is not None] if row[4] else [],
    }


def query_test_coverage(db: GraphDatabase, target: str, target_type: str = "file") -> Dict[str, Any]:
    """Find test files that cover a given file or symbol.

    Args:
        db: Graph database instance
        target: File path or symbol name
        target_type: "file" or "symbol"

    Returns:
        Dictionary with test coverage info

    Example:
        >>> coverage = query_test_coverage(db, "src/idlergear/tasks.py", "file")
        >>> print(f"Covered by {len(coverage['test_files'])} tests")
    """
    conn = db.get_connection()

    if target_type == "file":
        # Find test files that import or reference this file
        result = conn.execute(f"""
            MATCH (f:File {{path: '{target}'}})
            OPTIONAL MATCH (test:File)-[:IMPORTS]->(f)
            WHERE test.path CONTAINS 'test_' OR test.path CONTAINS '/tests/'
            OPTIONAL MATCH (test)-[:CONTAINS]->(test_sym:Symbol)
            WHERE test_sym.type = 'function' AND toLower(test_sym.name) CONTAINS 'test'
            RETURN DISTINCT
                COLLECT(DISTINCT test.path) AS test_files,
                COLLECT(DISTINCT test_sym.name) AS test_functions
        """)
    else:  # symbol
        # Find test symbols that might reference this symbol
        result = conn.execute(f"""
            MATCH (s:Symbol {{name: '{target}'}})
            OPTIONAL MATCH (test_sym:Symbol)-[:CALLS]->(s)
            WHERE toLower(test_sym.name) CONTAINS 'test'
            OPTIONAL MATCH (test_file:File)-[:CONTAINS]->(test_sym)
            RETURN DISTINCT
                COLLECT(DISTINCT test_file.path) AS test_files,
                COLLECT(DISTINCT test_sym.name) AS test_functions
        """)

    if not result.has_next():
        return {"target": target, "type": target_type, "test_files": [], "test_functions": []}

    row = result.get_next()
    return {
        "target": target,
        "type": target_type,
        "test_files": [f for f in row[0] if f] if row[0] else [],
        "test_functions": [f for f in row[1] if f] if row[1] else [],
    }


def query_change_history(db: GraphDatabase, symbol_name: str) -> List[Dict[str, Any]]:
    """Get all commits that touched a specific symbol.

    Traces symbol across file changes and renames.

    Args:
        db: Graph database instance
        symbol_name: Name of symbol

    Returns:
        List of commits affecting this symbol

    Example:
        >>> history = query_change_history(db, "parse_config")
        >>> for commit in history:
        >>>     print(f"{commit['hash']}: {commit['message']}")
    """
    conn = db.get_connection()

    # Find commits that changed files containing this symbol
    result = conn.execute(f"""
        MATCH (s:Symbol {{name: '{symbol_name}'}})
        MATCH (f:File)-[:CONTAINS]->(s)
        MATCH (c:Commit)-[:CHANGES]->(f)
        RETURN DISTINCT
            c.short_hash AS hash,
            c.message AS message,
            c.timestamp AS timestamp,
            c.author_name AS author,
            f.path AS file_path
        ORDER BY c.timestamp DESC
    """)

    history = []
    while result.has_next():
        row = result.get_next()
        history.append({
            "hash": row[0],
            "message": row[1],
            "timestamp": row[2],
            "author": row[3],
            "file": row[4],
        })

    return history


def query_dependency_chain(db: GraphDatabase, file_path: str, max_depth: int = 5) -> Dict[str, Any]:
    """Find transitive dependency chain for a file.

    Returns all files this file depends on (recursively via imports).

    Args:
        db: Graph database instance
        file_path: Source file path
        max_depth: Maximum depth to traverse

    Returns:
        Dictionary with dependency tree

    Example:
        >>> deps = query_dependency_chain(db, "src/idlergear/mcp_server.py")
        >>> print(f"Depends on {len(deps['dependencies'])} files")
    """
    conn = db.get_connection()

    # Get transitive dependencies via IMPORTS
    result = conn.execute(f"""
        MATCH path = (f:File {{path: '{file_path}'}})-[:IMPORTS*1..{max_depth}]->(dep:File)
        WITH dep, MIN(length(path)) AS depth
        RETURN DISTINCT
            dep.path AS file,
            depth AS distance
        ORDER BY distance ASC
    """)

    dependencies = []
    while result.has_next():
        row = result.get_next()
        dependencies.append({
            "file": row[0],
            "distance": row[1],
        })

    return {
        "source_file": file_path,
        "total_dependencies": len(dependencies),
        "dependencies": dependencies,
    }


def query_orphan_detection(db: GraphDatabase) -> Dict[str, Any]:
    """Find orphaned/unused code - functions with no callers, files with no imports.

    Args:
        db: Graph database instance

    Returns:
        Dictionary with orphan analysis

    Example:
        >>> orphans = query_orphan_detection(db)
        >>> print(f"Found {len(orphans['unused_symbols'])} unused symbols")
    """
    conn = db.get_connection()

    # Find symbols with no callers
    unused_symbols_result = conn.execute("""
        MATCH (s:Symbol)
        WHERE NOT exists((s)<-[:CALLS]-())
        AND s.type IN ['function', 'method']
        AND NOT toLower(s.name) CONTAINS 'test'
        AND NOT toLower(s.name) STARTS WITH '_'
        RETURN s.name AS name,
               s.file_path AS file,
               s.line_start AS line,
               s.type AS type
        LIMIT 100
    """)

    unused_symbols = []
    while unused_symbols_result.has_next():
        row = unused_symbols_result.get_next()
        unused_symbols.append({
            "name": row[0],
            "file": row[1],
            "line": row[2],
            "type": row[3],
        })

    # Find files with no incoming imports (excluding entry points)
    unreferenced_files_result = conn.execute("""
        MATCH (f:File)
        WHERE NOT exists((f)<-[:IMPORTS]-())
        AND NOT f.path CONTAINS '__main__'
        AND NOT f.path CONTAINS 'test_'
        AND NOT f.path ENDS WITH '.md'
        RETURN f.path AS file,
               f.lines AS lines
        LIMIT 100
    """)

    unreferenced_files = []
    while unreferenced_files_result.has_next():
        row = unreferenced_files_result.get_next()
        unreferenced_files.append({
            "file": row[0],
            "lines": row[1],
        })

    return {
        "unused_symbols": unused_symbols,
        "unused_symbol_count": len(unused_symbols),
        "unreferenced_files": unreferenced_files,
        "unreferenced_file_count": len(unreferenced_files),
    }


def query_symbol_callers(db: GraphDatabase, symbol_name: str) -> Dict[str, Any]:
    """Find all symbols that call a given symbol (reverse lookup).

    Args:
        db: Graph database instance
        symbol_name: Symbol to find callers for

    Returns:
        Dictionary with caller information

    Example:
        >>> callers = query_symbol_callers(db, "get_config_value")
        >>> for caller in callers['callers']:
        >>>     print(f"{caller['name']} in {caller['file']}")
    """
    conn = db.get_connection()

    # Find callers via CALLS relationship
    result = conn.execute(f"""
        MATCH (target:Symbol {{name: '{symbol_name}'}})
        OPTIONAL MATCH (caller:Symbol)-[:CALLS]->(target)
        OPTIONAL MATCH (f:File)-[:CONTAINS]->(caller)
        RETURN DISTINCT
            caller.name AS caller_name,
            caller.type AS caller_type,
            f.path AS file,
            caller.line_start AS line
        ORDER BY file, line
    """)

    callers = []
    while result.has_next():
        row = result.get_next()
        if row[0]:  # Only add if caller exists
            callers.append({
                "name": row[0],
                "type": row[1],
                "file": row[2],
                "line": row[3],
            })

    return {
        "symbol": symbol_name,
        "caller_count": len(callers),
        "callers": callers,
    }


def query_file_timeline(db: GraphDatabase, file_path: str, limit: int = 20) -> Dict[str, Any]:
    """Get evolution of a file over time via commits.

    Args:
        db: Graph database instance
        file_path: File to trace
        limit: Max commits to return

    Returns:
        Dictionary with file timeline

    Example:
        >>> timeline = query_file_timeline(db, "src/idlergear/tasks.py")
        >>> for event in timeline['commits']:
        >>>     print(f"{event['date']}: {event['message']}")
    """
    conn = db.get_connection()

    # Get commits affecting this file
    result = conn.execute(f"""
        MATCH (f:File {{path: '{file_path}'}})
        MATCH (c:Commit)-[:CHANGES]->(f)
        RETURN
            c.short_hash AS hash,
            c.message AS message,
            c.timestamp AS timestamp,
            c.author_name AS author
        ORDER BY c.timestamp DESC
        LIMIT {limit}
    """)

    commits = []
    while result.has_next():
        row = result.get_next()
        commits.append({
            "hash": row[0],
            "message": row[1],
            "timestamp": row[2],
            "author": row[3],
        })

    return {
        "file": file_path,
        "commit_count": len(commits),
        "commits": commits,
    }


def query_task_coverage(db: GraphDatabase) -> Dict[str, Any]:
    """Find tasks with no associated commits (not yet implemented).

    Args:
        db: Graph database instance

    Returns:
        Dictionary with task coverage analysis

    Example:
        >>> coverage = query_task_coverage(db)
        >>> print(f"{len(coverage['tasks_without_commits'])} tasks have no commits")
    """
    conn = db.get_connection()

    # Find tasks with no commits
    result = conn.execute("""
        MATCH (t:Task)
        WHERE NOT exists((c:Commit)-[:MODIFIES]->(t))
        RETURN
            t.id AS id,
            t.title AS title,
            t.state AS state,
            t.priority AS priority
        ORDER BY t.priority DESC, t.id DESC
        LIMIT 100
    """)

    tasks_without_commits = []
    while result.has_next():
        row = result.get_next()
        tasks_without_commits.append({
            "id": row[0],
            "title": row[1],
            "state": row[2],
            "priority": row[3],
        })

    # Find tasks WITH commits for comparison
    with_commits_result = conn.execute("""
        MATCH (t:Task)
        WHERE exists((c:Commit)-[:MODIFIES]->(t))
        RETURN COUNT(t) AS count
    """)

    with_commits_count = 0
    if with_commits_result.has_next():
        with_commits_count = with_commits_result.get_next()[0]

    return {
        "tasks_without_commits": tasks_without_commits,
        "tasks_without_commits_count": len(tasks_without_commits),
        "tasks_with_commits_count": with_commits_count,
        "coverage_percentage": (
            (with_commits_count / (with_commits_count + len(tasks_without_commits))) * 100
            if (with_commits_count + len(tasks_without_commits)) > 0
            else 0
        ),
    }

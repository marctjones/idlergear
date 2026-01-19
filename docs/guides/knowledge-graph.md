# Knowledge Graph User Guide

The IdlerGear knowledge graph provides **token-efficient context retrieval** by indexing your codebase structure and git history. Instead of reading entire files or running expensive grep commands, you can query the graph database for precise information.

## What It Does

The knowledge graph indexes:
- **Git commits**: Hash, message, author, timestamp, changed files
- **Files**: Path, language, size, lines, symbols
- **Code symbols**: Functions, classes, methods with their locations and docstrings
- **Relationships**: Which commits changed which files, which files contain which symbols

## Token Efficiency

**Example: Finding a function**

Traditional approach:
```bash
# grep across entire codebase
grep -r "milestone" src/  # Returns ~500 tokens of output
# Read 3 files to find the right one
cat src/file1.py src/file2.py src/file3.py  # ~7000 tokens
# Total: ~7500 tokens
```

Knowledge graph approach:
```python
# Query for symbol by name
idlergear_graph_query_symbols(pattern="milestone", limit=10)
# Returns just the locations: ~100 tokens
# Savings: 98.7%
```

## Setup (First Time)

### 1. Initialize the Graph

The graph database is automatically created at `~/.idlergear/graph.db`. No manual setup required.

### 2. Populate Git History

```python
# From Python or via MCP
idlergear_graph_populate_git(
    max_commits=100,      # Index last 100 commits
    incremental=True      # Skip already-indexed commits
)
```

This creates:
- Commit nodes with metadata
- File nodes with change stats
- CHANGES relationships

**Time**: ~5-10 seconds for 100 commits

### 3. Populate Code Symbols

```python
# From Python or via MCP
idlergear_graph_populate_code(
    directory="src",      # Scan src/ directory
    incremental=True      # Skip unchanged files
)
```

This creates:
- Symbol nodes (functions, classes, methods)
- File nodes if not already created
- CONTAINS relationships (File → Symbol)

**Time**: ~10-20 seconds for 1000 Python files

### 4. Verify

```python
# Check what was indexed
idlergear_graph_schema_info()
```

Returns:
```json
{
  "node_types": ["Task", "File", "Commit", "Symbol", ...],
  "relationship_types": ["MODIFIES", "CONTAINS", "CHANGES", ...],
  "node_counts": {
    "Commit": 100,
    "File": 450,
    "Symbol": 1823
  },
  "relationship_counts": {
    "CHANGES": 687,
    "CONTAINS": 1823
  },
  "total_nodes": 2373,
  "total_relationships": 2510
}
```

## Querying the Graph

### Query Task Context

Get all information related to a task:

```python
idlergear_graph_query_task(task_id=278)
```

Returns:
```json
{
  "task_id": 278,
  "title": "Implement knowledge graph",
  "state": "open",
  "files": [
    "src/idlergear/graph/database.py",
    "src/idlergear/graph/schema.py",
    "src/idlergear/graph/queries.py"
  ],
  "commits": ["a3f5c12", "b7e9d44"],
  "symbols": ["GraphDatabase", "initialize_schema", "query_task_context"]
}
```

**Use case**: "What files and symbols are related to task #278?"

### Query File Context

Get information about a specific file:

```python
idlergear_graph_query_file(file_path="src/idlergear/graph/database.py")
```

Returns:
```json
{
  "file_path": "src/idlergear/graph/database.py",
  "language": "python",
  "lines": 115,
  "tasks": [278, 279],
  "imports": [
    "src/idlergear/graph/schema.py"
  ],
  "symbols": [
    "GraphDatabase",
    "GraphDatabase.__init__",
    "GraphDatabase.get_connection",
    "GraphDatabase.execute",
    "get_database"
  ]
}
```

**Use case**: "What symbols are in this file? What tasks touched it?"

### Search for Symbols

Find functions, classes, or methods by name:

```python
idlergear_graph_query_symbols(
    pattern="milestone",  # Case-insensitive substring match
    limit=10              # Max results
)
```

Returns:
```json
{
  "symbols": [
    {
      "name": "create_milestone",
      "type": "function",
      "file": "src/projects/milestones.py",
      "line": 45
    },
    {
      "name": "Milestone",
      "type": "class",
      "file": "src/models/milestone.py",
      "line": 12
    },
    {
      "name": "Milestone.validate",
      "type": "method",
      "file": "src/models/milestone.py",
      "line": 28
    }
  ],
  "count": 3
}
```

**Use case**: "Where is the milestone function defined?"

## Incremental Updates

The graph supports incremental updates to avoid re-indexing unchanged data.

### Update Git History

```python
# Only index new commits
idlergear_graph_populate_git(
    max_commits=50,
    incremental=True  # Skip commits already in DB
)
```

The populator:
1. Queries existing commits in database
2. Skips commits that are already indexed
3. Only processes new commits

### Update Code Symbols

```python
# Only re-index changed files
idlergear_graph_populate_code(
    directory="src",
    incremental=True  # Skip files with same hash
)
```

The populator:
1. Compares file hash in DB with current file hash
2. Skips files that haven't changed
3. Only processes modified or new files

## Best Practices

### When to Populate

**Git history**: After significant development sessions
```python
# After 20+ commits
idlergear_graph_populate_git(max_commits=50)
```

**Code symbols**: After refactoring or adding new modules
```python
# After adding new files or major changes
idlergear_graph_populate_code(directory="src")
```

### Query Patterns

**Instead of grep**:
```python
# Bad: grep -r "function_name"
# Good:
idlergear_graph_query_symbols(pattern="function_name")
```

**Instead of reading files**:
```python
# Bad: Read 5 files to find related code
# Good:
idlergear_graph_query_file(file_path="src/module.py")
# Returns symbols, imports, and related tasks
```

**Instead of git log**:
```python
# Bad: git log --grep="task #278"
# Good:
idlergear_graph_query_task(task_id=278)
# Returns commits, files, and symbols
```

## Performance

Based on real-world testing:

| Operation | Time | Tokens |
|-----------|------|--------|
| Populate 100 commits | ~5-10s | N/A |
| Populate 1000 files | ~10-20s | N/A |
| Query task context | <40ms | ~100 |
| Query file context | <40ms | ~150 |
| Search symbols | <40ms | ~80-200 |

**vs Traditional**:
| Operation | grep + read files | Graph query | Savings |
|-----------|-------------------|-------------|---------|
| Find function | ~7500 tokens | ~100 tokens | 98.7% |
| Task context | ~5000 tokens | ~100 tokens | 98.0% |
| File symbols | ~3000 tokens | ~150 tokens | 95.0% |

## Limitations

### Current Version

1. **Python only**: Code symbol extraction currently only supports Python
   - Future: JavaScript, TypeScript, Go, Rust
2. **No import tracking**: Import relationships not yet analyzed
   - Future: IMPORTS relationships will be populated
3. **Manual population**: No automatic hooks for git commits
   - Future: Git hooks for auto-population
4. **No task linking**: Commits don't link to tasks via commit messages yet
   - Future: Parse commit messages for "Task: #123" references

### Database

1. **Location**: Graph database is global (`~/.idlergear/graph.db`)
   - All projects share the same graph
   - File paths are relative to help differentiate
2. **Size**: Database grows with codebase size
   - ~1-5MB for small projects
   - ~50-100MB for large projects (10k+ files)
3. **Concurrency**: Single-writer (Kuzu limitation)
   - Multiple readers OK
   - Only one population process at a time

## Troubleshooting

### "Knowledge graph not initialized"

**Cause**: Schema hasn't been created yet

**Fix**:
```python
idlergear_graph_populate_git()  # Auto-creates schema
# or
idlergear_graph_populate_code()  # Auto-creates schema
```

### "Task/File not found in graph"

**Cause**: Data hasn't been populated yet

**Fix**:
```python
# For tasks/commits
idlergear_graph_populate_git(max_commits=100)

# For files/symbols
idlergear_graph_populate_code(directory="src")
```

### Stale Data

**Cause**: Graph not updated after code changes

**Fix**:
```python
# Re-populate with incremental mode
idlergear_graph_populate_git(incremental=True)
idlergear_graph_populate_code(incremental=True)
```

### Performance Issues

**Cause**: Database file locked or too large

**Fix**:
```bash
# Check database size
ls -lh ~/.idlergear/graph.db

# If too large (>500MB), consider rebuilding
rm ~/.idlergear/graph.db
# Then re-populate
```

## Python API

You can also use the graph directly from Python code:

```python
from idlergear.graph import get_database, initialize_schema
from idlergear.graph.populators import GitPopulator, CodePopulator
from idlergear.graph.queries import (
    query_task_context,
    query_file_context,
    query_symbols_by_name,
)

# Get database instance
db = get_database()

# Initialize schema (first time only)
initialize_schema(db)

# Populate
git_pop = GitPopulator(db)
git_pop.populate(max_commits=100)

code_pop = CodePopulator(db)
code_pop.populate_directory("src/")

# Query
task_ctx = query_task_context(db, task_id=278)
file_ctx = query_file_context(db, "src/main.py")
symbols = query_symbols_by_name(db, "handle_request", limit=10)
```

## Architecture

The knowledge graph uses **Kuzu embedded graph database**:
- **Embedded**: No separate server required
- **Fast**: <40ms queries for multi-hop traversals
- **Persistent**: Data stored in `~/.idlergear/graph.db`
- **Cypher**: Powerful graph query language

**Schema**:
- 8 node types: Task, Note, Reference, Plan, File, Symbol, Commit, Branch
- 16 relationship types: MODIFIES, CONTAINS, CHANGES, IMPORTS, etc.

See `docs/architecture/knowledge-graph-integration.md` for full details.

## See Also

- [Architecture Document](../architecture/knowledge-graph-integration.md)
- [Phase 1 Completion Report](../implementation/graph-phase1-complete.md)
- [Research: Kuzu vs NetworkX](../research/knowledge-graph-comparison.md)
- [Schema Design](../research/knowledge-graph-schema.md)

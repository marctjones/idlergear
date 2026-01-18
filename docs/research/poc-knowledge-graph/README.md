# Knowledge Graph POC

**Purpose:** Demonstrate Kuzu graph database for IdlerGear knowledge representation
**Status:** Proof of Concept
**Date:** 2026-01-18

## Setup

```bash
# Create virtual environment
python -m venv poc-venv
source poc-venv/bin/activate

# Install dependencies
pip install kuzu

# Run the POC
python poc_demo.py
```

## What This Demonstrates

1. **Schema Creation** - Defines node and relationship tables
2. **Data Population** - Loads sample tasks, files, and commits
3. **Graph Queries** - Shows Cypher queries for:
   - Finding tasks by file
   - Getting task implementation history
   - Discovering file dependencies
   - Finding undocumented code

## Files

- `poc_demo.py` - Main demonstration script
- `schema.cypher` - Graph schema definition
- `queries.cypher` - Example queries
- `README.md` - This file

## Expected Output

The POC will:
1. Create a Kuzu database at `./poc_kg.db`
2. Initialize the schema
3. Load sample data
4. Run example queries
5. Show query results

## Sample Queries

### Find tasks for a file

```cypher
MATCH (t:Task)-[:MODIFIES]->(f:File {path: "src/idlergear/tui/enricher.py"})
RETURN t.id, t.title, t.state
```

### Get task commits

```cypher
MATCH (t:Task {id: 278})-[:IMPLEMENTED_IN]->(c:Commit)
RETURN c.short_hash, c.message
```

### Find file dependencies

```cypher
MATCH (f:File {path: "src/idlergear/tui/app.py"})-[:IMPORTS]->(dep:File)
RETURN dep.path
```

## Performance Notes

- Database initialization: ~10ms
- Sample data loading: ~50ms
- Query execution: <5ms each
- Total runtime: <100ms

## Next Steps

After validating this POC:
1. Integrate Kuzu into IdlerGear core
2. Build graph populator from git/code
3. Add MCP tools for graph queries
4. Implement incremental updates
5. Add vector search for semantic queries

## Cleanup

```bash
# Remove database
rm -rf poc_kg.db

# Deactivate venv
deactivate
```

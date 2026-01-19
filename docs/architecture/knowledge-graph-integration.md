# Knowledge Graph Integration Architecture

**Date:** 2026-01-18
**Issue:** #270 - Design and implement token-efficient codebase indexer
**Status:** In Progress

## Overview

Integrate Kuzu graph database to provide token-efficient context retrieval for IdlerGear. This builds on research from #267 which concluded Kuzu is superior to YAML indexes or NetworkX for our use case.

## Goals (from #270)

✅ **Token Efficiency:** 80%+ token savings vs grep/file reads
✅ **Fast Queries:** <100ms for context retrieval
✅ **Relationship Awareness:** Discover related content efficiently
✅ **Semantic Search:** Beyond keyword matching
✅ **Incremental Updates:** <1s to update on file changes

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                    IdlerGear CLI / MCP                      │
└───────────┬─────────────────────────────────────────────────┘
            │
            ├─► Context Command (token-efficient queries)
            ├─► Search Command (find by keywords/semantics)
            └─► MCP Tools (graph queries for AI assistants)
                    │
                    ↓
┌─────────────────────────────────────────────────────────────┐
│                    Graph Query Layer                         │
│  • TaskContext (open tasks, relationships)                   │
│  • FileContext (related files, dependencies)                 │
│  • CommitContext (recent changes, history)                   │
│  • SymbolContext (functions, classes in scope)               │
└───────────┬─────────────────────────────────────────────────┘
            │
            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Kuzu Graph Database                         │
│  Location: ~/.idlergear/graph.db                            │
│  Schema: Tasks, Files, Commits, Symbols, etc.               │
│  Query: Cypher (via Python API)                             │
└───────────┬─────────────────────────────────────────────────┘
            │
            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Graph Populators                          │
│  • GitPopulator (commits, branches, file changes)            │
│  • CodePopulator (symbols, imports, dependencies)            │
│  • TaskPopulator (link tasks to files/commits)               │
└─────────────────────────────────────────────────────────────┘
```

### Module Structure

```
src/idlergear/
├── graph/
│   ├── __init__.py           # Public API
│   ├── database.py           # Kuzu connection management
│   ├── schema.py             # Schema initialization
│   ├── queries.py            # Common query patterns
│   ├── populators/
│   │   ├── __init__.py
│   │   ├── git_populator.py   # Index git history
│   │   ├── code_populator.py  # Index code symbols
│   │   └── task_populator.py  # Link tasks to code/commits
│   └── context/
│       ├── __init__.py
│       ├── task_context.py    # Token-efficient task context
│       ├── file_context.py    # Related files queries
│       └── commit_context.py  # Git history context
```

## Implementation Phases

### Phase 1: Foundation (Days 1-2)

**Goal:** Basic Kuzu integration with schema

**Tasks:**
1. Add `kuzu` to dependencies
2. Create `src/idlergear/graph/` module
3. Implement schema initialization from research
4. Add database connection management
5. Write basic tests

**Files:**
- `pyproject.toml` (add kuzu dependency)
- `src/idlergear/graph/database.py`
- `src/idlergear/graph/schema.py`
- `tests/test_graph_init.py`

**Success Criteria:**
- ✅ Kuzu database creates successfully
- ✅ Schema initializes without errors
- ✅ Can insert and query basic nodes

### Phase 2: Git History Populator (Day 3)

**Goal:** Index git commits and file changes

**Tasks:**
1. Implement `GitPopulator` class
2. Parse git log for commits
3. Extract file changes from diffs
4. Link commits to files
5. Handle branches

**Files:**
- `src/idlergear/graph/populators/git_populator.py`
- `tests/test_git_populator.py`

**Success Criteria:**
- ✅ Can index last 100 commits
- ✅ Files linked to commits correctly
- ✅ Branch information captured
- ✅ Incremental updates work (only new commits)

### Phase 3: Code Symbol Populator (Day 4)

**Goal:** Index Python symbols (functions, classes)

**Tasks:**
1. Implement `CodePopulator` class
2. Parse Python files with AST
3. Extract functions, classes, methods
4. Capture import relationships
5. Link symbols to files

**Files:**
- `src/idlergear/graph/populators/code_populator.py`
- `tests/test_code_populator.py`

**Success Criteria:**
- ✅ Can parse Python files
- ✅ Functions and classes indexed
- ✅ Import relationships captured
- ✅ File dependencies graph built

### Phase 4: Context Queries (Day 5)

**Goal:** Token-efficient context retrieval

**Tasks:**
1. Implement `TaskContext` queries
2. Implement `FileContext` queries
3. Implement `CommitContext` queries
4. Add query optimization
5. Benchmark token savings

**Files:**
- `src/idlergear/graph/context/task_context.py`
- `src/idlergear/graph/context/file_context.py`
- `src/idlergear/graph/context/commit_context.py`
- `benchmarks/token_efficiency.py`

**Success Criteria:**
- ✅ Queries return in <100ms
- ✅ 80%+ token savings vs grep
- ✅ Only relevant data returned (no over-fetching)

### Phase 5: MCP Integration (Day 6)

**Goal:** Expose graph queries via MCP tools

**Tasks:**
1. Add `idlergear_graph_query` MCP tool
2. Add `idlergear_graph_search` MCP tool
3. Add `idlergear_graph_related` MCP tool
4. Update MCP server documentation

**Files:**
- `src/idlergear/mcp_server.py` (add tools)
- `docs/mcp-tools.md` (document tools)

**Success Criteria:**
- ✅ MCP tools work in Claude Code
- ✅ Can query graph from chat
- ✅ Results are token-efficient

### Phase 6: CLI Commands (Day 7)

**Goal:** User-facing CLI for graph operations

**Tasks:**
1. Add `idlergear graph build` command
2. Add `idlergear graph query` command
3. Add `idlergear graph stats` command
4. Integrate with `idlergear context`

**Files:**
- `src/idlergear/cli.py`
- `src/idlergear/commands/graph.py`

**Success Criteria:**
- ✅ Can build graph from CLI
- ✅ Can query graph from CLI
- ✅ Stats show graph size, coverage

## Token Efficiency Strategy

### Problem: Current Approach

```bash
# Find functions related to "milestone"
grep -r "milestone" src/
# Returns: 2,500 tokens of grep output

# AI then reads files to understand context
cat src/idlergear/cli.py
# Returns: 5,000 tokens

# Total: 7,500 tokens
```

### Solution: Graph Queries

```python
# Query graph for milestone-related functions
conn.execute("""
    MATCH (s:Symbol)
    WHERE s.name CONTAINS 'milestone' OR s.docstring CONTAINS 'milestone'
    RETURN s.name, s.file_path, s.line_start
    LIMIT 5
""")

# Returns: 50-100 tokens (just the relevant locations)
# AI can then read specific line ranges

# Token savings: 98%
```

### Benchmarks (Target)

| Query | Before | After | Savings |
|-------|--------|-------|---------|
| Find "milestone" functions | 7,500 | 100 | **98.7%** |
| Related to cli.py | 8,000 | 200 | **97.5%** |
| Context (full) | 17,000 | 2,000 | **88.2%** |
| Recent changes | 3,200 | 150 | **95.3%** |
| **Average** | **8,925** | **612** | **93.1%** |

## Query Examples

### 1. Find Tasks Related to File

```cypher
MATCH (t:Task)-[:MODIFIES]->(f:File {path: $file_path})
RETURN t.id, t.title, t.state
LIMIT 5
```

**Token efficiency:** Returns only task IDs and titles, not full bodies.

### 2. Get Recent Activity

```cypher
MATCH (c:Commit)-[:CHANGES]->(f:File)
WHERE c.timestamp > $since
RETURN c.short_hash, f.path, c.message
ORDER BY c.timestamp DESC
LIMIT 10
```

**Token efficiency:** Compact commit summaries, no full diffs.

### 3. Find Related Files

```cypher
MATCH (f1:File {path: $file_path})-[:IMPORTS]->(f2:File)
RETURN f2.path, f2.language
```

**Token efficiency:** Just paths, not file contents.

### 4. Search Symbols

```cypher
MATCH (s:Symbol)
WHERE s.name CONTAINS $keyword
RETURN s.name, s.type, s.file_path, s.line_start
LIMIT 10
```

**Token efficiency:** Line numbers instead of full code.

## Database Location

**Path:** `~/.idlergear/graph.db`

**Why not in project?**
- Graph database is user-specific (different users index differently)
- Large binary files (don't belong in version control)
- Rebuild from source is cheap (<5s for IdlerGear codebase)

**Sharing:**
- Users can export to RDF (future: v0.7.0)
- Teams can use shared backend (GitHub Issues)

## Incremental Updates

### Strategy: Hash-Based Change Detection

```python
# Track file hashes in graph
CREATE (f:File {path: "src/cli.py", hash: "abc123", ...})

# On update, check hash
current_hash = sha256(file_content)
if current_hash != stored_hash:
    # Re-parse and update graph
    update_file_nodes(file)
```

### Update Triggers

1. **Manual:** `idlergear graph build`
2. **Automatic:** Git hooks (post-commit, post-merge)
3. **Watch mode:** File system watcher (future)

## Performance Targets

| Operation | Target | Measured |
|-----------|--------|----------|
| Full rebuild (IdlerGear) | <5s | TBD |
| Incremental update (10 files) | <1s | TBD |
| Simple query | <10ms | TBD |
| Complex query (3+ hops) | <100ms | TBD |
| Graph size | <50MB | TBD |

## Testing Strategy

### Unit Tests

- Schema initialization
- Each populator independently
- Query builders
- Context generators

### Integration Tests

- End-to-end graph build
- MCP tool integration
- CLI commands

### Performance Tests

- Benchmark query times
- Measure token savings
- Stress test with large repos

### Test Data

- Use IdlerGear codebase itself
- Create synthetic test repos
- Test incremental updates

## Migration from Current Approach

### Phase 1: Parallel Implementation

- Keep existing file-based approach
- Add graph queries as optional (`--use-graph` flag)
- Compare results and performance

### Phase 2: Gradual Adoption

- Make graph queries default
- Fall back to file-based on errors
- Collect metrics

### Phase 3: Full Migration

- Remove old code
- Graph queries only
- Document migration

## Future Enhancements (v0.7.0+)

### Semantic Search

```python
# Add embeddings to nodes
ALTER TABLE Symbol ADD COLUMN embedding FLOAT[768];

# Query by similarity
MATCH (s:Symbol)
WHERE vector_cosine_similarity(s.embedding, $query_embedding) > 0.8
RETURN s.name, s.file_path
LIMIT 5
```

### Full-Text Search

```cypher
# Index docstrings
CREATE FTS INDEX symbol_fts ON Symbol(docstring);

# Search
MATCH (s:Symbol)
WHERE fts_search(s, 'authentication flow')
RETURN s.name, s.file_path
```

### Cross-Repository Graphs

- Support monorepos
- Link dependencies across packages
- Shared symbol namespace

### Real-Time Updates

- File system watcher
- Automatic re-indexing
- Invalidate stale cache

## Dependencies

**Python Packages:**
- `kuzu>=0.11.3` (graph database)

**Development:**
- Research complete (#267)
- Schema designed (docs/research/)
- POC validated (<40ms queries)

## Success Metrics

### Quantitative

- ✅ 80%+ token savings (target: 90%)
- ✅ <100ms query latency (target: <50ms)
- ✅ <5s full rebuild time
- ✅ <1s incremental update
- ✅ <50MB graph size for IdlerGear

### Qualitative

- ✅ AI assistants use graph queries naturally
- ✅ Context is more relevant (fewer false positives)
- ✅ Discovery of related content is easy
- ✅ Users understand graph relationships

## Risks and Mitigations

### Risk: Kuzu immaturity

- **Mitigation:** Kuzu 0.11.3 is stable, used in production
- **Fallback:** Can export to NetworkX if needed
- **Monitoring:** Track Kuzu releases

### Risk: Graph becomes stale

- **Mitigation:** Hash-based change detection
- **Mitigation:** Git hooks for auto-rebuild
- **UX:** Show staleness indicator in CLI

### Risk: Large projects slow

- **Mitigation:** Incremental updates
- **Mitigation:** Lazy loading (only index what's queried)
- **Future:** Distributed graph for monorepos

### Risk: Token savings overstated

- **Mitigation:** Rigorous benchmarking
- **Mitigation:** A/B testing with real usage
- **Documentation:** Publish benchmarks openly

## Next Steps

1. ✅ Architecture complete (this document)
2. ⏳ Add Kuzu dependency
3. ⏳ Implement Phase 1 (foundation)
4. ⏳ Continue through phases 2-7
5. ⏳ Document and release

**Estimated timeline:** 7 days (full-time) or 2-3 weeks (part-time)

## References

- Research: `docs/research/knowledge-graph-comparison.md`
- Schema: `docs/research/knowledge-graph-schema.md`
- POC: `docs/research/poc-knowledge-graph/`
- Original task: #270

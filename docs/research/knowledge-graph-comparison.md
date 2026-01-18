# Knowledge Graph Technology Comparison: NetworkX vs Kuzu

**Research Date:** 2026-01-18
**Purpose:** Evaluate graph technologies for IdlerGear's knowledge graph implementation
**Related Issue:** #267

## Executive Summary

After researching both [NetworkX](https://networkx.org/) and [Kuzu](https://kuzudb.com/), **Kuzu is recommended** for IdlerGear's knowledge graph implementation due to:
- Persistent storage (critical for session continuity)
- Superior performance at scale (18x faster than Neo4j)
- Native Cypher query language (powerful graph traversals)
- Embedded architecture (no server required)
- Built-in vector search (for semantic queries)

NetworkX remains valuable for **prototyping** graph algorithms and **visualization**.

## Technology Overview

### NetworkX

[NetworkX](https://networkx.org/documentation/stable/) is a Python library for graph creation, manipulation, and analysis.

**Strengths:**
- Pure Python, easy to use
- Excellent for prototyping and algorithm development
- Rich algorithm library (PageRank, shortest paths, centrality, etc.)
- Great visualization support via Matplotlib
- Large community and extensive documentation
- Handles graphs up to 10M nodes + 100M edges

**Limitations:**
- **No persistence** - data lives in memory only (must pickle or export)
- **High memory usage** - each edge ~100 bytes (30M edges = 40GB+ RAM)
- **Pure Python overhead** - not optimized for very large graphs
- **No query language** - must write Python code for traversals
- **No ACID guarantees** - can't handle concurrent updates

**Best For:**
- Prototyping graph algorithms
- Small-to-medium graphs (<10M nodes)
- Network analysis and visualization
- Research and experimentation

**Sources:**
- [NetworkX Documentation](https://networkx.org/documentation/stable/index.html)
- [Graph Data Science with NetworkX | Toptal](https://www.toptal.com/data-science/graph-data-science-python-networkx)
- [NVIDIA NetworkX Glossary](https://www.nvidia.com/en-us/glossary/networkx/)

### Kuzu

[Kuzu](https://kuzudb.com/) is an embedded graph database optimized for analytical workloads.

**Strengths:**
- **Persistent storage** - data stored on disk with efficient columnar format
- **Blazing fast** - [18x faster than Neo4j](https://thedataquarry.com/blog/embedded-db-2/) in benchmarks
- **Cypher query language** - standard graph query language (like SQL for graphs)
- **Embedded architecture** - no server, just `pip install kuzu`
- **Built-in extensions** - vector search, full-text search, JSON
- **Scalable** - tested on 280M nodes + 1.7B edges (LDBC SF100)
- **Multi-core parallelism** - automatic query optimization
- **MIT license** - permissive open source
- **Sub-millisecond queries** - 30-hop path queries in milliseconds
- **Python-first** - designed for data science workflows
- **NetworkX interop** - can export to NetworkX for algorithms

**Limitations:**
- Newer project (less mature than NetworkX/Neo4j)
- Smaller community (but growing fast)
- Algorithm library not as extensive as NetworkX

**Best For:**
- Production knowledge graphs
- Persistent graph storage
- Large-scale data (millions of nodes/edges)
- Complex graph queries (multi-hop, pattern matching)
- AI/ML applications (vector search, embeddings)

**Sources:**
- [Kuzu GitHub](https://github.com/kuzudb/kuzu)
- [Kuzu Performance Study](https://github.com/prrao87/kuzudb-study)
- [Embedded Databases: Kuzu | The Data Quarry](https://thedataquarry.com/blog/embedded-db-2/)
- [Kuzu Documentation](https://docs.kuzudb.com/)

## Comparison Matrix

| Feature | NetworkX | Kuzu | Winner |
|---------|----------|------|--------|
| **Persistence** | ❌ Memory only | ✅ Disk-based | Kuzu |
| **Performance (large graphs)** | ~100 bytes/edge | 18x faster than Neo4j | Kuzu |
| **Query Language** | Python code | Cypher (declarative) | Kuzu |
| **Setup Complexity** | `pip install` | `pip install` | Tie |
| **Memory Efficiency** | High (40GB for 30M edges) | Low (columnar storage) | Kuzu |
| **Algorithm Library** | Extensive | Limited (use NetworkX) | NetworkX |
| **Visualization** | Built-in (Matplotlib) | Export to NetworkX | NetworkX |
| **Scalability** | 10M nodes max | 280M+ nodes tested | Kuzu |
| **Vector Search** | ❌ | ✅ Built-in | Kuzu |
| **Full-Text Search** | ❌ | ✅ Built-in | Kuzu |
| **Multi-hop Queries** | Slow (Python loops) | Fast (<ms) | Kuzu |
| **Concurrent Access** | ❌ | ✅ ACID | Kuzu |
| **Community Size** | Large | Growing | NetworkX |
| **Documentation** | Excellent | Good | NetworkX |

## IdlerGear-Specific Analysis

### Use Cases

IdlerGear needs a knowledge graph to represent:

1. **Knowledge Items:**
   - Tasks (with status, labels, priority)
   - Notes (transient thoughts)
   - References (permanent documentation)
   - Plans (implementation roadmaps)
   - Vision (project goals)

2. **Code Elements:**
   - Files (source code)
   - Functions/Classes (code symbols)
   - Modules (packages)

3. **Git Elements:**
   - Commits (changes)
   - Branches (code versions)
   - Diffs (file changes)

4. **Relationships:**
   - Task → File (task modifies file)
   - Task → Commit (task implemented in commit)
   - Note → Task (note promoted to task)
   - Note → Reference (note promoted to reference)
   - File → File (imports/dependencies)
   - Commit → File (commit changes file)
   - Reference → Code (reference documents code)
   - Task → Task (dependencies, blocks)

### Requirements

| Requirement | Importance | NetworkX | Kuzu |
|-------------|-----------|----------|------|
| Persistence across sessions | **Critical** | ❌ | ✅ |
| Fast context retrieval (<100ms) | **Critical** | ⚠️ | ✅ |
| Token-efficient queries | **High** | ⚠️ | ✅ |
| Graph traversal (find related items) | **High** | ✅ | ✅ |
| Incremental updates | **High** | ⚠️ | ✅ |
| Vector/semantic search | **Medium** | ❌ | ✅ |
| Easy setup (embedded) | **Medium** | ✅ | ✅ |
| Algorithm development | **Low** | ✅ | ⚠️ |
| Visualization | **Low** | ✅ | ⚠️ |

### Decision Factors

**Why Kuzu Wins:**

1. **Persistence** - IdlerGear must store knowledge across sessions. NetworkX would require pickling/serialization on every change, adding complexity and overhead.

2. **Performance** - As projects grow (1000s of tasks, 10,000s of commits), Kuzu's columnar storage and optimized queries will significantly outperform NetworkX's Python dictionaries.

3. **Query Language** - Cypher makes complex queries simple:
   ```cypher
   // Find all tasks related to a file (direct + indirect)
   MATCH (t:Task)-[:MODIFIES]->(f:File {path: "api.py"})
   OPTIONAL MATCH (t)-[:IMPLEMENTED_IN]->(c:Commit)-[:CHANGES]->(f)
   RETURN t, c
   ```

   vs NetworkX:
   ```python
   # Must write custom traversal logic
   tasks = []
   for node in graph.nodes():
       if graph.nodes[node]['type'] == 'task':
           # Check direct edges
           for neighbor in graph.neighbors(node):
               if graph.nodes[neighbor].get('path') == 'api.py':
                   tasks.append(node)
           # Check indirect (via commits)... more code
   ```

4. **Vector Search** - Future semantic queries like "find tasks similar to this one" require embeddings + vector search, built into Kuzu.

5. **Token Efficiency** - Kuzu can return minimal projections:
   ```cypher
   MATCH (t:Task)-[:RELATED_TO]->(f:File)
   RETURN t.id, t.title, f.path  // Only what we need
   ```

**When to Use NetworkX:**

- **Prototyping** - Testing graph algorithms before implementing in Kuzu
- **Visualization** - Kuzu can export to NetworkX for visualization
- **One-off analysis** - Quick analysis on small graphs

## Recommendation

### Primary: Kuzu

Use Kuzu as the **primary knowledge graph** storage with:
- Schema defined in Cypher DDL
- MCP tools for graph queries
- Background indexer to populate graph from git/code
- Token-efficient context retrieval

### Secondary: NetworkX

Use NetworkX as a **complementary tool** for:
- Prototyping new graph algorithms
- Generating visualizations for debugging
- Exporting Kuzu graphs for analysis

### Hybrid Approach

```python
# Store in Kuzu, analyze with NetworkX
import kuzu
import networkx as nx

# Query Kuzu
db = kuzu.Database("./idlergear.db")
conn = kuzu.Connection(db)
result = conn.execute("MATCH (n)-[r]->(m) RETURN n, r, m")

# Export to NetworkX for visualization
G = nx.DiGraph()
for record in result:
    G.add_edge(record['n'], record['m'], type=record['r'])

nx.draw(G, with_labels=True)
```

## Next Steps

1. ✅ Research completed
2. ⏳ Design knowledge graph schema (node types, relationships)
3. ⏳ Build POC with Kuzu
4. ⏳ Implement graph populator (index git + code)
5. ⏳ Add MCP tools for graph queries
6. ⏳ Integrate with `idlergear context` command

## References

### NetworkX
- [NetworkX Documentation](https://networkx.org/documentation/stable/index.html)
- [NetworkX on Wikipedia](https://en.wikipedia.org/wiki/NetworkX)
- [Graph Data Science with NetworkX | Toptal](https://www.toptal.com/data-science/graph-data-science-python-networkx)
- [NetworkX Guide to Network Analysis | Medium](https://medium.com/@tushar_aggarwal/networkx-a-comprehensive-guide-to-mastering-network-analysis-with-python-fd7e5195f6a0)

### Kuzu
- [Kuzu Official Website](https://kuzudb.com/)
- [Kuzu GitHub Repository](https://github.com/kuzudb/kuzu)
- [Kuzu Documentation](https://docs.kuzudb.com/)
- [Kuzu Performance Benchmark Study](https://github.com/prrao87/kuzudb-study)
- [Embedded Databases: Kuzu | The Data Quarry](https://thedataquarry.com/blog/embedded-db-2/)
- [Kuzu Memory for AI Applications](https://github.com/bobmatnyc/kuzu-memory)
- [Kuzu LangChain Integration](https://docs.langchain.com/oss/python/integrations/graphs/kuzu_db)

### Comparisons
- [NetworkX vs Graph Databases | Restack](https://www.restack.io/p/knowledge-graph-networkx-vs-graph-tool-cat-ai)
- [Neo4j vs NetworkX Discussion | Neo4j Community](https://community.neo4j.com/t/what-is-the-difference-between-using-neo4j-for-graph-analytics-and-using-python-networkx-for-graph-analytics/31005)
- [Graph Databases Explained | Cognee](https://www.cognee.ai/blog/fundamentals/graph-databases-explained)

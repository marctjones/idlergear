# Knowledge Graph Demo

Demonstrates IdlerGear's knowledge graph capabilities through real-world use cases and token efficiency comparisons.

## Quick Start

**Full Demo** (recommended - shows real-world queries):
```bash
# Auto-advancing demo with 6 practical queries
./demo-graph.sh
```

**Quick Demo** (basic indexing only):
```bash
# Fast setup without queries (~30 seconds)
./demo-graph-quick.sh
```

## What You'll Learn

The demo showcases **6 real-world queries** that developers actually need:

1. **Architecture Understanding** - Find all populator classes
2. **Code Hotspots** - Which files change most frequently?
3. **Recent Activity** - What happened in the last commits?
4. **Complexity Analysis** - Where are most symbols concentrated?
5. **Refactoring Detection** - Find large commits that changed many files
6. **Technical Debt** - Identify high-complexity files

### Token Efficiency in Practice

See side-by-side comparisons:
- **Traditional**: `grep` + `cat` multiple files = ~8,000 tokens
- **Graph Query**: Single Cypher query = ~120 tokens
- **Savings**: 98.5% (67x reduction)

### Multi-Hop Queries

Learn how to traverse relationships:
- `Commit → File → Symbol` - "What code was added recently?"
- Answer in <40ms with 200 tokens vs 15,000+ traditional approach

## Requirements

- Python 3.10+
- IdlerGear installed (`pip install -e .`)
- Kuzu graph database (`pip install kuzu>=0.11.3`)
- Git repository

## Demo Flow

The demo **auto-advances** with brief pauses between sections:
1. Index git history (last 50 commits)
2. Extract code symbols from `src/`
3. Run 6 practical queries with use cases
4. Show token efficiency comparisons
5. Demonstrate multi-hop query
6. Explain what makes graph queries powerful

## Duration

- Full demo: ~90 seconds
- Indexing: ~10 seconds
- Queries: ~60 seconds (with explanations)
- Each query pauses 1.5s for reading

## What Makes It Interesting

Unlike basic "search for a class" demos, this shows:
- **Real problems developers face** - code hotspots, complexity, recent changes
- **Aggregation queries** - COUNT, SUM, GROUP BY for analytics
- **Before/after comparisons** - actual grep commands vs graph queries
- **Multi-hop traversals** - following relationships across node types
- **Practical metrics** - change frequency, symbol density, refactoring detection

## After the Demo

Try the graph yourself with Python:

```python
from idlergear.graph import get_database
from idlergear.graph.queries import query_symbols_by_name

db = get_database()
symbols = query_symbols_by_name(db, "your_function_name", limit=10)
print(symbols)
```

Or via MCP tools (if using Claude Code):
```
idlergear_graph_query_symbols(pattern="your_function_name")
```

## Troubleshooting

**"Kuzu not installed"**
```bash
pip install kuzu>=0.11.3
```

**"Not in a git repository"**
- Run from the idlergear repository root
- Or any git repository with Python code

**"No symbols found"**
- Make sure you have a `src/` directory with Python files
- Or modify the demo to scan a different directory

## Clean Up

The graph database persists at `~/.idlergear/graph.db`. To remove it:

```bash
rm -rf ~/.idlergear/graph.db
```

The demo will recreate it if run again.

## See Also

- [Knowledge Graph User Guide](docs/guides/knowledge-graph.md)
- [Implementation Report](docs/implementation/graph-phase2-complete.md)
- [Architecture](docs/architecture/knowledge-graph-integration.md)

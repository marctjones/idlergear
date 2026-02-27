---
id: 85
title: 'Bug: Code symbol populator fails on apostrophes/quotes in symbol names'
state: closed
created: '2026-02-27T03:18:18.932973Z'
accessed: '2026-02-27T03:22:22.148315Z'
access_count: 1
relevance_score: 1.0
labels:
- bug
- indexing
- knowledge-graph
- 'priority: high'
priority: high
---
## Problem

Code symbol population fails with parser exception when symbol names contain apostrophes or quotes.

## Error

```
Parser exception: Invalid input <MATCH (f:File {path: 'src/idlergear/cli.py'})-[r:CONTAINS]->(s:Symbol {id: 'src/idlergear/cli.py:6448:didn't work out'})
```

The apostrophe in `didn't` is not being escaped in the Cypher query.

## Root Cause

The code populator likely uses string interpolation to build Cypher queries without properly escaping quotes:
```python
query = f"... Symbol {{id: '{symbol_id}'}} ..."  # WRONG - no escaping
```

## Solution

Escape quotes in symbol IDs/names before inserting into Cypher queries:
```python
symbol_id = symbol_id.replace("'", "\\'")
# or use parameterized queries
```

## Impact

- Symbol indexing completely broken
- Background indexing cannot complete
- Knowledge graph missing 2,840 symbols
- 95-98% token savings features not available for symbol lookups

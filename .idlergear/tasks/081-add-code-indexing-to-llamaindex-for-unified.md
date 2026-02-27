---
id: 81
title: Add code indexing to LlamaIndex for unified code+docs search
state: open
created: '2026-02-03T05:30:53.715306Z'
accessed: '2026-02-03T05:37:56.110672Z'
access_count: 3
relevance_score: 1.0
labels:
- enhancement
---
## Motivation

Currently we have separation:
- ChromaDB: Code similarity search (function bodies, algorithms)
- LlamaIndex: Documentation search (references, notes, guides)

## Proposed Feature

Add code indexing to LlamaIndex to enable unified hybrid search:
- Query both code AND documentation in one search
- Example: "Find authentication code and related documentation"
- Natural language queries over code: "How is JWT validation implemented?"

## Benefits

1. **Unified interface** - Single search across all project knowledge
2. **Context-rich results** - Code + docs together for better understanding
3. **Natural language code queries** - Ask questions about implementation
4. **Better token efficiency** - One search instead of two separate queries

## Implementation Ideas

1. **Raw code → ChromaDB** (for similarity matching)
2. **Code summaries → LlamaIndex** (for natural language queries)
3. **Hybrid search API** - Query both systems, merge results

## Relation to #404

This could be part of Code Summarization (#404):
- Generate summaries of functions/classes
- Index summaries in LlamaIndex for natural language search
- Keep raw code in ChromaDB for similarity

## API Example

```python
# Current (separate):
code_results = idlergear_code_search("authentication")
doc_results = idlergear_rag_search("authentication")

# Proposed (unified):
results = idlergear_unified_search("authentication", sources=["code", "docs"])
# Returns: [{type: "function", ...}, {type: "reference", ...}]
```

## Token Savings

- Current: 2 searches = ~200 tokens
- Unified: 1 search = ~150 tokens (25% savings)
- Plus: More relevant results by combining context

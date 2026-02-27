---
id: 84
title: 'Bug: Background indexing stuck after annotating 55 files, not progressing
  to git commits/symbols'
state: closed
created: '2026-02-27T03:11:42.844738Z'
accessed: '2026-02-27T03:18:36.234725Z'
access_count: 1
relevance_score: 1.0
labels:
- bug
- indexing
- 'priority: high'
priority: high
---
## Problem

Background indexing gets stuck after successfully annotating 55 files. Subsequent batches all annotate 0 files and make no progress on remaining work (git commits, code symbols).

## Observed Behavior

1. Initial status: 135 file annotations, 99 git commits, 2839 code symbols remaining (234 items total)
2. First `idlergear index run --batches 50`:
   - Batches 1-11: Successfully annotated 5 files each (55 total)
   - Batches 12-50: Annotated 0 files each
   - Reports "174 items remaining"
3. Second `idlergear index run --batches 50`:
   - All batches (1-50): Annotated 0 files each
   - Still reports "174 items remaining" (no progress)

## Expected Behavior

After completing file annotations, indexing should automatically switch to:
1. Indexing git commits (99 remaining)
2. Indexing code symbols (2839 remaining)

## Root Cause Hypothesis

The batch processing logic likely:
- Only processes one work type at a time
- Gets stuck when one work type returns empty results
- Doesn't automatically switch to the next work type

## Impact

- File annotation indexing incomplete (80 files remain)
- Git commit indexing not starting
- Code symbol indexing not starting
- Token savings features not fully operational

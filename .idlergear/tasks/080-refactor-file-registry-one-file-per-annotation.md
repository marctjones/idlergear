---
id: 80
title: 'Refactor file registry: one-file-per-annotation (git-friendly, scalable)'
state: open
created: '2026-02-02T02:30:25.974136Z'
accessed: null
access_count: 0
relevance_score: 1.0
labels:
- enhancement
priority: high
---
## Problem

Current: Single JSON file causes git conflicts, doesn't scale
Proposed: One file per annotation (like tasks/notes)

Structure: .idlergear/file_annotations/src/api/auth.py.json

Benefits: Git diffs, no conflicts, infinite scale

Related: #399, #384, #295

Effort: 2-3 days

---
id: 49
title: Implement token-efficient context modes for idlergear context
state: closed
created: '2026-01-07T03:35:40.260612Z'
labels:
- enhancement
- performance
- token-efficiency
priority: high
---
## Problem

`idlergear context` can return 15K-20K+ tokens when projects have:
- Many open tasks (10+)
- Long task descriptions with full bodies
- Long vision/plan documents
- Large reference documents

Current implementation has minimal limits:
- max_tasks=10 (but includes full bodies)
- max_notes=5 (truncated to 80 chars)
- Vision/plan included in full

## Solution: Multi-Mode Context System

### Mode 1: **Minimal** (Default, ~500-1000 tokens)
**Use case**: Session start, quick refresh
- Vision: First paragraph only (max 200 chars)
- Plan: Title + 3-line summary only
- Tasks: Top 5 by priority, titles only (no bodies)
- Notes: Count only
- References: Excluded
- **Target**: <1000 tokens

### Mode 2: **Standard** (~2000-3000 tokens)
**Use case**: General development work
- Vision: First 500 chars
- Plan: Title + first 10 lines
- Tasks: Top 10, titles + first line of body
- Notes: Last 5, truncated to 80 chars
- References: Titles only (no bodies)
- **Target**: <3000 tokens

### Mode 3: **Detailed** (~5000-10000 tokens)
**Use case**: Deep planning, research
- Vision: Full (but capped at 2000 chars)
- Plan: Full (capped at 3000 chars)
- Tasks: Top 20, full bodies
- Notes: Last 10, full content
- References: Full titles + first 200 chars
- **Target**: <10000 tokens

### Mode 4: **Full** (Unlimited, current behavior)
**Use case**: Rare, when explicitly needed
- Everything in full
- No truncation
- No limits

## Implementation

1. Add `mode` parameter to `idlergear_context` tool
2. Update `gather_context()` to accept mode parameter
3. Add truncation utilities for smart content trimming
4. Update format functions to respect mode
5. Change default from "full" to "minimal"

## Token Savings

| Mode | Tokens | Savings | Use Case |
|------|--------|---------|----------|
| Minimal | ~750 | 95%+ | Session start |
| Standard | ~2500 | 85% | Regular dev |
| Detailed | ~7000 | 60% | Deep work |
| Full | ~17000 | 0% | Rare |

## Benefits

1. **Faster sessions** - Less wait time for context loading
2. **More context budget** - AI can think more with saved tokens
3. **Better UX** - Quicker responses
4. **Opt-in verbosity** - Only pay token cost when needed
5. **Backwards compatible** - Add mode param, default to minimal

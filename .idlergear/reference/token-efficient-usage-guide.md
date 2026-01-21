---
id: 1
title: Token-Efficient Usage Guide
created: '2026-01-07T05:34:16.624090Z'
updated: '2026-01-07T05:34:16.624112Z'
---
# Token-Efficient Usage Guide

## Overview

IdlerGear commands are designed to be **token-efficient** for AI assistants. Large context windows waste tokens and can cause output truncation. This guide shows how to minimize token usage while getting the information you need.

## Problem: Token Waste

**Before** (inefficient):
```bash
idlergear context  # Returns ~17,000 tokens (all tasks with full bodies!)
```

**After** (efficient):
```bash
idlergear context --mode minimal  # Returns ~750 tokens (titles only)
```

### Real-World Impact

| Command | Default (Old) | Minimal Mode | Savings |
|---------|---------------|--------------|---------|
| `context` | ~17,000 tokens | ~750 tokens | **95% reduction** |
| `task list` (10 tasks) | ~5,000 tokens | ~200 tokens | **96% reduction** |
| `note list` | ~2,000 tokens | Counts only | **99% reduction** |

## Context Modes

The `idlergear context` command has **4 verbosity modes**:

### 1. Minimal (~750 tokens) - **DEFAULT**
**Use for:** Session start, quick refresh

```bash
idlergear context
idlergear context --mode minimal
```

**Returns:**
- Vision: First 200 characters
- Plan: First 3 lines
- Tasks: Top 5 (titles only, no bodies)
- Notes: Count only (not content)
- Explorations: Count only

**Example output:**
```
Vision: IdlerGear is structured project management for AI...

Open Tasks (5):
- #118: Context command returns too much content
- #117: Fix GitHubReferenceBackend
- #116: Add reference sync command
- #115: Add release command
- #114: Add session persistence

Notes: 5  |  Explorations: 0
```

### 2. Standard (~2,500 tokens)
**Use for:** General development work

```bash
idlergear context --mode standard
```

**Returns:**
- Vision: First 500 characters
- Plan: First 10 lines
- Tasks: Top 10 (1-line preview per task)
- Notes: Last 5 notes (preview)
- Explorations: Last 3

### 3. Detailed (~7,000 tokens)
**Use for:** Deep planning, architecture decisions

```bash
idlergear context --mode detailed
```

**Returns:**
- Vision: First 1500 characters
- Plan: First 50 lines
- Tasks: Top 15 (5-line preview per task)
- Notes: Last 8 notes (full content)
- Explorations: Last 5

### 4. Full (17,000+ tokens)
**Use for:** Rare cases when you need EVERYTHING

```bash
idlergear context --mode full
```

**Returns:**
- Everything with no truncation
- All tasks with full bodies
- All notes
- All explorations

## Task List Efficiency

### Limit Results

```bash
# Only top 5 tasks
idlergear task list --limit 5

# Only high-priority tasks
idlergear task list --priority high

# Combine filters
idlergear task list --priority high --limit 3
```

### Preview Mode (Titles Only)

```bash
# Strip task bodies entirely (minimal tokens)
idlergear task list --preview

# Combine with limit
idlergear task list --preview --limit 10
```

**Comparison:**
```bash
# Before: ~500 tokens per task (with full body)
idlergear task list  # 10 tasks = ~5,000 tokens

# After: ~50 tokens per task (title only)
idlergear task list --preview --limit 10  # ~500 tokens
```

## MCP Tools (For AI Assistants)

All MCP tools default to **token-efficient modes**:

### Context Tool

```python
# Default: minimal mode (~750 tokens)
idlergear_context()

# Explicit modes
idlergear_context(mode="minimal")    # ~750 tokens
idlergear_context(mode="standard")   # ~2500 tokens
idlergear_context(mode="detailed")   # ~7000 tokens
idlergear_context(mode="full")       # ~17000+ tokens
```

### Task List Tool

```python
# Default: all open tasks (potentially large)
idlergear_task_list(state="open")

# Token-efficient: limit results
idlergear_task_list(state="open", limit=5)
```

## Best Practices

### 1. Start Minimal, Expand as Needed

```bash
# Session start: minimal
idlergear context  # (~750 tokens)

# Need more detail on specific task?
idlergear task show 118  # Only that task

# Deep planning session?
idlergear context --mode detailed  # (~7000 tokens)
```

### 2. Use Targeted Queries

**Don't:**
```bash
idlergear context --mode full  # Get everything (wasteful)
```

**Do:**
```bash
idlergear context  # Get overview (750 tokens)
idlergear task list --limit 5  # Top 5 tasks only
idlergear note list --limit 3  # Recent notes only
```

### 3. Preview Before Full Fetch

```bash
# Step 1: See titles only
idlergear task list --preview

# Step 2: Get full details for specific task
idlergear task show 118
```

### 4. Filter at Query Time

```bash
# Filter to reduce results
idlergear task list --priority high --limit 3
idlergear task list --state open --limit 10
```

## Token Budgets by Use Case

| Use Case | Recommended Mode | Est. Tokens | Command |
|----------|------------------|-------------|---------|
| Session start | minimal | ~750 | `idlergear context` |
| Quick status check | status | ~200 | `idlergear status` |
| Browse tasks | preview + limit | ~500 | `idlergear task list --preview --limit 10` |
| Plan review | standard | ~2500 | `idlergear context --mode standard` |
| Architecture planning | detailed | ~7000 | `idlergear context --mode detailed` |
| Full audit | full | ~17000+ | `idlergear context --mode full` |

## Configuration

You can set default modes in `.idlergear/config.toml`:

```toml
[context]
default_mode = "minimal"  # or standard, detailed, full

[tasks]
default_limit = 10
preview_by_default = false
```

## Migration from Old Behavior

**Old default** (before 2026-01-07):
- `idlergear context` returned FULL mode (~17,000 tokens)
- Task bodies included in full

**New default** (after 2026-01-07):
- `idlergear context` returns MINIMAL mode (~750 tokens)
- Use `--mode full` for old behavior

**Migration:**
```bash
# Old behavior
idlergear context  # ~17K tokens

# New equivalent
idlergear context --mode full  # ~17K tokens

# Recommended new usage
idlergear context  # ~750 tokens (efficient!)
```

## Troubleshooting

### "Not enough detail in context"

**Solution:** Use a higher verbosity mode
```bash
idlergear context --mode standard  # or detailed
```

### "Output is too large, causing truncation"

**Solution:** Use minimal mode or limit results
```bash
idlergear context --mode minimal
idlergear task list --limit 5
```

### "I need full task #118 body"

**Solution:** Query that task specifically
```bash
idlergear task show 118
```

## Summary

**Key Principles:**
1. **Default to minimal** - Start with least tokens, expand as needed
2. **Query specifically** - Ask for exactly what you need
3. **Use limits** - Cap result sizes
4. **Preview mode** - Strip bodies when scanning titles
5. **Mode selection** - Match verbosity to use case

**Token Savings:**
- Minimal mode: **95% reduction** vs full
- Preview mode: **90% reduction** vs full bodies
- Limit flags: **Variable** (depends on filter)

**Best Practice:**
```bash
# Every session start
idlergear context  # ~750 tokens, instant overview

# Deep dive only when needed
idlergear task show <id>  # Specific task
idlergear context --mode detailed  # Full planning session
```

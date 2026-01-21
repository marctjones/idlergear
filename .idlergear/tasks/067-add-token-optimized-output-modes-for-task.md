---
id: 67
title: Add token-optimized output modes for task subcommands
state: closed
created: '2026-01-08T01:16:51.194358Z'
labels:
- enhancement
- 'component: cli'
- core-v1
priority: high
---
## Summary

Add token-efficient output modes to `idlergear task` subcommands to reduce context usage when called by AI assistants.

## Problem

Current `idlergear task list` output includes full task bodies, which can consume significant tokens. When Claude Code calls these commands, the verbose output wastes context window.

## Proposed Solution

Add flags for compact/minimal output:

```bash
# Current (verbose)
idlergear task list
# Returns full JSON with bodies, labels, dates, etc.

# Proposed: Preview mode (titles only)
idlergear task list --preview
# Returns: "1. [high] Title one\n2. [med] Title two"

# Proposed: Compact JSON
idlergear task list --compact
# Returns minimal JSON: [{"id": 1, "title": "...", "priority": "high"}]

# Proposed: Limit results
idlergear task list --limit 5
# Returns only first 5 tasks

# Combine for maximum efficiency
idlergear task list --preview --limit 10
# ~200 tokens vs ~2000+ tokens
```

## Implementation

1. Add `--preview` flag: Output as simple numbered list (human-readable)
2. Add `--compact` flag: Minimal JSON (id, title, priority, state only)
3. Add `--limit N` flag: Limit number of results
4. Update MCP tools to use compact mode by default

## Acceptance Criteria

- [ ] `--preview` outputs human-readable list without bodies
- [ ] `--compact` outputs minimal JSON
- [ ] `--limit N` limits results
- [ ] MCP tools use token-efficient defaults
- [ ] Documented in help text

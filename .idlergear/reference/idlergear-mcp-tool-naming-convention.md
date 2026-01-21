---
id: 1
title: IdlerGear MCP Tool Naming Convention
created: '2026-01-17T21:27:26.564447Z'
updated: '2026-01-17T21:27:26.564484Z'
---
## Decision

When building MCP tools as part of IdlerGear, use IdlerGear branding.

## Rationale

1. These tools are part of the IdlerGear ecosystem
2. Users interact via `idlergear fs list`, not `mcp_fs.list()`
3. Consistency with existing commands (`idlergear task`, `idlergear note`, etc.)
4. Option for shorthand: `ig fs list` for faster typing

## Command Structure

```bash
idlergear fs list ./src         # Full form
idlergear git status            # Full form
ig fs list ./src                # Short form
ig git status                   # Short form
```

## MCP Tool Naming

When exposed to MCP protocol, tools should be:
- `idlergear_fs_list()` (MCP protocol name)
- `idlergear_git_status()` (MCP protocol name)

NOT:
- `mcp_fs.list()` ❌
- `mcp_git.status()` ❌

## Implementation Note

Research existing MCP servers FIRST before building any tools to avoid duplication.

## Related

- Issue #223 (original decision)
- Current implementation: All 126 MCP tools follow this convention

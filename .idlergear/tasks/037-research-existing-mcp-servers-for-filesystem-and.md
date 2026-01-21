---
id: 37
title: Research existing MCP servers for fs, git, env, and process operations
state: open
created: '2026-01-07T01:48:11.293202Z'
labels:
- research
- mcp
- goose
priority: high
---
Before building any custom MCP tools in IdlerGear, research what already exists to avoid reinventing the wheel.

**Areas to research:**

1. **Filesystem Operations**
   - Directory listing (ls/tree alternatives)
   - File search (find alternatives)
   - File metadata operations
   - Existing: Check MCP registry, GitHub for "mcp filesystem", "mcp files"

2. **Git Operations**
   - Status, diff, log with structured output
   - Existing: Search for "mcp git", check if GitHub has official MCP git tools

3. **Environment/System Info**
   - Python/Node version detection
   - Virtual environment detection
   - PATH inspection
   - Existing: Check for "mcp env", "mcp system"

4. **Process Management**
   - Process listing (ps alternatives)
   - Existing: Check for "mcp process", "mcp ps"

**Deliverable:**
- Document what exists and what gaps remain
- For each gap, determine if it should be part of IdlerGear or a separate MCP server
- Update tasks #38-40 based on findings (close if tool exists, modify if partial overlap)

**Key Decision:**
If good MCP servers exist, we should USE them (via dependencies/integration) rather than rebuild.
Only build `idlergear fs`, `idlergear git`, etc. for gaps or IdlerGear-specific optimizations.

**Research Sources:**
- https://github.com/modelcontextprotocol
- MCP registry/directory (if exists)
- GitHub search: "mcp server" + topic
- Anthropic docs on existing MCP tools

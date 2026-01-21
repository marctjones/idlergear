---
id: 36
title: Add command to register IdlerGear as Goose GUI extension
state: open
created: '2026-01-07T01:38:47.514474Z'
labels:
- enhancement
- goose-integration
- gui
- mcp
priority: high
---
Create a command (e.g., `idlergear goose register`) that registers IdlerGear as an extension in the Goose GUI.

## Requirements

- Command should handle Goose GUI extension registration workflow
- Automatically configure necessary metadata (name, description, capabilities)
- Register MCP server endpoints with Goose
- Handle authentication/permissions if needed
- Verify registration was successful
- Provide clear feedback to user

## Investigation Needed

- Research Goose GUI extension registration API/process
- Understand Goose's extension manifest format
- Determine if registration is per-user or system-wide
- Identify where Goose stores extension configuration

## Success Criteria

- User can run `idlergear goose register` to add IdlerGear to Goose GUI
- IdlerGear appears in Goose GUI's extension list
- All MCP tools are accessible from Goose GUI interface
- Command is idempotent (safe to run multiple times)

## Related

- Depends on understanding Goose architecture (Task #35)
- Related to Goose-specific MCP tools (Task #32)

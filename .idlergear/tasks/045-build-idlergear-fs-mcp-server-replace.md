---
id: 45
title: Build idlergear fs MCP server (replace @modelcontextprotocol/server-filesystem)
state: closed
created: '2026-01-07T02:31:09.701297Z'
labels:
- enhancement
- mcp
- filesystem
- high-priority
priority: high
---
## Goal
Replace the Node.js @modelcontextprotocol/server-filesystem with a Python-native IdlerGear implementation.

## Why Replace?
- **Single runtime**: Eliminate Node.js dependency, use Python everywhere
- **Better integration**: Direct access to IdlerGear's file context
- **Consistency**: Same codebase, testing, deployment as rest of IdlerGear
- **Performance**: No npx overhead, direct Python execution
- **Customization**: Can add IdlerGear-specific features (e.g., filter by task files)

## Tools to Implement
Based on official server (https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem):

1. **read_file(path)** - Read file contents
2. **read_multiple_files(paths)** - Batch read
3. **write_file(path, content)** - Write file
4. **edit_file(path, edits)** - Apply structured edits
5. **create_directory(path)** - Make directory
6. **list_directory(path)** - List contents
7. **directory_tree(path)** - Recursive tree view
8. **move_file(source, destination)** - Move/rename
9. **search_files(path, pattern, exclude)** - gitignore-aware search
10. **get_file_info(path)** - File metadata
11. **list_allowed_directories()** - Show accessible paths
12. **get_file_checksum(path)** - MD5/SHA256 checksums

## Additional IdlerGear-Specific Features
- `search_task_files(task_id)` - Find files related to a task
- Auto-exclude patterns from .gitignore
- Integration with IdlerGear's context system

## Implementation Notes
- Use pathlib for cross-platform paths
- Security: sandboxing to allowed directories
- Token optimization: configurable depth/exclusions
- Structured JSON output (not raw text)

## Dependencies
- Python stdlib only (pathlib, os, shutil, hashlib, fnmatch)
- gitignore parsing: use gitignore_parser (pip)

## Estimated Effort
~500-800 LOC, 4-6 hours

## References
- Original: https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem
- MCP servers listing: https://mcpservers.org/servers/modelcontextprotocol/filesystem

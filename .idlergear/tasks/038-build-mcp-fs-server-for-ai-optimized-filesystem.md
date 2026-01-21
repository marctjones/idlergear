---
id: 38
title: Integrate official @modelcontextprotocol/server-filesystem (DO NOT BUILD)
state: open
created: '2026-01-07T01:48:11.308424Z'
labels:
- enhancement
- mcp
- filesystem
- goose
priority: high
---
## Research Complete: DO NOT BUILD

Research (Task #42, Note #8) found the official @modelcontextprotocol/server-filesystem already provides ALL features we need:
- ✅ Structured JSON outputs (directory_tree tool)
- ✅ Gitignore-aware search (search_files with exclusion patterns)
- ✅ Token-efficient (no parsing needed)
- ✅ Fast (<100ms, local Node.js)
- ✅ Secure (path validation, allowed directories)
- ✅ Official Anthropic support

## Instead: INTEGRATE, don't rebuild

1. Add @modelcontextprotocol/server-filesystem as a dependency/recommendation
2. Document how to configure it with IdlerGear
3. Update .goosehints template to include it
4. Consider thin wrappers for IdlerGear-specific features:
   - `idlergear fs link <file> <task_id>` - Link file changes to tasks
   - `idlergear fs track` - Show files being worked on for current task
   - `idlergear fs smart-ignore` - Project-aware .gitignore additions

## Tools Available (Official Server)
- read_text_file, read_media_file, read_multiple_files
- list_directory, list_directory_with_sizes, directory_tree
- write_file, edit_file, move_file
- search_files, get_file_info, create_directory
- list_allowed_directories

See Note #8 for complete research findings.

# Changelog

All notable changes to IdlerGear will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-01-21

### Added - File Registry System
- **File Registry Core** - Track file status (current/deprecated/archived/problematic) (#287)
  - FileRegistry data model with JSON storage
  - Status tracking with reason and successor information
  - Pattern-based file matching (e.g., `*.csv` → deprecated)
  - Status cache for performance optimization
- **File Annotations** - Token-efficient file discovery system (#304)
  - Annotate files with descriptions, tags, and components
  - Search annotations before using grep (93% token savings)
  - Related files tracking for navigation
  - Proactive annotation workflow for AI assistants
- **MCP File Access Interception** - Automatic file access control (#290)
  - Block AI assistant access to deprecated files with helpful error messages
  - Warn when writing to deprecated files (but allow updates)
  - Access logging to `.idlergear/access_log.jsonl` for audit trail
  - Override mechanism with `_allow_deprecated` parameter
  - URL and command flag detection to avoid false positives
- **Daemon Multi-Agent Coordination** - Real-time file registry synchronization (#291)
  - File registry changes broadcast to all connected agents within 1 second
  - Event callbacks for file_registered and file_deprecated events
  - MCP server automatic subscription to file.* events on startup
  - Graceful degradation when daemon not running
  - Wildcard subscription support for registry events

### Added - CLI Commands
File registry management commands (#288):
- `idlergear file register` - Register file with status
- `idlergear file deprecate` - Mark file as deprecated with successor
- `idlergear file status` - Change file status
- `idlergear file list` - List all registered files
- `idlergear file search` - Search file annotations
- `idlergear file annotate` - Add file annotations
- `idlergear file unregister` - Remove file from registry

### Added - MCP Tools
File registry tools for AI assistants (#289):
- `idlergear_file_register` - Register file programmatically
- `idlergear_file_deprecate` - Mark file as deprecated
- `idlergear_file_update_status` - Change file status
- `idlergear_file_list` - Query registered files
- `idlergear_file_search` - Search by annotations
- `idlergear_file_annotate` - Add file annotations
- `idlergear_file_get_annotations` - Retrieve file metadata
- `idlergear_file_unregister` - Remove file from registry

### Added - AI Assistant Integrations
- **Cursor AI** - IDE rules generation with `.mdc` files (#299)
- **Aider** - Configuration file generation (`.aider.conf.yml`) (#300)
- **GitHub Copilot** - Enhanced `COPILOT.md` template
- **Gemini** - Comprehensive `GEMINI.md` template
- **AGENTS.md** - Multi-assistant coordination guide

### Added - Documentation
- Comprehensive file registry user guide (#294)
- File annotations guide with examples
- MCP file interception documentation
- Quick start guide (`QUICKSTART.md`)
- Token efficiency best practices

### Fixed
- Mock server missing `storage_path` attribute in daemon tests
- CLI initialization tests affected by stale `/tmp/.idlergear`
- Unused variables in test file detection
- Invalid `verbose` parameter in context command
- Unused variable in installation assistant detection
- pipx installation support (#285)

### Improved
- End-to-end integration tests for file registry daemon (#296)
- 18 comprehensive tests for MCP file interception
- 9 tests for daemon multi-agent coordination
- Test isolation and cleanup

### Security
- Access logging for all file registry operations (`.idlergear/access_log.jsonl`)
- Audit trail for deprecated file access attempts
- Clear error messages prevent accidental use of outdated files

## [0.5.33] - 2026-01-21

### Added
- File registry event system for daemon broadcasts
- MCP server daemon subscription capabilities

### Fixed
- Unused variables in test file detection
- Invalid verbose parameter in context command
- Unused variable in installation assistant detection

## [0.5.22] - 2026-01-15

### Added
- Plugin system foundation
- LlamaIndex plugin for vector search
- Mem0 plugin for experiential memory
- Langfuse plugin for observability

### Improved
- Documentation updates
- README with plugin features

## [0.5.20] - 2026-01-14

### Added
- Cursor AI integration documentation
- README updates with current version

### Improved
- ROADMAP with current progress (v0.5.19)

## [0.5.19] - 2026-01-13

### Added
- Comprehensive AGENTS.md guidance
- Enhanced GEMINI.md template
- Enhanced COPILOT.md template

### Improved
- Multi-assistant coordination workflows

## [0.5.13] - 2026-01-12

### Added
- Plugin system (6 CLI tools, 6 MCP tools)
- Plugin discovery and management
- Semantic search capabilities
- Observability integration

## [0.5.11] - 2026-01-11

### Added
- Plugin system foundation
- LlamaIndex integration
- Langfuse integration

## [0.5.4] - 2026-01-10

### Added
- File registry initial implementation
- Data file detection
- Documentation updates

## [0.5.0] - 2025-12-15

### Added
- Planning & Foundation milestone
- GraphQL API
- Documentation enforcement
- Priority tracking

## [0.4.0] - 2025-11-30

### Added
- Core IdlerGear functionality
- Task management
- Note management
- Vision and plan support

---

## Upgrade Guide

### Upgrading to v0.6.0

**New Features Available:**
1. **File Registry** - Start tracking deprecated files:
   ```bash
   idlergear file deprecate old_data.csv --successor new_data.csv
   ```

2. **File Annotations** - Annotate files for efficient discovery:
   ```bash
   idlergear file annotate src/api/auth.py \
     --description "REST API endpoints for authentication" \
     --tags api,auth,jwt
   ```

3. **Multi-Agent Coordination** - Enable daemon for coordination:
   ```bash
   idlergear daemon start
   ```

**Breaking Changes:**
- None. v0.6.0 is fully backward compatible.

**Deprecations:**
- None.

---

## Links

- [GitHub Repository](https://github.com/marctjones/idlergear)
- [Documentation](https://github.com/marctjones/idlergear/blob/main/README.md)
- [Issue Tracker](https://github.com/marctjones/idlergear/issues)
- [Release Notes](https://github.com/marctjones/idlergear/releases)

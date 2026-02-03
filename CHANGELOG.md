# Changelog

All notable changes to IdlerGear will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.0] - 2026-02-02

### Added

**Multi-Language Code Parsing (#400)**
- Tree-sitter integration for Python, JavaScript, TypeScript, Rust, Go, C/C++, Java
- Docstring extraction from Python functions, classes, and methods
- Fully qualified method names (e.g., `Greeter.greet`) in symbol extraction
- Error-tolerant parsing (handles syntax errors gracefully)
- Language detection from file extensions

**Vector Embeddings & Semantic Code Search (#401)**
- ChromaDB integration for code symbol embeddings
- Semantic code search with natural language queries
- MCP tools: `idlergear_code_search`, `idlergear_find_similar_code`
- 93-98% token savings vs grep + file reading
- Sub-second query performance
- Duplicate code detection via similarity search

**LlamaIndex RAG for Documentation (#402)**
- Semantic search over references and notes using LlamaIndex
- Local embeddings (sentence-transformers) - zero-config operation
- Optional OpenAI embeddings for better quality
- MCP tools: `idlergear_rag_search`, `idlergear_rag_index_all`, `idlergear_rag_rebuild`
- CLI commands: `rag-search`, `rag-index`, `rag-rebuild`
- 90%+ token savings vs reading all documentation
- Metadata filtering (search only references or only notes)

**Test Coverage**
- Comprehensive tests for tree-sitter parsing
- Tests for vector code search
- Tests for LlamaIndex RAG plugin
- All tests gracefully handle optional dependencies

### Changed

- **BREAKING**: Removed AST parsing fallback - tree-sitter is now the primary parser
- Updated plan display formatter for Plan Objects API (uses `description`, `status` fields)
- Updated search module for Plan Objects compatibility
- Refactored code_populator.py - removed `_extract_symbols_and_imports` method
- Updated pyproject.toml with new optional dependencies (`rag` extra)

### Fixed

- Fixed 39 test failures related to Plan Objects API changes
- Fixed KuzuDB schema error - created `PR_MODIFIES` as separate relationship table
- Fixed plan CLI tests to use new `--description` parameter requirement
- Fixed search.py to use correct Plan Objects field names
- Fixed display.py plan formatter to show correct fields
- Fixed tmux integration bug (deprecated `Server.find_where()` API)
- Fixed file annotation persistence bug (one-file-per-annotation storage)

### Performance

- **Code Search**: 93-98% token savings (vs grep + file reads)
- **Documentation Search**: 90%+ token savings (vs reading all docs)
- **Knowledge Graph**: 95-98% token savings (vs file reads)
- **Query Speed**: Sub-second response times for all semantic searches
- **Indexing Speed**: ~60 seconds for 10K LOC codebase

### Dependencies

**New Required Dependencies:**
- `tree-sitter>=0.21.0,<0.22.0` - Multi-language parsing
- `tree-sitter-languages>=1.10.0` - Language grammars
- `chromadb>=0.4.22` - Vector database for code search
- `sentence-transformers>=2.2.0` - Local embeddings

**New Optional Dependencies:**
- `llama-index>=0.11.0` - RAG for documentation (install with `[rag]`)
- `llama-index-embeddings-huggingface>=0.3.0` - Local embeddings for RAG
- `llama-index-embeddings-openai>=0.2.0` - OpenAI embeddings option

### Documentation

- Updated CLAUDE.md with RAG usage guide
- Added semantic search architecture explanation
- Documented token savings comparisons
- Added configuration examples for RAG

---

## [0.7.x] - 2026-01-25

### Added - Session Management Advanced
- **Session Branching** - Git-like branching for experimental work (#273)
  - Create branches from any session with purpose/reason tracking
  - Switch between branches with `checkout`
  - Compare branches with detailed diff (files, tasks, duration)
  - Merge successful experiments back to main
  - Abandon failed experiments with documentation
  - Delete merged/abandoned branches
  - Full session lineage tracking with parent pointers
  - Branch metadata: status (active/merged/abandoned), created, forked_from
- **Knowledge Harvesting** - Extract insights from completed sessions (#274)
  - Harvest single session: tasks completed, focus areas, tool usage
  - Identify patterns across multiple sessions (days/weeks)
  - Save harvested insights as notes with tags
  - Insight types: achievement, focus_area, tool_pattern, success_pattern, learning
  - Pattern analysis: success rates, common directories, tool preferences, avg duration
  - Integration with session branching for experiment comparison
- **Session Analytics** - Deep session efficiency analysis (#275)
  - Productivity metrics and efficiency scoring
  - Tool usage analysis and recommendations
  - Task completion rate tracking
  - File change pattern identification
  - Session duration statistics
- **Container Support** - Isolated process execution (#325)
  - Podman and Docker support with unified API
  - Resource limits: memory and CPU constraints
  - Environment variable injection
  - Volume mounting for workspace access
  - Container lifecycle management (start, stop, remove, logs, stats)
  - Integration with run system for task-aware containers
  - Containerized testing infrastructure (Containerfiles for install/build)
  - Test matrix script: Python 3.10, 3.11, 3.12

### Added - CLI Commands
Session management commands:
- `idlergear session branch` - Create experimental branch
- `idlergear session checkout` - Switch to branch
- `idlergear session branches` - List all branches
- `idlergear session diff` - Compare two branches
- `idlergear session merge` - Merge branch into target
- `idlergear session abandon` - Mark branch as abandoned
- `idlergear session delete-branch` - Delete branch
- `idlergear session harvest` - Extract insights from session(s)
- `idlergear session analyze` - Deep efficiency analysis

Container run enhancements:
- `idlergear run start --container` - Run in container
- `--image`, `--memory`, `--cpus` - Container resource options
- `--env` - Environment variable injection

### Added - Infrastructure
- **Tmux Integration** - Terminal multiplexer support for persistent sessions (#327)
- **Test Infrastructure** - Containerized testing
  - `containers/test-install.Containerfile` - Clean environment install testing
  - `containers/test-build.Containerfile` - Build process validation
  - `scripts/podman-test.sh` - Test runner (install/build/matrix)

### Added - Documentation
- Wiki pages for v0.8.0 features
  - Session Branching guide with use cases and best practices
  - Knowledge Harvesting guide with insight types and workflows
  - Container Support guide with resource limits and examples
- Updated README.md, AGENTS.md, SKILL.md for v0.8.0
- Updated wiki Home.md with v0.8.0 release notes

### Fixed
- Session history snapshot loading edge cases
- Container runtime detection priority (Podman first, Docker fallback)

### Improved
- Session metadata tracking with parent/child relationships
- ProcessManager abstraction for containers
- Run system integration with container lifecycle

## [0.7.0] - 2026-01-24

### Added - GitHub Projects Integration
- **GitHub Projects v2 Sync** - Bidirectional project board integration (#320, #257)
  - Create and manage Kanban boards locally
  - Sync to/from GitHub Projects v2
  - Link existing GitHub Projects to IdlerGear projects
  - Automatic task addition to default project (configurable)
  - Token-efficient project queries
- **Custom Field Sync** - Rich GitHub Projects metadata (#283)
  - Map IdlerGear task properties to GitHub custom fields
  - Supported field types: single-select (priority), date (due), text (labels)
  - Automatic sync on task create/update
  - Field validation and graceful failure handling
  - Configuration via `projects.field_mapping` in config.toml
- **Status Column Mapping** - Automatic task movement (#282)
  - Configure column mapping for task states (open → Backlog, in_progress → Doing, etc.)
  - Auto-move tasks when state changes
  - Configurable via `projects.column_mapping` in config.toml
- **Bidirectional Sync** - GitHub as source of truth (#284)
  - Pull changes from GitHub Projects to IdlerGear
  - Sync priority, due dates, labels, and issue status
  - Automatic task closure when GitHub issue closed
  - Conflict resolution: GitHub wins by default

### Added - GitHub Backend Enhancements
- **Vision Sync** - Copy vision to `VISION.md` in repo root (#319)
- **Reference Sync** - Sync references to GitHub Wiki (#318)
- **Plan Sync** - Sync plans to GitHub (#317)

### Added - CLI Commands
GitHub Projects commands:
- `idlergear project sync` - Sync project to GitHub Projects v2
- `idlergear project link` - Link to existing GitHub Project
- `idlergear project pull` - Pull changes from GitHub (bidirectional)

### Added - MCP Tools
- `idlergear_project_sync` - Sync project to GitHub
- `idlergear_project_link` - Link existing project
- `idlergear_project_pull` - Pull GitHub changes
- `idlergear_project_sync_fields` - Sync custom fields

### Added - Documentation
- GitHub Projects integration guide
- Custom field sync documentation
- Bidirectional sync workflow examples
- Project board automation guide

### Fixed
- GitHub Projects GraphQL query optimization
- Field type validation for custom fields
- Project board column detection

### Improved
- Token efficiency for project queries
- GitHub API error handling
- Project configuration schema

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

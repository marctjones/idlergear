---
id: 1
title: Refactoring Plan - Dead Code and Cleanup
created: '2026-01-12T15:50:33.243165Z'
updated: '2026-01-12T15:50:33.243232Z'
---
# IdlerGear Refactoring Plan

## Summary

Analysis of the codebase revealed:
- **6 dead code files** (0% coverage, not imported anywhere)
- **2 duplicate implementations** requiring consolidation
- **5 deprecated features** ready for removal
- **Total removable code**: ~1,000+ lines

---

## 1. DEAD CODE TO DELETE

These files have 0% test coverage AND are NOT imported anywhere in the codebase.

### 1.1 daemon_mcp_handlers.py (DELETE)
- **Location**: `src/idlergear/daemon_mcp_handlers.py`
- **Lines**: 112
- **Purpose**: MCP tool handlers for daemon coordination (older version)
- **Status**: NOT imported anywhere
- **Replaced by**: `daemon/mcp_handlers.py` (403 lines, imported by mcp_server.py)
- **Action**: DELETE - completely superseded by daemon/mcp_handlers.py

### 1.2 daemon_mcp_tools.py (DELETE)
- **Location**: `src/idlergear/daemon_mcp_tools.py`
- **Lines**: 221 (including Tool definitions)
- **Purpose**: MCP tool definitions for daemon
- **Status**: NOT imported anywhere
- **Action**: DELETE - tool definitions are in mcp_server.py

### 1.3 script_mcp_handlers.py (DELETE)
- **Location**: `src/idlergear/script_mcp_handlers.py`
- **Lines**: 180
- **Purpose**: MCP handlers for script generation
- **Status**: NOT imported anywhere (only imports script_generator.py)
- **Note**: script_generator.py IS used (imported by cli.py)
- **Action**: DELETE - handlers never wired up, script_generator remains

### 1.4 script_mcp_tools.py (DELETE)
- **Location**: `src/idlergear/script_mcp_tools.py`
- **Lines**: 131
- **Purpose**: MCP tool definitions for scripts
- **Status**: NOT imported anywhere
- **Action**: DELETE - tools never added to MCP server

### 1.5 goose.py (DELETE)
- **Location**: `src/idlergear/goose.py`
- **Lines**: 359
- **Purpose**: Goose AI assistant integration templates
- **Status**: NOT imported anywhere
- **Note**: Contains GOOSEHINTS_TEMPLATE and installation helpers
- **Action**: DELETE - incomplete feature, never integrated

### 1.6 otel.py (DELETE)
- **Location**: `src/idlergear/otel.py`
- **Lines**: 266
- **Purpose**: OpenTelemetry CLI commands (start/stop collector)
- **Status**: NOT imported anywhere
- **Note**: Uses otel_collector.py and otel_storage.py which ARE imported
- **Action**: DELETE - CLI commands never wired up

**Total Lines to Delete**: ~1,269 lines

---

## 2. DUPLICATE FILES TO CONSOLIDATE

### 2.1 Session Management Duplicate

**Files**:
- `session.py` (86 lines, 92% coverage) - Class-based implementation
- `sessions.py` (312 lines, 0% coverage) - Dataclass-based implementation

**Analysis**:
- Both files are imported (session.py by cli.py and mcp_server.py)
- sessions.py is imported by cli.py only
- Different approaches: session.py uses class, sessions.py uses dataclasses
- session.py is simpler and better tested

**Recommendation**: 
1. Review if sessions.py has features not in session.py
2. Merge any unique features into session.py
3. DELETE sessions.py (312 lines savings)
4. Update cli.py imports

### 2.2 Daemon MCP Handlers Duplicate (Resolved in Section 1)

**Files**:
- `daemon_mcp_handlers.py` (112 lines, 0% coverage) - Older version
- `daemon/mcp_handlers.py` (403 lines, 0% coverage) - Newer version with auto-start

**Analysis**:
- daemon/mcp_handlers.py IS imported by mcp_server.py
- daemon_mcp_handlers.py is NOT imported anywhere
- daemon/mcp_handlers.py has more features (auto-start, presence files)

**Action**: Already covered - DELETE daemon_mcp_handlers.py

---

## 3. DEPRECATED FEATURES TO REMOVE

### 3.1 --verbose Flag (cli.py:236)

```python
False, "--verbose", "-v", help="Include more detail (deprecated, use --mode)"
```

**Current State**: Deprecated but still functional
**Action**: Remove flag and associated handler code (cli.py:289)
**Impact**: Users must use `--mode standard` instead of `-v`

### 3.2 Exploration Tools (mcp_server.py:376-398)

Three deprecated MCP tools:
- `idlergear_explore_create` → Use `idlergear_note_create` with tags=['explore']
- `idlergear_explore_list` → Use `idlergear_note_list` with tag='explore'
- `idlergear_explore_delete` → Use `idlergear_note_delete`

**Current State**: Still functional, marked DEPRECATED in descriptions
**Action**: Remove tool definitions and handlers
**Impact**: Users must switch to note-based exploration

### 3.3 Explore CLI Commands (cli.py:2661+)

```python
# Explore commands (deprecated - now aliases for notes with --tag explore)
```

**Current State**: Commands work but redirect to notes
**Action**: Remove explore subcommand group
**Impact**: Users must use `idlergear note` commands

---

## 4. REFACTORING RECOMMENDATIONS

### 4.1 Module Organization

The daemon functionality is split across:
- `daemon/` directory (proper module structure)
- `daemon_mcp_handlers.py` (dead, DELETE)
- `daemon_mcp_tools.py` (dead, DELETE)

**After cleanup**: All daemon code in `daemon/` directory - cleaner structure

### 4.2 Code Coverage Blockers

Two files block overall 90% coverage:
- `cli.py` (3,465 lines, 26% coverage) - 100+ CLI commands
- `mcp_server.py` (1,030 lines, 30% coverage) - 50+ MCP handlers

**Recommendation**: 
- These are hard to test comprehensively
- Focus on testing critical paths
- Accept ~70-80% overall coverage as realistic target

### 4.3 Test Infrastructure

Low-coverage but actively used files:
- `sessions.py` (0% coverage) - May be removed (see 2.1)
- `hooks.py` (0% coverage) - Shell hook management
- `watch.py` (has MCP tools) - Needs tests
- `process_manager.py` - NOT imported, potential dead code

---

## 5. IMPLEMENTATION ORDER

### Phase 1: Delete Dead Code (Low Risk)
1. DELETE daemon_mcp_handlers.py
2. DELETE daemon_mcp_tools.py  
3. DELETE script_mcp_handlers.py
4. DELETE script_mcp_tools.py
5. DELETE goose.py
6. DELETE otel.py
7. Run tests to confirm no breakage

### Phase 2: Consolidate Duplicates (Medium Risk)
1. Review sessions.py vs session.py feature parity
2. Merge any unique features
3. DELETE sessions.py
4. Update cli.py imports
5. Run tests

### Phase 3: Remove Deprecated Features (User Impact)
1. Remove --verbose flag from cli.py
2. Remove explore MCP tools from mcp_server.py  
3. Remove explore CLI commands from cli.py
4. Update documentation
5. Add migration note to changelog

---

## 6. ESTIMATED IMPACT

| Action | Lines Removed | Risk |
|--------|---------------|------|
| Delete dead code (6 files) | ~1,269 | Low |
| Consolidate sessions | ~312 | Medium |
| Remove deprecated | ~100 | Medium (user impact) |
| **Total** | **~1,681** | - |

This represents approximately 10% of the codebase being cleanly removed.

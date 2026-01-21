---
id: 40
title: Build idlergear env MCP server + integrate existing system/process tools
state: open
created: '2026-01-07T01:48:11.327537Z'
labels:
- enhancement
- mcp
- system
- goose
priority: medium
---
## Research Complete: MIXED APPROACH - Integrate + Build Gaps

Research (Task #44, Note #10) found excellent servers for system monitoring and process management, but a GAP exists for developer environment detection.

## Recommendation: Integrate Existing

### 1. **pm-mcp** (Process Management) - INTEGRATE
- 7 tools for managing long-running processes
- Perfect for dev servers, build processes, background tasks
- Log capture, search, interactive input
- **Action**: Document in .goosehints, recommend to users

### 2. **mcp-system-monitor** (System Metrics) - INTEGRATE
- 8 tools for CPU, memory, disk, network, processes
- JSON-RPC 2.0 structured output
- **Limitation**: Linux-only
- **Action**: Optional dependency, document for Linux users

### 3. **mcp-package-version** (Package Versions) - INTEGRATE
- Check latest stable versions (npm, PyPI)
- **Action**: Recommend for version checking

## Build This: idlergear env MCP Server

**GAP IDENTIFIED**: No existing server provides developer environment detection.

### Tools to Implement (4 core tools)

1. **idlergear_env.info()**
   - Consolidated environment snapshot
   - Python/Node/Rust/Go versions
   - Active virtual environment
   - Package manager versions
   - PATH entries
   - **Output**: Clean JSON structure
   - **Token savings**: 60% vs multiple commands

2. **idlergear_env.which(command)**
   - Enhanced `which` replacement
   - Shows ALL PATH matches (not just first)
   - Indicates source (venv, system, nvm, etc.)
   - Includes version for each match
   - **Output**: Array of matches with metadata

3. **idlergear_env.detect()**
   - Detect project type (Python, Node, Rust, Go, etc.)
   - Find version managers (nvm, pyenv, rbenv, etc.)
   - Identify virtual environments
   - Return environment requirements
   - **Output**: Project environment profile

4. **idlergear_env.activate()**
   - Auto-detect virtual environment
   - Return activation commands
   - Modify PATH for session
   - **Output**: Activation status + commands

### Why Build This?

**Fills a Real Gap:**
- Existing servers: **System monitoring** (CPU, memory, processes)
- IdlerGear needs: **Development environment awareness** (venvs, versions, PATH)
- Lightweight (~500 LOC), high-value, missing from ecosystem

**Developer-Specific Use Case:**
- Goose/Claude Code constantly run `which python && python --version`
- With idlergear_env.info(): Single call, structured output, 60% token reduction
- Critical for understanding project environment

### Implementation Details

**Language**: Python (native subprocess, shutil, os support)
**Complexity**: Simple (~500 lines)
**Dependencies**: Standard library only (subprocess, shutil, os, json, pathlib)

**Structure:**
```
idlergear/mcp/env/
├── __init__.py
├── server.py      # MCP server implementation
├── detectors.py   # Python/Node/Rust version detection
├── venv.py        # Virtual environment detection
└── which.py       # Enhanced which command
```

## Token Savings Example

**Before (multiple commands):**
```bash
which python && python --version  # 50 tokens output
which node && node --version      # 50 tokens output
env | grep PATH                   # 100 tokens output
Total: ~200 tokens
```

**After (single MCP call):**
```python
idlergear_env.info()
# Returns structured JSON: ~80 tokens
# 60% reduction!
```

## Implementation Plan

**Phase 1: Integration (Quick Wins)**
1. Document pm-mcp in .goosehints template
2. Document mcp-system-monitor (Linux users)
3. Add recommended MCP servers to README

**Phase 2: Build idlergear env**
1. Implement core 4 tools (info, which, detect, activate)
2. Python-based, standard library only
3. Clean JSON structured outputs
4. Unit tests for cross-platform compatibility

**Phase 3: Polish**
1. Add to IdlerGear CLI: `idlergear mcp env --start`
2. Auto-configure in .mcp.json
3. Documentation and examples

See Note #10 for complete research findings.

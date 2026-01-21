---
id: 1
title: 'Design: External Terminal Run Tracking (ig run)'
created: '2026-01-17T16:42:59.456736Z'
updated: '2026-01-17T16:42:59.456755Z'
---
---
name: ig-run
title: External Terminal Run Tracking (ig run)
state: active
created: '2026-01-11T08:25:41.148364Z'
---
# Implementation Plan: `ig run` for External Terminal Tracking

## Overview

Add a user-facing command wrapper that tracks script execution from external terminals, providing AI assistants with structured visibility into what ran, when, and with what version.

## Problem Statement

When users run scripts in a separate terminal from the AI assistant:
- AI has no context about WHEN the command ran
- No way to verify WHICH VERSION of a script was executed
- Output may be truncated or stale when copy-pasted
- Logs aren't programmatically accessible

## Design Decision

**Approach: Option A with Header/Footer** (from design note #34)
- Wrapper script that executes commands with metadata output
- Integrates with existing `runs.py` infrastructure
- Optional daemon/OTEL streaming for real-time visibility

---

## Phase 1: Core `ig run` Command

### 1.1 Create `ig` CLI Entry Point
- New lightweight CLI specifically for user-facing terminal commands
- Entry point: `ig` (short alias for common operations)
- Implemented in `src/idlergear/ig_cli.py`

**Commands:**
```bash
ig run <command>           # Execute with tracking
ig run --name <name> <cmd> # Named run
ig run --quiet <cmd>       # Suppress header/footer
ig run status              # Show recent runs
ig run logs <name>         # View logs
```

### 1.2 Script Hash Calculation
- Add `calculate_script_hash()` to `runs.py`
- SHA256 of file contents for script files
- SHA256 of command string for inline commands
- First 8 chars displayed as version identifier

### 1.3 Header/Footer Output
- Structured banner before execution with:
  - Run ID (unique identifier)
  - Script path and hash
  - Timestamp (ISO format)
  - Log streaming status
- Footer after execution with:
  - Exit code
  - Duration
  - Log file location

### 1.4 PTY Passthrough
- Use `pty` module for proper terminal handling
- Preserve colors, interactive prompts
- Tee output to log files while displaying

---

## Phase 2: Enhanced Run Metadata

### 2.1 Extended Run Storage
Update `.idlergear/runs/<name>/` structure:
```
command.txt      # Command executed
pid              # Process ID
status.txt       # Status and timestamps
stdout.log       # Standard output
stderr.log       # Standard error
metadata.json    # NEW: Extended metadata
```

**metadata.json schema:**
```json
{
  "id": "run_abc12345",
  "command": "./train.sh",
  "script_path": "/path/to/train.sh",
  "script_hash": "sha256:a1b2c3d4...",
  "started_at": "2026-01-11T04:30:00Z",
  "completed_at": "2026-01-11T04:45:00Z",
  "exit_code": 0,
  "duration_seconds": 900,
  "terminal": "external",
  "streaming": false
}
```

### 2.2 Update MCP Tools
Enhance existing tools to expose new metadata:
- `idlergear_run_list()` - Include hash, terminal type
- `idlergear_run_status()` - Include full metadata
- `idlergear_run_logs()` - No changes needed

---

## Phase 3: Daemon Integration

### 3.1 Real-time Log Streaming
- `ig run --stream` flag for daemon integration
- Stream logs to OTEL collector via daemon
- AI can query logs in real-time

### 3.2 Run Registration
- Register external runs with daemon
- Visible in `idlergear daemon agents`
- Status updates (running → completed/failed)

### 3.3 Graceful Degradation
- Work without daemon (local-only mode)
- Warning message if --stream requested but daemon unavailable
- All features work except real-time streaming

---

## Phase 4: Polish and Integration

### 4.1 Quiet Mode
- `ig run --quiet` suppresses header/footer
- Still logs to files and registers with daemon
- Useful for scripts that parse their own output

### 4.2 History Commands
```bash
ig run history              # Recent runs with status
ig run history --failed     # Only failed runs
ig run clean                # Clean old run logs
```

### 4.3 Documentation
- Update AGENTS.md with `ig run` usage
- Add to skill references
- Example workflows in README

---

## Files to Create/Modify

**New Files:**
- `src/idlergear/ig_cli.py` - Lightweight `ig` CLI
- `src/idlergear/pty_runner.py` - PTY execution wrapper
- `tests/test_ig_cli.py` - Tests for ig CLI
- `tests/test_pty_runner.py` - Tests for PTY runner

**Modified Files:**
- `src/idlergear/runs.py` - Add hash calculation, metadata
- `src/idlergear/mcp_server.py` - Enhanced run tools
- `pyproject.toml` - Add `ig` entry point

---

## Success Criteria

1. User can run `ig run ./script.sh` and see structured output
2. AI can query run metadata including script hash
3. Copy-pasted output includes identifiable run context
4. Optional streaming works with daemon
5. Works gracefully without daemon

---

## Open Questions (Resolved)

1. ~~Should this be `ig run` or `idlergear run-external`?~~
   → `ig run` - shorter for frequent use in external terminal

2. ~~How to handle interactive commands?~~
   → PTY passthrough preserves interactivity

3. ~~Header/footer configurable?~~
   → Yes, `--quiet` flag suppresses them

4. ~~Daemon not running?~~
   → Graceful degradation, local-only mode

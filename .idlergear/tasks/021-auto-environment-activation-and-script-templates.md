---
id: 21
title: Auto-environment activation and script templates for long-running processes
state: closed
created: '2026-01-03T05:58:02.216223Z'
labels:
- enhancement
- 'effort: medium'
- 'component: run'
- core-v1
priority: high
---
## Summary

Enhance `idlergear run` to automatically activate development environments (venv, conda, nvm) and provide script templates for long-running processes that register with the daemon for efficient monitoring.

## Problem

When running long processes (tests, builds, training):
1. Need to **manually activate dev environments** each time
2. Claude Code doesn't know **when to use separate terminal** vs direct execution
3. No **standardized pattern** for registering processes with daemon
4. **Inefficient monitoring** - requires polling logs instead of event-based updates

## Proposed Solution

### 1. Auto-Environment Detection and Activation

```bash
# New flag: --auto-env
idlergear run start "pytest tests/" --name tests --auto-env

# Automatically detects and activates:
# - Python: venv/bin/activate
# - Node.js: nvm use
# - Conda: conda activate
# - Ruby: rbenv local
```

### 2. Script Template System

```bash
# Generate a script with environment setup
idlergear run create-script test-suite \
    --command "pytest tests/ -v --cov=src" \
    --output scripts/run_tests.sh

# Creates scripts/run_tests.sh with:
# - Auto-detect and activate venv
# - Register with daemon
# - Cleanup on exit
# - Log to .idlergear/logs/test-suite.log
```

### 3. CLAUDE.md Guidance

Add "Long-Running Process Policy" to CLAUDE.md:
- NEVER run long-running processes (>30s) via Bash tool directly
- Use `idlergear run create-script` or `idlergear run start`
- Clear distinction between short (<30s) and long processes

### 4. Efficient Log Monitoring

Use **inotify** (Linux) or **FSEvents** (macOS) for event-based log watching:
- No polling required
- Only read new lines (track file offset)
- Daemon emits updates to interested sessions

### 5. Enhanced Status Command

```bash
# Shows last 10 log lines
idlergear run status test-suite

# Stream logs live
idlergear run logs test-suite --follow
```

## Example Workflow

**User:** "Run the full test suite"

**Claude Code:**
1. Creates `scripts/run_tests.sh` with auto-environment activation
2. Tells user: "Run this in a separate terminal: `./scripts/run_tests.sh`"

**Script automatically:**
- Activates venv/conda/nvm based on project files
- Registers with daemon (PID, log path)
- Captures logs to `.idlergear/logs/test-suite.log`
- Cleans up on exit

**User can monitor:**
```bash
idlergear run status test-suite    # Check status + last 10 log lines
idlergear run logs test-suite --follow  # Live stream
```

## Implementation Plan

### Phase 1: Environment Auto-Detection
- [ ] Implement `detect_environment()` function
- [ ] Support Python venv detection (venv, .venv, env)
- [ ] Support Node.js nvm detection (.nvmrc)
- [ ] Support Conda environment detection (environment.yml)
- [ ] Support Ruby rbenv detection (.ruby-version)
- [ ] Add `--auto-env` flag to `run start`
- [ ] Add config: `run.auto_activate_env = true`

### Phase 2: Script Templates
- [ ] Create `templates/run_script.sh` template
- [ ] Implement `idlergear run create-script` command
- [ ] Template variable substitution ({{name}}, {{command}}, {{env_activate}})
- [ ] Auto-detect environment for template
- [ ] Make generated script executable (`chmod +x`)

### Phase 3: Efficient Log Monitoring
- [ ] Add `watchdog` dependency (inotify/FSEvents wrapper)
- [ ] Implement `LogWatcher` class in daemon
- [ ] Track file offsets (read only new lines)
- [ ] Integrate with daemon startup
- [ ] Emit log updates to MCP subscribers

### Phase 4: Enhanced Status
- [ ] `idlergear run status <name>` shows last N log lines
- [ ] Add `--tail <n>` flag (default: 10)
- [ ] Add `--follow` flag for live streaming
- [ ] MCP tool returns structured status with logs

### Phase 5: CLAUDE.md + Hook Integration
- [ ] Add "Long-Running Process Policy" to CLAUDE.md template
- [ ] Implement UserPromptSubmit hook for keyword detection
- [ ] Update MCP tool descriptions with guidance
- [ ] Add examples to AGENTS.md

## Configuration

```toml
# .idlergear/config.toml
[run]
auto_activate_env = true  # Default: auto-detect and activate
log_dir = ".idlergear/logs"

[run.env]
# Environment detection order
detection_order = ["venv", "conda", "nvm", "rbenv"]

# Python
python_venv_paths = ["venv", ".venv", "env"]

# Node.js
node_version_file = ".nvmrc"

# Conda
conda_env_file = "environment.yml"

# Ruby
ruby_version_file = ".ruby-version"
```

## Benefits

1. ✅ **No manual environment setup** - Auto-detects and activates
2. ✅ **Standardized pattern** - Templates ensure consistency
3. ✅ **Efficient monitoring** - Event-based, not polling
4. ✅ **Session independence** - Processes survive Claude restarts
5. ✅ **Clear guidance** - Claude knows when to use separate terminal
6. ✅ **User-friendly** - Simple commands, clear output

## Related Issues

- #19 - Daemon-based prompt queue (uses run system)
- #112 - Watch mode (can trigger run scripts)
- #113 - Status command (includes run status)
- #66 - Unified daemon architecture (run monitoring)

## Reference Documents

- "Shell Script Pattern for Long-Running Processes" - Complete implementation guide

## Acceptance Criteria

- [ ] `idlergear run start --auto-env` detects and activates venv
- [ ] `idlergear run create-script` generates working script
- [ ] Generated scripts auto-register with daemon
- [ ] Log monitoring uses inotify/FSEvents (no polling)
- [ ] `idlergear run status <name>` shows last 10 log lines
- [ ] `idlergear run logs <name> --follow` streams logs in real-time
- [ ] CLAUDE.md includes long-running process policy
- [ ] UserPromptSubmit hook detects long-running process keywords
- [ ] MCP tool descriptions updated with usage guidance
- [ ] Works with Python (venv), Node.js (nvm), Conda, Ruby (rbenv)

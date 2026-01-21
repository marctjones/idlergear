---
id: 1
title: Shell Script Pattern for Long-Running Processes
created: '2026-01-03T05:51:15.551596Z'
updated: '2026-01-03T05:51:15.551607Z'
---
# IdlerGear Pattern: Long-Running Shell Scripts

## Problem

When Claude Code needs to run long-running processes (tests, builds, training, etc.), we want:
1. Run in a **separate terminal** (not blocking Claude session)
2. **Auto-activate dev environment** (venv, conda, nvm, etc.)
3. **Register with daemon** so IdlerGear can monitor status/logs
4. **Efficient monitoring** without polling

## Solution: Standardized Shell Script Pattern

### Script Template

```bash
#!/bin/bash
# scripts/run_training.sh - Example long-running script

set -euo pipefail

SCRIPT_NAME="training"
LOG_DIR=".idlergear/logs"
mkdir -p "$LOG_DIR"

# 1. Activate development environment
activate_env() {
    # Python venv
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✓ Activated Python venv"
    fi
    
    # Node.js (nvm)
    if [ -f ".nvmrc" ]; then
        nvm use
        echo "✓ Activated Node.js $(node --version)"
    fi
    
    # Conda
    if [ -n "${CONDA_DEFAULT_ENV:-}" ]; then
        conda activate "$CONDA_DEFAULT_ENV"
        echo "✓ Activated Conda env: $CONDA_DEFAULT_ENV"
    fi
}

# 2. Register with IdlerGear daemon
register_run() {
    idlergear run start \
        --name "$SCRIPT_NAME" \
        --command "$0 $*" \
        --log "$LOG_DIR/${SCRIPT_NAME}.log" \
        --pid $$ \
        --metadata "auto_registered=true"
    
    echo "✓ Registered with IdlerGear daemon (PID: $$)"
}

# 3. Cleanup on exit
cleanup() {
    EXIT_CODE=$?
    idlergear run complete "$SCRIPT_NAME" --exit-code $EXIT_CODE
    exit $EXIT_CODE
}
trap cleanup EXIT INT TERM

# Main execution
main() {
    echo "=== Starting $SCRIPT_NAME ==="
    
    activate_env
    register_run
    
    # Your actual work here
    python train_model.py --epochs 100
    
    echo "=== $SCRIPT_NAME completed ==="
}

# If run from IdlerGear daemon, main is already registered
if [ "${IDLERGEAR_RUN:-}" != "true" ]; then
    main "$@"
else
    # Just run the work, daemon already registered us
    python train_model.py --epochs 100
fi
```

### Usage Patterns

#### Pattern 1: Claude generates script, user runs manually
```bash
# Claude Code creates scripts/run_tests.sh
# User runs in separate terminal:
./scripts/run_tests.sh
```

#### Pattern 2: Claude uses `idlergear run` (daemon manages it)
```bash
# Claude Code:
idlergear run start "scripts/run_tests.sh" --name "test-suite"

# Daemon:
# - Activates env automatically
# - Captures logs
# - Registers in process table
# - User can check: idlergear run status test-suite
```

#### Pattern 3: User queues via daemon
```bash
# User in separate terminal:
idlergear queue add "run the full test suite"

# Claude Code session picks it up:
# - Creates/uses scripts/run_tests.sh
# - Registers with daemon
# - Runs in background
```

## How Claude Code Knows to Use Separate Terminal

### Option 1: CLAUDE.md Rules

Add to `CLAUDE.md`:

```markdown
## Long-Running Process Policy

**NEVER run long-running processes directly via Bash tool.**

Long-running processes (>30 seconds) should use this pattern:

1. **Create a shell script** in `scripts/` directory
2. **Use the script template** (see reference: Shell Script Pattern)
3. **Tell the user** to run it in a separate terminal:
   "I've created scripts/run_training.sh. Run this in a separate terminal:
   ./scripts/run_training.sh"

OR use daemon:

4. **Use idlergear run**: `idlergear run start scripts/run_training.sh --name training`

### What counts as "long-running"?
- Test suites (>30s)
- Build processes
- Training ML models
- Database migrations
- Large file processing
- Web servers / daemons

### Short processes (run directly via Bash):
- Quick tests (<30s)
- Git commands
- File operations
- Quick scripts
```

### Option 2: MCP Tool Enhancement

Enhance `run_start` MCP tool description:

```python
@mcp.tool()
def run_start(command: str, name: str = None):
    """
    Start a long-running process monitored by IdlerGear daemon.
    
    Use this for:
    - Test suites, builds, training
    - Any process >30 seconds
    - Processes that need separate terminal
    
    The daemon will:
    - Activate dev environment (venv, conda, nvm)
    - Capture logs to .idlergear/logs/
    - Monitor process status
    - Allow status checks: idlergear run status <name>
    
    Example:
        run_start("scripts/run_tests.sh", name="test-suite")
    """
```

### Option 3: Heuristic Detection

Add to `UserPromptSubmit` hook:

```bash
#!/bin/bash
# .claude/hooks/user-prompt-submit.sh

PROMPT=$(cat | jq -r '.prompt')

# Detect long-running process requests
if echo "$PROMPT" | grep -qiE "(run tests|build|train|benchmark|migration)"; then
    cat <<EOF
{
  "additionalContext": "LONG-RUNNING PROCESS DETECTED

This appears to be a long-running task. Use one of these patterns:

1. Create a script in scripts/ and tell user to run in separate terminal
2. Use: idlergear run start 'command' --name 'task-name'

The daemon will auto-activate dev environments and capture logs.
See reference: Shell Script Pattern for Long-Running Processes"
}
EOF
fi
```

## Dev Environment Auto-Detection

### idlergear run start --auto-env

```bash
# Automatically detect and activate environment
idlergear run start "pytest tests/" --name tests --auto-env

# Behind the scenes:
# 1. Detect environment type:
detect_env() {
    if [ -f "venv/bin/activate" ]; then
        echo "source venv/bin/activate"
    elif [ -f ".nvmrc" ]; then
        echo "nvm use"
    elif [ -f "environment.yml" ]; then
        echo "conda activate $(grep name: environment.yml | cut -d: -f2)"
    fi
}

# 2. Prepend activation to command:
ENV_ACTIVATE=$(detect_env)
FULL_CMD="$ENV_ACTIVATE && pytest tests/"

# 3. Run in subshell with env activated
bash -c "$FULL_CMD"
```

### Configuration

```toml
# .idlergear/config.toml
[run]
auto_activate_env = true  # Default: activate env automatically

[run.env]
# Environment detection order
detection_order = ["venv", "conda", "nvm", "rbenv"]

# Python
python_venv_paths = ["venv", ".venv", "env"]

# Node.js
node_version_file = ".nvmrc"

# Ruby
ruby_version_file = ".ruby-version"
```

## Daemon Process Monitoring

### Efficient Log Monitoring (No Polling)

Use `inotify` (Linux) or `FSEvents` (macOS) to watch log files:

```python
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class LogWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.log'):
            # Read new lines only (track file offset)
            self.read_new_lines(event.src_path)
    
    def read_new_lines(self, path):
        # Track last read position
        offset = self.offsets.get(path, 0)
        with open(path, 'r') as f:
            f.seek(offset)
            new_lines = f.readlines()
            self.offsets[path] = f.tell()
        
        # Emit new lines to interested sessions
        self.emit_log_update(path, new_lines)

# In daemon:
observer = Observer()
observer.schedule(LogWatcher(), path=".idlergear/logs", recursive=False)
observer.start()
```

### Status Checking

```bash
# Check status (daemon reads process table + log tail)
idlergear run status training

# Output:
# Name:     training
# Status:   running
# PID:      12345
# Uptime:   5m 23s
# Log:      .idlergear/logs/training.log (2.3 MB)
# Last 5 lines:
#   [INFO] Epoch 45/100 complete
#   [INFO] Loss: 0.0234
#   [INFO] Validation accuracy: 94.2%
#   [INFO] Checkpoint saved
#   [INFO] Epoch 46/100 starting...
```

### MCP Tool for Status

```python
@mcp.tool()
def run_status(name: str) -> dict:
    """
    Get status of a running process.
    
    Returns:
        {
            "name": "training",
            "status": "running",
            "pid": 12345,
            "uptime_seconds": 323,
            "log_path": ".idlergear/logs/training.log",
            "log_size_bytes": 2400000,
            "last_lines": ["Epoch 45/100...", ...]
        }
    """
```

## Complete Workflow Example

### User Request
"Run the full test suite"

### Claude Code Response

```
I'll create a script to run the full test suite with proper environment setup
and daemon registration.
```

*Creates `scripts/run_tests.sh`:*

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_NAME="test-suite"
LOG_DIR=".idlergear/logs"
mkdir -p "$LOG_DIR"

# Activate venv
source venv/bin/activate

# Register with daemon
idlergear run start \
    --name "$SCRIPT_NAME" \
    --command "$0" \
    --log "$LOG_DIR/${SCRIPT_NAME}.log" \
    --pid $$

# Cleanup on exit
trap 'idlergear run complete "$SCRIPT_NAME" --exit-code $?' EXIT

# Run tests
pytest tests/ -v --cov=src

echo "Tests complete! Check results with: idlergear run logs $SCRIPT_NAME"
```

*Claude Code message to user:*

```
I've created scripts/run_tests.sh which will:
- Activate the Python venv
- Register with IdlerGear daemon for monitoring
- Run the full test suite with coverage
- Log output to .idlergear/logs/test-suite.log

Run this in a separate terminal:
  ./scripts/run_tests.sh

Or queue it for background execution:
  idlergear run start scripts/run_tests.sh --name test-suite

Check status anytime with:
  idlergear run status test-suite
  idlergear run logs test-suite
```

## Advanced: Multiple Environments

```bash
# scripts/run_fullstack_tests.sh

activate_backend() {
    cd backend
    source venv/bin/activate
    cd ..
}

activate_frontend() {
    cd frontend
    nvm use
    cd ..
}

# Register both processes
idlergear run start \
    "cd backend && source venv/bin/activate && pytest tests/" \
    --name "backend-tests"

idlergear run start \
    "cd frontend && nvm use && npm test" \
    --name "frontend-tests"

# Wait for both
idlergear run wait backend-tests frontend-tests
```

## Benefits

1. **No polling** - inotify/FSEvents for efficient log monitoring
2. **Auto-environment** - Scripts activate venv/conda/nvm automatically
3. **Process tracking** - Daemon knows what's running, can report status
4. **Log aggregation** - All logs in `.idlergear/logs/`
5. **Session independence** - Processes survive Claude Code restart
6. **Cross-session visibility** - Any Claude session can check status
7. **User-friendly** - Clear instructions to run in separate terminal

## Implementation Checklist

- [ ] Script template in templates/run_script.sh
- [ ] `idlergear run start --auto-env` flag
- [ ] Environment detection (venv, conda, nvm)
- [ ] Log file watching (inotify/FSEvents)
- [ ] `idlergear run status` shows last N log lines
- [ ] `idlergear run logs <name>` streams log output
- [ ] MCP tool: run_status(name)
- [ ] CLAUDE.md: Long-running process policy
- [ ] UserPromptSubmit hook: detect long-running requests

---
id: 1
title: Script Generation and Daemon Integration
created: '2026-01-07T05:28:28.078524Z'
updated: '2026-01-07T05:28:28.078539Z'
---
# Script Generation and Daemon Integration

## Overview

IdlerGear provides powerful tools for generating shell scripts that automatically integrate with the daemon for multi-agent coordination. This enables processes running in separate terminals to stay coordinated with AI assistants.

## Use Cases

### When to Generate Scripts

1. **Long-running dev servers** (Django, Flask, FastAPI)
2. **Test runners** that you want to monitor from multiple terminals
3. **Background workers** (Celery, cron jobs)
4. **Data processing pipelines**
5. **Any process that should coordinate with AI agents**

### Benefits

- **Auto-registration**: Script registers as an agent with the daemon
- **Log streaming**: Optionally stream logs to daemon for AI visibility
- **Coordination helpers**: Built-in functions for messaging and status updates
- **Environment setup**: Virtualenv, dependencies, env vars handled automatically
- **Clean exit**: Auto-unregisters from daemon on script termination

## CLI Commands

### 1. Generate Custom Script

```bash
idlergear run generate-script <name> <command> [OPTIONS]
```

**Options:**
- `--output, -o PATH` - Output file path (default: ./scripts/{name}.sh)
- `--venv PATH` - Virtualenv to activate
- `--requirement, -r PKG` - Python package to install (repeatable)
- `--env, -e KEY=VALUE` - Environment variable (repeatable)
- `--stream-logs` - Enable log streaming to daemon
- `--no-register` - Don't register with daemon
- `--agent-name NAME` - Custom agent name
- `--agent-type TYPE` - Agent type (default: dev-script)

**Examples:**

```bash
# Django dev server
idlergear run generate-script django-dev "python manage.py runserver" \
    --venv ./venv \
    --requirement django \
    --env DJANGO_SETTINGS_MODULE=settings \
    --stream-logs

# Pytest with coverage
idlergear run generate-script test "pytest -v --cov" \
    --requirement pytest \
    --requirement pytest-cov

# Celery worker
idlergear run generate-script worker "celery -A app worker" \
    --venv ./venv \
    --requirement celery \
    --env CELERY_BROKER_URL=redis://localhost:6379
```

### 2. Generate from Template

```bash
idlergear run generate-script <name> <command> --template <template>
```

**Available Templates:**
- `pytest` - Pre-configured test runner
- `django-dev` - Django development server
- `flask-dev` - Flask development server
- `jupyter` - Jupyter Lab
- `fastapi-dev` - FastAPI with uvicorn

**Examples:**

```bash
# Pytest runner
idlergear run generate-script test "pytest -v" --template pytest

# Django dev
idlergear run generate-script dev "python manage.py runserver" --template django-dev

# FastAPI
idlergear run generate-script api "uvicorn main:app" --template fastapi-dev
```

### 3. Run Process with Daemon Integration

```bash
idlergear run start <command> [--name NAME]
```

By default, runs now auto-register with the daemon. Control this with:

```python
# In code:
start_run(command, register_with_daemon=True, stream_logs=False)
```

## Generated Script Features

Every generated script includes:

### 1. Environment Setup

```bash
# Virtualenv activation
source ./venv/bin/activate

# Dependency installation
pip install -q pytest pytest-cov

# Environment variables
export DJANGO_SETTINGS_MODULE=settings
```

### 2. Daemon Registration

```bash
# Auto-registers with daemon
AGENT_ID=$(python3 -m idlergear.cli daemon register "$AGENT_NAME" \
    --type "$AGENT_TYPE" \
    --metadata "{\"script\": \"$SCRIPT_NAME\", \"pid\": $$}")

# Cleanup on exit
cleanup() {
    python3 -m idlergear.cli daemon unregister "$AGENT_ID"
}
trap cleanup EXIT INT TERM
```

### 3. Helper Functions

Scripts include built-in coordination functions:

```bash
# Send message to all agents
idlergear_send "Database migration complete"

# Log with daemon visibility
idlergear_log "Processing batch 5/10"

# Update agent status
idlergear_status "busy"  # or "idle", "active"
```

### 4. Optional Log Streaming

When `--stream-logs` is enabled:

```bash
# Streams stdout/stderr to daemon in real-time
# Other AI agents can see your logs via daemon
```

## Using Generated Scripts

### Run in Separate Terminal

```bash
# Terminal 1: Start IdlerGear daemon
idlergear daemon start

# Terminal 2: Run your generated script
./scripts/django-dev.sh

# Terminal 3: Claude Code session
# Can see the django-dev agent is running
idlergear daemon agents
```

### Coordination Flow

```
Terminal 1 (Script)          Daemon              Terminal 2 (AI Agent)
     │                         │                         │
     ├─register──────────────>│                         │
     │                         ├──agent_registered─────>│
     │                         │                         │
     ├─idlergear_log("...")──>│                         │
     │                         ├──log_event────────────>│
     │                         │                         │
     │                         │<──send_message─────────┤
     │<─receives broadcast─────┤                         │
```

## MCP Tools for AI Agents

### idlergear_script_generate

Generate a custom script from AI conversation:

```python
{
    "script_name": "test-runner",
    "command": "pytest -v --cov",
    "venv_path": "./venv",
    "requirements": ["pytest", "pytest-cov"],
    "env_vars": {"PYTHONPATH": "src"},
    "stream_logs": true
}
```

### idlergear_script_from_template

Generate from template:

```python
{
    "template": "django-dev",
    "script_name": "dev-server",
    "venv_path": "./venv",
    "env_vars": {"DJANGO_SETTINGS_MODULE": "settings"}
}
```

### idlergear_run_with_daemon

Start a background process with daemon integration:

```python
{
    "command": "celery -A app worker",
    "name": "celery-worker",
    "register": true,
    "stream_logs": false
}
```

## Real-World Workflow

### Scenario: Multi-Agent Web Development

**Setup:**

```bash
# Generate scripts for different processes
idlergear run generate-script backend "python manage.py runserver" \
    --template django-dev --stream-logs

idlergear run generate-script frontend "npm run dev" \
    --env NODE_ENV=development --stream-logs

idlergear run generate-script worker "celery -A app worker" \
    --requirement celery --stream-logs
```

**Usage:**

```bash
# Terminal 1: Daemon
idlergear daemon start

# Terminal 2: Backend
./scripts/backend.sh

# Terminal 3: Frontend
./scripts/frontend.sh

# Terminal 4: Worker
./scripts/worker.sh

# Terminal 5: Claude Code
# Can see all 3 processes, their logs, coordinate them
idlergear daemon agents

# Send message to all
idlergear daemon send "API schema changed, restart if needed"

# Check logs from any agent
idlergear daemon queue-list
```

## Implementation Details

### Files Created

- `src/idlergear/script_generator.py` - Core generation logic
- `src/idlergear/script_mcp_tools.py` - MCP tool definitions
- `src/idlergear/script_mcp_handlers.py` - MCP tool handlers
- Updates to `src/idlergear/runs.py` - Daemon integration
- Updates to `src/idlergear/cli.py` - CLI command

### Integration Points

**Runs System:**
```python
start_run(
    command,
    register_with_daemon=True,  # Auto-register
    stream_logs=False,          # Optional streaming
)
```

**Daemon Client:**
- `register_agent(name, agent_type, metadata)`
- `unregister_agent(agent_id)`
- `update_agent_status(agent_id, status)`
- `log_from_agent(agent_id, message, level)`

## Best Practices

1. **Always start daemon first**: `idlergear daemon start`
2. **Use templates when possible**: Less configuration needed
3. **Enable log streaming for long-running processes**: Better visibility
4. **Use coordination helpers**: Make multi-agent workflows explicit
5. **Clean shutdown**: Scripts auto-cleanup, but Ctrl+C works too

## Troubleshooting

**Script can't register with daemon:**
```bash
# Check daemon is running
idlergear daemon status

# Start daemon if needed
idlergear daemon start
```

**Logs not streaming:**
- Ensure `--stream-logs` was used during generation
- Check daemon is running
- Verify agent registered: `idlergear daemon agents`

**Script won't execute:**
```bash
# Make sure it's executable
chmod +x scripts/your-script.sh

# Check shebang line
head -1 scripts/your-script.sh  # Should be #!/bin/bash
```

## Next Steps

- Wire up MCP tools in `mcp_server.py`
- Add tests for multi-agent scenarios
- Create more templates (Rails, Next.js, etc.)
- Add script templates to `idlergear init`

# Complete IdlerGear Workflow: LLM-Assisted Development

**The Golden Path: From Zero to Production with AI Coding Assistants**

This document describes the complete workflow for creating a new project with full LLM coding assistant support, automated log management, multi-assistant collaboration, and best practices enforcement.

---

## Table of Contents

1. [Single Command Initialization](#single-command-initialization)
2. [What Gets Created](#what-gets-created)
3. [Multi-LLM Collaboration](#multi-llm-collaboration)
4. [Log Management Architecture](#log-management-architecture)
5. [Branch Management](#branch-management)
6. [Complete Example Workflow](#complete-example-workflow)
7. [Architecture Diagram](#architecture-diagram)

---

## Single Command Initialization

### The Magic Command

```bash
idlergear new my-awesome-app \
  --lang python \
  --llm-tools claude,gemini,copilot \
  --enable-logs \
  --enable-messaging
```

### What This Does (Behind the Scenes)

```
⏳ Creating project 'my-awesome-app'...

[1/12] Creating local directory
  ✓ Created: ~/projects/my-awesome-app/

[2/12] Initializing git repository
  ✓ Git initialized
  ✓ Created .gitignore (Python)

[3/12] Creating GitHub repository
  🌐 Connecting to GitHub...
  ✓ Created: github.com/marctjones/my-awesome-app (private)
  ✓ Remote 'origin' added
  ✓ Initial commit pushed

[4/12] Creating documentation for LLM assistants
  ✓ VISION.md - Project vision and goals
  ✓ DESIGN.md - Technical design and architecture
  ✓ TODO.md - Task tracking
  ✓ IDEAS.md - Future ideas / scope boundary
  ✓ DEVELOPMENT.md - Development practices
  ✓ AI_INSTRUCTIONS/README.md - Instructions for AI assistants
  ✓ AI_INSTRUCTIONS/SECRETS.md - Secret management guide
  ✓ AI_INSTRUCTIONS/TESTING.md - Testing requirements
  ✓ AI_INSTRUCTIONS/LOGGING.md - Logging best practices

[5/12] Setting up development environment
  ✓ Created Python venv: venv/
  ✓ Created requirements.txt
  ✓ Created requirements-dev.txt (pytest, black, flake8)
  ✓ Created .editorconfig
  ✓ Created .prettierrc (for docs)

[6/12] Installing development tools
  ✓ Installing pytest, coverage, black, flake8, mypy
  ✓ Installing python-dotenv (secret management)
  ✓ Installing structlog (structured logging)

[7/12] Setting up project structure
  ✓ src/ - Source code
  ✓ tests/ - Test suite
  ✓ docs/ - Additional documentation
  ✓ .idlergear/ - IdlerGear configuration
  ✓ .idlergear/logs/ - Local log storage
  ✓ .idlergear/messages/ - Message passing
  ✓ .idlergear/config.toml - Project configuration

[8/12] Setting up pre-commit hooks
  ✓ Created .pre-commit-config.yaml
  ✓ Installed pre-commit hooks
  ✓ Hooks: black, flake8, mypy, pytest

[9/12] Setting up log management
  ✓ Created log daemon configuration
  ✓ Started log collector service
  ✓ Log sources: stdout/stderr, OpenTelemetry, Splunk
  ✓ Log server: ~/.idlergear/log-daemon.sock

[10/12] Setting up message passing (eddi)
  ✓ Created eddi messaging server
  ✓ Server: /tmp/eddi-msgsrv-my-awesome-app.sock
  ✓ Tor hidden service: abc123def456.onion (30-60s to bootstrap)
  ✓ Generated connection codes for LLM assistants

[11/12] Creating initial project files
  ✓ src/__init__.py
  ✓ src/main.py (with structured logging)
  ✓ tests/test_main.py (example test)
  ✓ README.md
  ✓ LICENSE (MIT)
  ✓ .env.example (template for secrets)

[12/12] Final setup
  ✓ Running initial tests (1 passed)
  ✓ Committing initial structure
  ✓ Pushing to GitHub
  ✓ Creating coordination branch: idlergear-coord

✨ Project 'my-awesome-app' created successfully!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Enter project directory:
   cd my-awesome-app

2. Connect LLM coding assistants:

   🤖 Claude Code (Local):
   claude-code --mcp http://localhost:3000

   🌐 Claude Code Web:
   Connection code: TOR-ABC123
   Paste in web interface to connect to local environment

   🤖 Gemini CLI (Local):
   gemini --mcp http://localhost:3000

   🤖 GitHub Copilot CLI (Local):
   gh copilot configure --mcp http://localhost:3000

3. View project status:
   idlergear status

4. Start developing:
   idlergear tools launch claude
   # or
   idlergear tools launch gemini

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 SECRETS MANAGEMENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Create .env file for secrets (already in .gitignore):
cp .env.example .env
# Edit .env with your API keys, database credentials, etc.

Never commit .env to git!
LLM assistants will use python-dotenv to load secrets safely.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 LOG MANAGEMENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Log daemon running: ~/.idlergear/log-daemon.sock

All application logs are automatically collected and made
available to LLM assistants via:
- MCP server (local LLMs)
- eddi messaging (web LLMs)
- Git sync branches (async)

Configure remote log sources:
idlergear logs source add otel http://localhost:4317
idlergear logs source add splunk http://splunk:8088 --token <token>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## What Gets Created

### Directory Structure

```
my-awesome-app/
├── .git/                          # Git repository
├── .github/
│   └── workflows/
│       ├── ci.yml                 # CI/CD pipeline (pytest, coverage)
│       └── lint.yml               # Linting (black, flake8, mypy)
│
├── .idlergear/                    # IdlerGear configuration
│   ├── config.toml                # Project configuration
│   ├── logs/                      # Local log storage
│   │   ├── latest.log            # Most recent logs
│   │   ├── daemon.log            # Log daemon output
│   │   └── metadata.json         # Log metadata
│   ├── messages/                  # Message passing (git-based)
│   │   └── *.json                # Message files
│   └── mcp-config.json           # MCP server configuration
│
├── AI_INSTRUCTIONS/               # Instructions for AI assistants
│   ├── README.md                  # Main instructions
│   ├── ARCHITECTURE.md            # System architecture
│   ├── TESTING.md                 # Testing requirements (TDD)
│   ├── LOGGING.md                 # Logging best practices
│   ├── SECRETS.md                 # Secret management
│   ├── BRANCHING.md               # Git workflow
│   └── COLLABORATION.md           # Multi-LLM collaboration
│
├── src/                           # Source code
│   ├── __init__.py
│   ├── main.py                    # Entry point with logging
│   └── config.py                  # Configuration management
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_main.py               # Example tests
│   └── conftest.py                # Pytest configuration
│
├── docs/                          # Documentation
│   └── api.md                     # API documentation
│
├── venv/                          # Python virtual environment
│
├── .env.example                   # Template for secrets
├── .gitignore                     # Git ignore (includes .env)
├── .editorconfig                  # Editor configuration
├── .prettierrc                    # Prettier (for markdown)
├── .pre-commit-config.yaml        # Pre-commit hooks
│
├── VISION.md                      # Project vision
├── DESIGN.md                      # Technical design
├── TODO.md                        # Task tracking
├── IDEAS.md                       # Future ideas
├── DEVELOPMENT.md                 # Development practices
├── README.md                      # Project README
├── LICENSE                        # License (MIT)
│
├── requirements.txt               # Python dependencies
├── requirements-dev.txt           # Development dependencies
├── pytest.ini                     # Pytest configuration
├── setup.py                       # Package setup (optional)
└── pyproject.toml                 # Project metadata
```

### Key Files for LLM Assistants

#### `AI_INSTRUCTIONS/README.md`

```markdown
# Instructions for AI Coding Assistants

You are working on the **my-awesome-app** project.

## Project Context

**Vision:** [Auto-populated from VISION.md]

**Current Status:** [Auto-generated from git log, test coverage, etc.]

## Best Practices (REQUIRED)

1. **Test-Driven Development (TDD)**
   - Write tests BEFORE implementation
   - Run tests after every change: `pytest tests/ -v`
   - Maintain >80% code coverage: `pytest --cov=src tests/`

2. **Structured Logging**
   - Use structlog for all logging
   - Include context in log messages
   - Never log secrets or PII
   - Example:
     ```python
     import structlog
     log = structlog.get_logger()
     log.info("user_action", user_id=user_id, action="login")
     ```

3. **Secret Management**
   - NEVER hardcode secrets in code
   - Use .env file (never committed)
   - Load with python-dotenv: `load_dotenv()`
   - Example:
     ```python
     from dotenv import load_dotenv
     import os

     load_dotenv()
     api_key = os.getenv("API_KEY")
     ```

4. **Git Workflow**
   - Work on feature branches: `feature/<name>`
   - Commit frequently with clear messages
   - Run tests before committing
   - Create PRs for review
   - See AI_INSTRUCTIONS/BRANCHING.md

5. **Code Quality**
   - Format with black: `black src/ tests/`
   - Lint with flake8: `flake8 src/ tests/`
   - Type check with mypy: `mypy src/`
   - All enforced by pre-commit hooks

6. **Documentation**
   - Update README.md when adding features
   - Write docstrings for all functions
   - Update TODO.md as you complete tasks
   - Add complex decisions to DESIGN.md

## Available Tools

### Local Development (MCP Server)

If you're a local LLM tool (Claude Desktop, Gemini CLI, etc.):

```bash
# Access IdlerGear tools via MCP
project_status()        # Get project health
get_logs()              # Get recent application logs
run_tests()             # Run test suite
get_coverage()          # Get test coverage report
list_todos()            # Get current TODO items
```

### Web Development (eddi Messaging)

If you're a web LLM tool (Claude Code Web, Copilot Web, etc.):

**Connection Code:** TOR-ABC123

```bash
# Connect to local environment (one-time)
eddi-msgsrv connect --code TOR-ABC123 --namespace web@my-awesome-app --alias local

# Execute commands locally
eddi-msgsrv send "EXEC: pytest tests/ -v" --server local

# Get logs
eddi-msgsrv send "LOGS: show --errors-only" --server local

# Run app and stream output
eddi-msgsrv send "RUN: python -m src.main" --server local
```

### Git-Based Message Passing

To communicate with other LLM assistants:

```bash
# Send message to other assistants
idlergear message send --to web "Review the authentication module"

# Read messages from other assistants
idlergear message list --filter-to local

# Respond to message
idlergear message respond --id <msg-id> --body "Looks good!"
```

## Current Tasks

[Auto-populated from TODO.md]

## Recent Activity

[Auto-generated from git log --oneline -5]

## Test Coverage

[Auto-generated from coverage report]

## Recent Logs (Errors Only)

[Auto-populated from .idlergear/logs/latest.log]
```

#### `AI_INSTRUCTIONS/COLLABORATION.md`

```markdown
# Multi-LLM Collaboration Guide

This project may have multiple AI coding assistants working simultaneously.
Follow these guidelines to collaborate effectively.

## Active Assistants

This project is configured for:
- 🤖 Claude Code (local + web)
- 🤖 Gemini CLI (local)
- 🤖 GitHub Copilot CLI (local)

## Communication Channels

### 1. Git Commits (Primary)

- Commit messages are the main communication channel
- Write clear, descriptive commit messages
- Include context: "Fix login bug found by Gemini"

### 2. Message Passing (Real-Time)

Use message passing for coordination:

```bash
# Claude Code Web → Local Gemini
idlergear message send --to local "Can you review the auth tests?"

# Local Gemini → Claude Code Web
idlergear message respond --id <msg-id> --body "Tests look good, ready to merge"
```

### 3. Branch Comments (Design Discussion)

Use TODO.md and IDEAS.md for design discussions:

```markdown
## TODO: Implement caching layer

**Proposed by:** Claude (2025-11-18)
**Discussion:**
- Gemini: Consider Redis vs in-memory
- Copilot: Redis for production, in-memory for tests
- Claude: Agreed, will implement both
```

## Branch Ownership

### Rule: One assistant per feature branch

```
main
├── feature/auth-system (owned by Claude)
├── feature/caching (owned by Gemini)
└── feature/api-endpoints (owned by Copilot)
```

If you need to work on another assistant's branch:
1. Send message requesting review/collaboration
2. Wait for approval
3. Create sub-branch: `feature/auth-system-claude-review`
4. Submit PR to their branch, not main

## Merge Coordination

### Before Merging to Main

1. **Run full test suite:** `pytest tests/ -v`
2. **Check coverage:** `pytest --cov=src tests/` (must be >80%)
3. **Update docs:** README.md, TODO.md
4. **Send coordination message:**
   ```bash
   idlergear message send --to all "About to merge feature/auth-system to main. Any objections?"
   ```
5. **Wait 5 minutes** for responses
6. **Create PR** on GitHub
7. **Notify others:**
   ```bash
   idlergear message send --to all "PR created: #42 - Please review"
   ```

## Conflict Resolution

If multiple assistants modify the same file:

1. **Detect conflict** during git pull
2. **Send coordination message:**
   ```bash
   idlergear message send --to all "Merge conflict in src/auth.py - who's working on this?"
   ```
3. **Wait for response** (check message queue)
4. **Coordinate resolution:**
   - Newer code wins by default
   - Critical changes: request human review
   - Document resolution in commit message

## Log Access

All assistants have access to application logs:

### Local Assistants (MCP)
```python
logs = get_logs(since="1 hour ago", level="ERROR")
```

### Web Assistants (eddi)
```bash
eddi-msgsrv send "LOGS: show --since='1 hour ago' --errors-only" --server local
```

### Git-Based (Async)
```bash
idlergear sync pull  # Includes latest logs in .idlergear/logs/
```

## Example Collaboration Workflow

### Scenario: Claude Web + Local Gemini

**Day 1: Claude Code Web (Feature Development)**

```bash
# Claude creates feature branch
git checkout -b feature/user-profiles

# Implements user profile system
# ... coding ...

# Runs tests
pytest tests/test_profiles.py -v

# Commits
git commit -m "feat: Add user profile CRUD operations"

# Sends message to Gemini for review
idlergear message send --to local "User profiles implemented. Please review tests."

# Pushes to sync branch for Gemini to access
idlergear sync push
```

**Day 1: Local Gemini (Code Review)**

```bash
# Gemini pulls changes
idlergear sync pull

# Reviews code and tests
# ... analyzing ...

# Finds issue: missing edge case test
# Adds test
cat >> tests/test_profiles.py <<EOF
def test_profile_with_unicode_name():
    profile = create_profile(name="José García")
    assert profile.name == "José García"
EOF

# Runs tests
pytest tests/test_profiles.py -v

# Commits
git commit -m "test: Add unicode name test case"

# Responds to Claude
idlergear message respond --id <msg-id> --body "Added unicode test case. Ready to merge!"

# Pushes update
idlergear sync push
```

**Day 1: Claude Code Web (Merge)**

```bash
# Claude pulls Gemini's update
idlergear sync pull

# Reviews new test
# ... looks good ...

# Runs full test suite
pytest tests/ -v

# Creates PR
gh pr create --title "Add user profile system" --body "Reviewed by Gemini"

# Notifies all
idlergear message send --to all "PR #42 created - user profiles ready for review"
```

## Best Practices

1. **Claim work in TODO.md**
   ```markdown
   - [ ] Implement caching (Gemini, in progress, ETA: 2h)
   ```

2. **Update status frequently**
   - Commit every 30 minutes
   - Push to sync branches hourly
   - Check messages every 15 minutes

3. **Communicate blockers**
   ```bash
   idlergear message send --to all "BLOCKED: Need database schema decision for caching"
   ```

4. **Share context**
   - Include error logs in messages
   - Reference specific files/lines
   - Link to relevant issues/PRs

5. **Respect ownership**
   - Don't force-push to others' branches
   - Always ask before major refactors
   - Document breaking changes

## Emergency Override

If human intervention is needed:

```bash
idlergear message send --to human "HUMAN_REVIEW_NEEDED: Conflicting approaches to authentication"
```

This creates a GitHub issue automatically for human review.
```

---

## Multi-LLM Collaboration

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                         │
│                    github.com/user/my-app                        │
│                                                                   │
│  main ──┬── feature/auth (Claude)                               │
│         ├── feature/api (Gemini)                                │
│         └── feature/ui (Copilot)                                │
│                                                                   │
│  idlergear-coord ← Message passing branch                       │
│    └── .idlergear/messages/*.json                              │
└─────────────────────────────────────────────────────────────────┘
                              ↑ ↓ git push/pull
        ┌─────────────────────┴─────────────────────┐
        │                                             │
        ↓                                             ↓
┌──────────────────┐                        ┌──────────────────┐
│  Claude Code Web │                        │  Local Gemini CLI│
│                  │←──────────────────────→│                  │
│  Via: Git sync   │   eddi messaging      │  Via: MCP server │
│       eddi msg   │   (real-time)         │       Git sync   │
└──────────────────┘                        └──────────────────┘
        ↓                                             ↓
        └─────────────────────┬─────────────────────┘
                              ↓
                    ┌─────────────────────┐
                    │  Log Daemon (Local) │
                    │                     │
                    │  Collects from:     │
                    │  - App stdout/stderr│
                    │  - OpenTelemetry    │
                    │  - Splunk           │
                    │  - Remote servers   │
                    └─────────────────────┘
                              ↓
                    Distributes logs to:
                    - MCP server (local LLMs)
                    - eddi messaging (web LLMs)
                    - Git sync (.idlergear/logs/)
```

### Communication Methods

#### 1. Git-Based (Async, Persistent)

**Use for:** Code sync, documentation updates, long-term coordination

```bash
# Send message via git
idlergear message send --to web "Please review authentication module"

# Creates: .idlergear/messages/<uuid>.json
# Commits to: idlergear-coord branch
# Other assistants read via: idlergear message list
```

**Latency:** 30-60 seconds
**Pros:** Persistent, works offline, integrated with git
**Cons:** Slow for real-time

#### 2. eddi Messaging (Real-Time, Ephemeral)

**Use for:** Command execution, log streaming, rapid iteration

```bash
# Send command for immediate execution
eddi-msgsrv send "EXEC: pytest tests/ -v" --server local

# Receive response in 2-5 seconds
```

**Latency:** 2-5 seconds
**Pros:** Real-time, live streaming, long-running processes
**Cons:** Requires eddi server running, ephemeral

#### 3. MCP Server (Local Only, Direct)

**Use for:** Local LLM tools accessing project context

```python
# LLM calls MCP tool
result = await mcp_client.call_tool("project_status")
logs = await mcp_client.call_tool("get_logs", {"since": "1 hour"})
```

**Latency:** <100ms
**Pros:** Instant, rich data structures, typed
**Cons:** Local only, no remote access

---

## Log Management Architecture

### Three-Tier Log System

```
┌──────────────────────────────────────────────────────────────┐
│                    TIER 1: Log Sources                        │
│                                                                │
│  Local App           Remote Servers        External Services  │
│  ├─ stdout/stderr    ├─ SSH servers        ├─ OpenTelemetry  │
│  ├─ log files        ├─ Docker containers  ├─ Splunk         │
│  └─ Python logging   └─ Kubernetes pods    └─ Datadog        │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│               TIER 2: Log Daemon (Aggregation)                │
│                                                                │
│  idlergear-log-daemon                                         │
│  ~/.idlergear/log-daemon.sock                                │
│                                                                │
│  Functions:                                                   │
│  - Collect logs from all sources                             │
│  - Parse and structure (JSON)                                │
│  - Filter by level, keyword, time                            │
│  - Deduplicate                                               │
│  - Enrich with metadata (timestamp, source, context)         │
│  - Store in SQLite buffer                                    │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│            TIER 3: Log Distribution (Consumers)               │
│                                                                │
│  MCP Server          eddi Messaging      Git Sync             │
│  (local LLMs)        (web LLMs)          (async)             │
│  ├─ Real-time        ├─ Real-time        ├─ Batch (hourly)  │
│  ├─ Query API        ├─ Stream           ├─ Commit to branch│
│  └─ Filters          └─ Broadcast        └─ .idlergear/logs/ │
└──────────────────────────────────────────────────────────────┘
```

### Log Daemon Configuration

**File:** `.idlergear/log-daemon.toml`

```toml
[daemon]
enabled = true
socket = "~/.idlergear/log-daemon.sock"
storage = "~/.idlergear/log-buffer.db"  # SQLite
buffer_size_mb = 100
retention_hours = 48

[sources.local]
# Local application logs
enabled = true
methods = ["stdout", "stderr", "file"]

[sources.local.file]
paths = [
  "/tmp/*.log",
  "~/.local/share/*/logs/*.log",
]
watch = true  # inotify/fsevents

[sources.otel]
# OpenTelemetry collector
enabled = true
endpoint = "http://localhost:4317"
protocol = "grpc"
auth = "none"

[sources.splunk]
# Splunk HEC (HTTP Event Collector)
enabled = true
endpoint = "http://splunk.example.com:8088"
token = "keychain:splunk-token"  # From system keychain
index = "my-app-logs"

[sources.remote_ssh]
# Remote servers via SSH
enabled = true

[[sources.remote_ssh.servers]]
name = "production"
host = "prod.example.com"
user = "deploy"
key = "~/.ssh/id_rsa"
log_paths = ["/var/log/myapp/*.log"]

[[sources.remote_ssh.servers]]
name = "staging"
host = "staging.example.com"
user = "deploy"
key = "~/.ssh/id_rsa"
log_paths = ["/var/log/myapp/*.log"]

[processing]
# Log processing pipeline

[processing.parsing]
# Parse structured logs
formats = ["json", "logfmt", "clf"]
fallback = "plain"

[processing.filtering]
# Filter logs
min_level = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
exclude_patterns = [
  "health_check",
  "metrics_scrape",
]

[processing.enrichment]
# Add metadata
add_hostname = true
add_timestamp = true
add_project = true
add_git_branch = true

[distribution.mcp]
# MCP server (local LLMs)
enabled = true
real_time = true
query_api = true

[distribution.eddi]
# eddi messaging (web LLMs)
enabled = true
server = "my-awesome-app"
real_time = true
broadcast = true

[distribution.git]
# Git sync branches (async)
enabled = true
branch = "idlergear-coord"
interval_minutes = 60
max_size_mb = 10
format = "json"
path = ".idlergear/logs/"
```

### Log Daemon Commands

```bash
# Start log daemon
idlergear logs daemon start

# Check daemon status
idlergear logs daemon status
# Output:
# ✓ Log daemon running
#   PID: 12345
#   Uptime: 2h 15m
#   Sources: 5 active (local, otel, splunk, ssh:prod, ssh:staging)
#   Buffer: 1,234 logs (12.5 MB)
#   Distributed: 10,456 logs (last hour)

# Stop daemon
idlergear logs daemon stop

# Add log source
idlergear logs source add otel http://localhost:4317
idlergear logs source add splunk http://splunk:8088 --token <token>
idlergear logs source add ssh prod.example.com --user deploy --path /var/log/app/*.log

# List sources
idlergear logs source list
# Output:
# SOURCE      TYPE      STATUS    LOGS/MIN
# local       file      active    45
# otel        grpc      active    120
# splunk      http      active    200
# ssh:prod    ssh       active    80
# ssh:staging ssh       inactive  0

# Query logs (local, from daemon)
idlergear logs show --since "1 hour ago"
idlergear logs show --level ERROR
idlergear logs show --source ssh:prod
idlergear logs show --grep "authentication failed"

# Stream logs in real-time
idlergear logs stream
idlergear logs stream --follow --source otel

# Export logs for LLM analysis
idlergear logs export --format llm-friendly --since "1 day" > logs_for_llm.txt
```

### Log Access from LLM Assistants

#### Local LLMs (via MCP)

```python
# In Claude Desktop, Gemini CLI, etc.
# MCP tool: get_logs

result = await get_logs(
    since="1 hour ago",
    level="ERROR",
    source="all",
    limit=100
)

# Returns structured JSON:
[
  {
    "timestamp": "2025-11-18T10:30:15Z",
    "level": "ERROR",
    "source": "local",
    "message": "Failed to connect to database",
    "context": {
      "file": "src/db.py",
      "line": 42,
      "function": "connect",
      "exception": "psycopg2.OperationalError"
    }
  },
  ...
]
```

#### Web LLMs (via eddi)

```bash
# In Claude Code Web
eddi-msgsrv send "LOGS: show --since='1 hour' --errors-only" --server local

# Response (streamed):
{
  "type": "LOGS",
  "count": 5,
  "entries": [
    {
      "timestamp": "2025-11-18T10:30:15Z",
      "level": "ERROR",
      "message": "Failed to connect to database",
      "context": {...}
    },
    ...
  ]
}
```

#### Git-Based (Async)

```bash
# Logs synced to git every hour
idlergear sync pull

# Read logs
cat .idlergear/logs/latest.json

# Or use idlergear command
idlergear logs show --from-git
```

### Remote Log Collection Example

**Scenario:** Debugging production issue from Claude Code Web

```bash
# 1. Configure remote SSH source (one-time)
idlergear logs source add ssh prod.example.com \
  --user deploy \
  --key ~/.ssh/prod_rsa \
  --path "/var/log/myapp/*.log"

# 2. Log daemon automatically starts collecting
#    Logs from production server stream to local daemon

# 3. In Claude Code Web, query production logs
eddi-msgsrv send "LOGS: show --source=ssh:prod --since='10 minutes' --errors-only" --server local

# 4. Receive production logs in web interface
#    Claude analyzes and suggests fixes

# 5. Deploy fix
eddi-msgsrv send "EXEC: ssh prod.example.com 'cd /app && git pull && systemctl restart myapp'" --server local

# 6. Monitor logs in real-time
eddi-msgsrv send "LOGS: stream --source=ssh:prod --follow" --server local
# Watches production logs live from web interface
```

---

## Branch Management

### Automated Branch Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Branch Creation                           │
│  idlergear branch create feature/auth --owner claude-web    │
└─────────────────────────────────────────────────────────────┘
                            ↓
              Registers in .idlergear/branches.json
              {
                "name": "feature/auth",
                "owner": "claude-web",
                "created": "2025-11-18T10:00:00Z",
                "status": "active"
              }
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Development Phase                           │
│  - Claude works on feature/auth                             │
│  - Regular commits                                          │
│  - CI runs on every push                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Collaboration Phase                         │
│  - Gemini reviews: idlergear branch request-access feature/auth │
│  - Claude approves: idlergear branch grant-access feature/auth gemini │
│  - Gemini creates sub-branch: feature/auth-gemini-review   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    PR Creation                               │
│  idlergear pr create --title "Add authentication"          │
│  - Creates GitHub PR                                        │
│  - Notifies all assistants via message passing             │
│  - Runs full CI/CD                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Merge & Cleanup                            │
│  idlergear pr merge --cleanup                               │
│  - Merges PR to main                                        │
│  - Deletes feature/auth (local + remote)                   │
│  - Deletes sub-branches (feature/auth-*)                   │
│  - Updates .idlergear/branches.json (status: merged)       │
│  - Notifies all assistants                                  │
└─────────────────────────────────────────────────────────────┘
```

### Branch Management Commands

```bash
# Create branch with ownership
idlergear branch create feature/caching --owner gemini

# List branches with metadata
idlergear branch list
# Output:
# BRANCH              OWNER        CREATED     STATUS    COMMITS
# feature/auth        claude-web   2h ago      active    12
# feature/caching     gemini       1h ago      active    5
# feature/api         copilot      30m ago     active    3

# Request access to another assistant's branch
idlergear branch request-access feature/auth --requester gemini

# Grant access
idlergear branch grant-access feature/auth gemini

# Check branch status
idlergear branch status feature/auth
# Output:
# Branch: feature/auth
# Owner: claude-web
# Created: 2 hours ago
# Last commit: 15 minutes ago
# CI status: ✓ Passing
# Coverage: 87%
# Collaborators: gemini (reviewer)

# Auto-cleanup stale branches
idlergear branch cleanup --dry-run
# Output:
# Would delete:
#   feature/old-experiment (merged 7 days ago)
#   feature/test-branch (no commits in 14 days)

idlergear branch cleanup --force
```

### Conflict Resolution

```bash
# Detect conflicts
idlergear branch check-conflicts feature/auth
# Output:
# ⚠️  Conflicts detected with main:
#   src/auth.py (modified by both)
#   tests/test_auth.py (modified by both)
#
# Suggested resolution:
#   1. Pull latest main: git pull origin main
#   2. Resolve conflicts in editor
#   3. Run tests: pytest tests/
#   4. Commit: git commit -m "Merge main, resolve conflicts"

# Send coordination message
idlergear branch send-conflict-notice feature/auth
# Creates message:
#   "Conflict in feature/auth with main.
#    Files: src/auth.py, tests/test_auth.py
#    Owner (claude-web): Please resolve"
```

---

## Complete Example Workflow

### Day 0: Project Initialization

```bash
# Human runs single command
idlergear new my-awesome-app \
  --lang python \
  --llm-tools claude,gemini,copilot \
  --enable-logs \
  --enable-messaging

# Everything is created (see above)

# Enter directory
cd my-awesome-app

# Verify setup
idlergear status

# Output:
# ✓ Project: my-awesome-app
# ✓ Git: Clean, on branch main
# ✓ GitHub: github.com/marctjones/my-awesome-app (private)
# ✓ Tests: 1 passed, 0 failed
# ✓ Coverage: 100% (1 file)
# ✓ Log daemon: Running (PID 12345)
# ✓ Message server: Running (TOR-ABC123)
# ✓ MCP server: Running (localhost:3000)
```

### Day 1: Claude Code Web - Initial Development

```bash
# In browser: https://claude.ai/code
# Clone repo: github.com/marctjones/my-awesome-app

# Connect to local environment (one-time)
eddi-msgsrv connect --code TOR-ABC123 --namespace claude-web@my-app --alias local

# Create feature branch
git checkout -b feature/user-authentication

# Ask Claude to implement auth
"""
Implement user authentication system with:
- Login/logout endpoints
- JWT token generation
- Password hashing (bcrypt)
- User registration

Follow TDD - write tests first!
See AI_INSTRUCTIONS/TESTING.md for requirements.
"""

# Claude implements (TDD):
# 1. Writes test_auth.py
# 2. Runs tests (fails) via: eddi-msgsrv send "EXEC: pytest tests/ -v"
# 3. Implements auth.py
# 4. Runs tests (passes)
# 5. Commits

# Test locally
eddi-msgsrv send "EXEC: python -m src.main" --server local

# Receives logs in real-time, sees error
# Fixes error, tests again

# Push to GitHub
git push origin feature/user-authentication

# Send message to Gemini for review
idlergear message send --to local "Auth system implemented in feature/user-authentication. Please review!"
```

### Day 1: Local Gemini - Code Review

```bash
# Gemini CLI runs locally with MCP access

# Check messages
idlergear message list --filter-to local

# Output:
# [1] From: claude-web | 10 minutes ago
#     "Auth system implemented in feature/user-authentication. Please review!"

# Pull branch
git fetch origin
git checkout feature/user-authentication

# Review code with context
gemini "Review the authentication implementation.
Check for security issues, test coverage, and best practices.
Use get_logs() to see recent test runs."

# Gemini uses MCP tools:
code = await read_file("src/auth.py")
tests = await read_file("tests/test_auth.py")
coverage = await get_coverage()
logs = await get_logs(since="1 hour", grep="auth")

# Gemini finds issues:
# 1. Missing rate limiting on login endpoint
# 2. Passwords not validated for strength
# 3. Test coverage only 75% (need 80%+)

# Gemini adds fixes
# ... implements rate limiting ...
# ... adds password validation ...
# ... adds more tests ...

# Runs tests
pytest tests/test_auth.py -v --cov=src

# All pass, coverage 87%

# Commits
git commit -m "security: Add rate limiting and password validation to auth"

# Responds to Claude
idlergear message respond --id 1 --body "Added rate limiting and password validation. Coverage now 87%. Ready to merge!"

# Pushes
git push origin feature/user-authentication
```

### Day 2: Claude Code Web - Merge

```bash
# Claude sees Gemini's response
idlergear message list --filter-from local

# Pulls latest
git pull origin feature/user-authentication

# Reviews Gemini's additions
# ... looks good ...

# Runs full test suite via local
eddi-msgsrv send "EXEC: pytest tests/ -v --cov=src" --server local

# All tests pass, 87% coverage

# Creates PR
idlergear pr create \
  --title "Add user authentication system" \
  --body "Implements login/logout with JWT. Includes rate limiting and password validation. Reviewed by Gemini."

# This automatically:
# - Creates GitHub PR
# - Runs CI/CD
# - Sends message to all assistants

# Notifies team
idlergear message send --to all "PR #1 created - authentication system. Please review before merge."
```

### Day 2: Human Review & Merge

```bash
# Human reviews PR on GitHub
# Approves

# Merge via idlergear (auto-cleanup)
idlergear pr merge 1 --cleanup

# This:
# 1. Merges PR to main
# 2. Deletes feature/user-authentication (local + remote)
# 3. Updates .idlergear/branches.json
# 4. Sends message to all assistants
# 5. Switches local repos to main
# 6. Pulls latest main

# All assistants automatically notified:
# "PR #1 merged. Branch feature/user-authentication deleted. Please sync to main."
```

### Day 3: Copilot CLI - New Feature

```bash
# Human wants API endpoints
# Runs local Copilot CLI

# Copilot creates branch
idlergear branch create feature/api-endpoints --owner copilot

# Implements REST API
# Uses MCP to access project context
# Writes tests (TDD)
# Commits regularly

# Meanwhile, app is running in production
# Logs streaming from production server

# Copilot gets production logs via MCP
logs = await get_logs(source="ssh:prod", since="1 hour", level="ERROR")

# Sees authentication errors in production
# Realizes bug in rate limiting (from Gemini's code)

# Creates hotfix branch
git checkout main
git checkout -b hotfix/auth-rate-limit

# Fixes bug
# Tests locally
# Commits
# Creates PR with urgent label

# Sends coordination message
idlergear message send --to all "URGENT: Hotfix for auth rate limiting bug in production. PR #2 needs immediate review!"

# Human sees notification
# Reviews and merges immediately
# Deploys to production

# Copilot continues working on API endpoints
# Merges when ready
```

### Day 4: Multi-Assistant Parallel Development

```bash
# Three features in parallel:

# Claude Code Web: feature/email-notifications
# Gemini CLI: feature/database-migration
# Copilot CLI: feature/admin-dashboard

# All working simultaneously
# Communicating via message passing
# Logs flowing to all assistants
# Branch management automatic
# CI/CD running on all branches
# No conflicts (different files)

# End of day: 3 PRs ready
# Human reviews all
# Merges in order (database first, then email, then dashboard)
# idlergear handles cleanup automatically
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            GITHUB REPOSITORY                                 │
│                      github.com/user/my-awesome-app                          │
│                                                                              │
│  main ──┬── feature/auth (Claude)                                           │
│         ├── feature/api (Gemini)                                            │
│         └── feature/ui (Copilot)                                            │
│                                                                              │
│  idlergear-coord ← Message passing + logs sync                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↕ git
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LOCAL DEVELOPMENT MACHINE                            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      MCP Server (localhost:3000)                     │   │
│  │  Tools: project_status, get_logs, run_tests, list_todos, etc.      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           ↕                    ↕                    ↕                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │ Claude Code  │    │  Gemini CLI  │    │ Copilot CLI  │                 │
│  │   (local)    │    │              │    │              │                 │
│  └──────────────┘    └──────────────┘    └──────────────┘                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │               eddi Messaging Server (Tor Hidden Service)             │   │
│  │  Unix Socket: /tmp/eddi-msgsrv-my-app.sock                          │   │
│  │  Tor .onion: abc123def456.onion                                     │   │
│  │  Connection code: TOR-ABC123                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           ↕ (real-time messaging, 2-5s latency)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Log Daemon (idlergear-log-daemon)                 │   │
│  │  Socket: ~/.idlergear/log-daemon.sock                               │   │
│  │  Storage: ~/.idlergear/log-buffer.db (SQLite)                       │   │
│  │                                                                       │   │
│  │  Sources:                          Consumers:                        │   │
│  │  ├─ Local app stdout/stderr   →   ├─ MCP server (local LLMs)       │   │
│  │  ├─ OpenTelemetry (localhost)  →   ├─ eddi messaging (web LLMs)    │   │
│  │  ├─ Splunk (remote)            →   └─ Git sync (async)              │   │
│  │  └─ SSH servers (prod, staging) →                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Application Runtime                            │   │
│  │  python -m src.main                                                  │   │
│  │  ├─ stdout/stderr → Log daemon                                      │   │
│  │  ├─ structlog → Log daemon                                          │   │
│  │  └─ OpenTelemetry → Log daemon → OTel collector                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↕ Tor network
┌─────────────────────────────────────────────────────────────────────────────┐
│                          WEB-BASED LLM TOOLS                                 │
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│  │ Claude Code Web  │    │  Copilot Web     │    │  Codex Web       │     │
│  │                  │    │                  │    │                  │     │
│  │ Browser-based    │    │ Browser-based    │    │ Browser-based    │     │
│  │                  │    │                  │    │                  │     │
│  │ Connects via:    │    │ Connects via:    │    │ Connects via:    │     │
│  │ - Git sync       │    │ - Git sync       │    │ - Git sync       │     │
│  │ - eddi (Tor)     │    │ - eddi (Tor)     │    │ - eddi (Tor)     │     │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↕ SSH/HTTPS
┌─────────────────────────────────────────────────────────────────────────────┐
│                          REMOTE LOG SOURCES                                  │
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│  │ Production       │    │ Staging          │    │ OpenTelemetry    │     │
│  │ Server           │    │ Server           │    │ Collector        │     │
│  │                  │    │                  │    │                  │     │
│  │ /var/log/app/*   │    │ /var/log/app/*   │    │ localhost:4317   │     │
│  │                  │    │                  │    │                  │     │
│  │ SSH access       │    │ SSH access       │    │ gRPC endpoint    │     │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘     │
│                                                                              │
│  ┌──────────────────────────────────────────┐                              │
│  │ Splunk                                    │                              │
│  │ http://splunk.example.com:8088            │                              │
│  │ HEC (HTTP Event Collector)                │                              │
│  └──────────────────────────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration Reference

### `.idlergear/config.toml`

```toml
[project]
name = "my-awesome-app"
language = "python"
version = "0.1.0"
created = "2025-11-18T10:00:00Z"

[git]
default_branch = "main"
auto_push = true
auto_pull = true

[llm_tools]
enabled = ["claude", "gemini", "copilot"]
preferred = "claude"

[mcp]
enabled = true
port = 3000
bind_address = "127.0.0.1"
auto_start = true

[eddi]
enabled = true
server_name = "my-awesome-app"
ttl_minutes = 10
tor_enabled = true
local_only = false
auto_start = true

[logs]
enabled = true
daemon_enabled = true
retention_hours = 48
buffer_size_mb = 100

[logs.sources]
local = true
otel = true
splunk = true
ssh = true

[testing]
framework = "pytest"
coverage_threshold = 80
tdd_required = true
pre_commit_test = true

[security]
secret_manager = "dotenv"
never_commit = [".env", "*.pem", "*.key"]
scan_for_secrets = true

[branches]
auto_cleanup = true
cleanup_after_days = 30
require_owner = true
```

---

## Summary

This workflow provides:

### ✅ One Command Setup
- `idlergear new my-app` creates everything
- GitHub repo, documentation, tools, logging, messaging
- Ready for multi-LLM development immediately

### ✅ Multi-LLM Collaboration
- Git-based messaging (async, persistent)
- eddi messaging (real-time, ephemeral)
- MCP server (local, instant)
- Clear ownership and coordination

### ✅ Comprehensive Log Management
- Collects from anywhere (local, remote, OTel, Splunk)
- Distributes to all LLMs (MCP, eddi, git)
- Real-time streaming and batch access
- Query and filter capabilities

### ✅ Automated Branch Management
- Branch ownership tracking
- Conflict detection and resolution
- Automatic cleanup after merge
- Collaboration workflows

### ✅ Security & Best Practices
- Secrets never committed (.env, keychain)
- TDD enforced (pre-commit hooks)
- Code quality (black, flake8, mypy)
- Test coverage requirements (>80%)

### ✅ Documentation for LLMs
- AI_INSTRUCTIONS/ directory with complete guidance
- Auto-updated context (git log, coverage, TODOs)
- Clear best practices and workflows
- Examples and templates

**This is the complete vision for IdlerGear: Zero-friction, AI-first development with industrial-grade tooling.**

# IdlerGear Architecture: Three-Layer System

## Overview

IdlerGear operates as three interconnected layers:
1. **CLI Tool** - Standalone command-line interface (no LLM needed)
2. **MCP Server** - Model Context Protocol server for LLM tools
3. **Log Coordinator** - Runtime telemetry collection and distribution

---

## Layer 1: CLI Tool (Standalone)

### Core Commands

#### Project Lifecycle
```bash
# Create new project
idlergear new my-project --path ~/projects
# - Creates GitHub repo (local + remote)
# - Clones locally
# - Sets up isolated environment (venv, node_modules, etc.)
# - Installs dependencies
# - Initializes charter documents

# Setup existing project
idlergear setup
# - Detects language
# - Creates isolated environment
# - Installs dependencies
```

#### Development Tools
```bash
# Launch LLM coding tool
idlergear tools launch gemini    # Launch Gemini CLI with context
idlergear tools launch claude    # Launch Claude CLI with context
idlergear tools launch copilot   # Launch GitHub Copilot CLI

# Project introspection
idlergear status                 # Project health dashboard
idlergear context                # Generate LLM-ready context
idlergear logs show              # Show collected logs
idlergear check                  # Best practice nudges
```

#### Web ↔ Local Coordination
```bash
# Push work to web environment
idlergear sync push
# - Creates temp branch (e.g., idlergear-web-sync)
# - Adds ALL files (including data, .env templates)
# - Pushes to GitHub
# - Output: "Ready for web: switch to branch 'idlergear-web-sync'"

# Pull work from web environment
idlergear sync pull
# - Fetches web sync branch
# - Merges changes to current branch
# - Cleans up sync branch
# - Output: "Merged changes from web environment"

# Check sync status
idlergear sync status
# - What's in web but not local?
# - What's local but not in web?
```

#### Log Collection
```bash
# Start log collector for running process
idlergear logs collect --pid 12345
idlergear logs collect --name "my-app"
idlergear logs collect --auto      # Auto-detect from git repo

# Configure telemetry sources
idlergear logs source add otel http://localhost:4317
idlergear logs source add splunk http://splunk-instance:8088

# Show collected logs
idlergear logs show --last
idlergear logs show --since "1 hour ago"
idlergear logs show --errors-only

# Export logs for LLM analysis
idlergear logs export --format llm-friendly
```

#### PR & Merge Workflow
```bash
# Create PR from current branch
idlergear pr create --title "Add user authentication"

# Merge and cleanup
idlergear pr merge --cleanup
# - Merges PR to main
# - Deletes feature branch locally and remotely
# - Cleans up web sync branches
# - Switches back to main

# List dangling branches
idlergear branches cleanup --dry-run
idlergear branches cleanup --execute
```

---

## Layer 2: MCP Server

### What Is MCP?
Model Context Protocol - a standard way for LLM tools to access external tools and context.

### IdlerGear MCP Server

```bash
# Start MCP server
idlergear mcp start --port 3000

# MCP server exposes all CLI commands as tools
# LLM tools (Gemini, Claude, Copilot) can discover and invoke them
```

### MCP Tools Exposed:

1. **project_status** - Get project health
2. **project_context** - Get full project context
3. **logs_show** - Show collected logs
4. **logs_collect** - Start collecting logs
5. **sync_push** - Push to web environment
6. **sync_pull** - Pull from web environment
7. **pr_create** - Create pull request
8. **pr_merge** - Merge and cleanup
9. **check** - Best practice analysis

### Configuration

```toml
# ~/.config/idlergear/mcp.toml
[mcp]
enabled = true
port = 3000
auto_start = true

[mcp.tools]
# Which commands to expose via MCP
expose = ["status", "context", "logs", "sync", "pr"]
```

### LLM Tool Integration

**Gemini CLI:**
```bash
# Gemini discovers IdlerGear MCP server
gemini --mcp-server http://localhost:3000

# Can now invoke:
# "Show me project status" → calls project_status
# "Collect logs from the running app" → calls logs_collect
```

**Claude Code:**
```bash
# Claude connects to MCP server
claude --mcp http://localhost:3000
```

---

## Layer 3: Log Coordinator

### Purpose
Collect logs and telemetry from running applications (outside coding environment) and make them available to LLM tools.

### Architecture

```
┌─────────────────┐
│  Running App    │ (GUI, CLI, server - outside coding tool)
│  (Your Code)    │
└────────┬────────┘
         │ stdout/stderr, OpenTelemetry, Splunk
         ↓
┌─────────────────┐
│ Log Coordinator │ (idlergear logs collect)
│  - Captures logs│
│  - Parses OTel  │
│  - Formats data │
└────────┬────────┘
         │
         ├─→ .idlergear/logs/latest.log (file)
         ├─→ MCP Server (live stream)
         └─→ Web sync branch (push to web)
```

### Usage Scenario

**1. Develop in Web (Claude Code Web):**
```bash
# In Claude Code Web:
# - Write code for a GUI application
# - Commit to branch: feature/new-ui
```

**2. Test Locally (Outside Coding Tool):**
```bash
# In terminal (not in LLM tool):
git pull
git checkout feature/new-ui
python gui_app.py &  # App running in background

# Start log collection
idlergear logs collect --pid $! --export-to-web
# Collecting logs from PID 12345
# Logs will be synced to web environment
```

**3. Analyze in LLM Tool:**
```bash
# Back in Gemini CLI (local):
# Gemini invokes: logs_show
# Sees: "Error: Button click handler undefined"

# Or in Claude Web (after sync):
idlergear sync push  # Pushes logs to web branch
# Claude Code Web can now see the logs
```

### Log Collector Features

**Capture Methods:**
- **Process monitoring:** Attach to PID, capture stdout/stderr
- **OpenTelemetry:** Ingest OTLP traces/metrics/logs
- **Splunk:** Query Splunk for application logs
- **File watching:** Tail log files

**Processing:**
- **Parsing:** JSON logs, structured logs, plain text
- **Filtering:** Error levels, keywords, time ranges
- **Formatting:** Human-readable or LLM-optimized format
- **Storage:** `.idlergear/logs/` directory

**Distribution:**
- **File:** Write to `.idlergear/logs/latest.log`
- **MCP:** Stream to MCP server for real-time access by LLM tools
- **Sync:** Include in web sync branch for web LLM tools

### Configuration

```toml
# .idlergear.toml (per-project)
[logs]
enabled = true
auto_collect = true
format = "llm-friendly"

[logs.sources]
# Automatically detect and collect from:
detect_process = true  # Find running process from git repo
stdout_stderr = true   # Capture standard streams

[logs.telemetry]
otel_endpoint = "http://localhost:4317"
splunk_endpoint = "http://splunk:8088"
splunk_token = "keychain:splunk-token"

[logs.sync]
auto_push_to_web = true  # Automatically sync logs to web branch
```

---

## Complete Development Workflow

### Scenario: Build GUI App (Local → Web → Local)

**1. Create Project:**
```bash
cd ~/projects
idlergear new my-gui-app --path .
cd my-gui-app
```

**2. Do Early Work Locally (Gemini CLI):**
```bash
idlergear tools launch gemini
# Work in Gemini CLI:
# - Create initial structure
# - Write some tests
# - Commit changes
```

**3. Switch to Web (Claude Code Web):**
```bash
idlergear sync push
# Output: "Branch 'idlergear-web-sync' ready for web environment"

# Open browser: https://claude.ai/code
# - Switch to 'idlergear-web-sync' branch
# - Continue development in Claude Code Web
# - Build out GUI components
# - Commit to branch
```

**4. Test GUI Locally (Outside Coding Tools):**
```bash
# Back in terminal (not in LLM tool)
idlergear sync pull  # Get latest from web

# Start log collection
idlergear logs collect --auto --export-to-web

# Run the GUI app
python -m src.gui.main &

# Interact with GUI, test features
# Logs are being collected automatically
```

**5. Debug Issues (Back in LLM Tool):**
```bash
# In local Gemini CLI:
idlergear logs show --errors-only
# Gemini sees: "ValueError in button_handler.py line 42"
# Gemini suggests fix

# Or push logs to web:
idlergear sync push  # Includes logs

# In Claude Code Web:
# Claude reads logs from sync branch
# Claude suggests different fix
```

**6. Merge and Cleanup:**
```bash
# After testing successful:
idlergear pr create --title "Add GUI interface"
# Review PR on GitHub
idlergear pr merge --cleanup
# - Merges to main
# - Deletes feature/new-ui
# - Deletes idlergear-web-sync
# - Cleans up dangling branches
```

---

## Implementation Phases

### Phase 3A: Core CLI Commands (IMMEDIATE)
- [ ] `idlergear status` - Project health
- [ ] `idlergear context` - Generate context
- [ ] `idlergear logs show` - Display logs
- [ ] `idlergear sync push/pull` - Web coordination

### Phase 3B: Log Coordinator (SHORT TERM)
- [ ] `idlergear logs collect` - Process monitoring
- [ ] OpenTelemetry integration
- [ ] Log formatting and storage
- [ ] Auto-sync to web branch

### Phase 4: MCP Server (MEDIUM TERM)
- [ ] Implement MCP protocol
- [ ] Expose CLI commands as MCP tools
- [ ] Test with Gemini CLI
- [ ] Test with Claude Code

### Phase 5: PR Workflow (MEDIUM TERM)
- [ ] `idlergear pr create` - Create PR
- [ ] `idlergear pr merge` - Merge with cleanup
- [ ] `idlergear branches cleanup` - Remove dangling branches

### Phase 6: Advanced Telemetry (LONG TERM)
- [ ] Splunk integration
- [ ] Custom telemetry sources
- [ ] Real-time streaming to MCP
- [ ] Advanced log analysis

---

## Key Principles

1. **CLI First** - Everything works standalone, no LLM required
2. **MCP Layer** - LLM tools get structured access via standard protocol
3. **Runtime Awareness** - Collect telemetry from running code, not just static analysis
4. **Cross-Environment** - Seamlessly work between local CLI and web UIs
5. **Tool Agnostic** - Works with any LLM tool (Gemini, Claude, Copilot, future)
6. **Non-Invasive** - Doesn't change your workflow, enhances it

---

**This architecture makes IdlerGear a complete development orchestration platform.**

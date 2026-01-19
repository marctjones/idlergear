# IdlerGear

**A knowledge management API that synchronizes AI context management with human project management.**

AI coding assistants are stateless. Every session starts fresh. Knowledge is constantly lost:
- Issues discovered but forgotten next session
- Learnings not recorded for future AI instances
- Script output invisible to other agents
- Project vision drifts without protection
- Multiple AI instances can't coordinate

IdlerGear provides a **command-based API** that manages this knowledge across sessions, machines, and teams.

## AI-Assistant Agnostic

IdlerGear works identically across all major AI coding assistants:

| Assistant | Integration | Status |
|-----------|-------------|--------|
| Claude Code | MCP + CLAUDE.md | ✅ Full support |
| Gemini CLI | MCP + GEMINI.md | ✅ Full support |
| GitHub Copilot CLI | MCP + agents | ✅ Full support |
| OpenAI Codex CLI | MCP + AGENTS.md | ✅ Full support |
| Aider | CLI + .aider.conf.yml | ✅ CLI support |
| Block's Goose | MCP + .goosehints | ✅ Full support |

**Same commands, same knowledge, any assistant.** Switch between assistants without losing context.

## Features (v0.5.0)

### Knowledge Types
- **Tasks** - Track work items with status
- **Notes** - Capture quick insights and learnings
- **Vision** - Maintain project direction and goals
- **Plans** - Organize work into phases
- **References** - Store documentation and resources
- **Session State** - Perfect continuity across AI sessions
- **Runs** - Background process tracking with logs
- **Secrets** - Secure encrypted local storage for sensitive data (CLI-only, no MCP tools for security)
- **Projects** - Kanban boards with GitHub Projects v2 sync (NEW in v0.5.0!)

### Python-Native MCP Servers (Zero Node.js!)
- **Knowledge Graph** - 6 tools (95-98% token savings, relationship queries) ⭐ NEW!
- **Project Boards** - 9 tools (Kanban boards, GitHub sync, auto-add tasks) ⭐ NEW!
- **Filesystem** - 11 tools (read, write, tree, search, checksums)
- **Git + Task Integration** - 18 tools (commit-task linking, status, diff, branches)
- **Process Management** - 11 tools (list, monitor, IdlerGear runs integration)
- **Environment Detection** - 5 tools (auto-activate venv, Python/Node/Rust/.NET detection)
- **OpenTelemetry Logs** - 3 tools (query, logs, recent errors)
- **Session Management** - 4 tools (start, save, end, status)
- **Test Framework** - 11 tools (detect, run, status, coverage mapping)
- **Health Check** - Doctor command for configuration validation

**Total: 132 MCP Tools | 100% Python | 0 Node.js Dependencies**

### Backends
- **Local** - JSON file storage in `.idlergear/`
- **GitHub** - Issues, Projects, Wiki integration via `gh` CLI

### AI Integration
- **MCP Server** - **132 tools** via Model Context Protocol (universal)
- **Knowledge Graph** - 95-98% token savings for context retrieval ⭐ NEW!
- **Claude Code Hooks** - Lifecycle hooks for 100% enforcement
- **Goose Integration** - CLI + GUI support with `.goosehints`
- **Token Efficiency** - Up to 98% context reduction (15K → 200 tokens!)
- **Session Persistence** - Perfect state restoration across sessions
- **Auto Error Capture** - OpenTelemetry errors → tasks/notes automatically
- **Auto-Add Projects** - Tasks automatically assigned to boards ⭐ NEW!

### 🔍 Live Session Monitoring

Watch your AI coding session in real-time with **idlerwatch**:

```bash
idlerwatch  # See every tool call, file change, and decision as it happens
```

Beautiful TUI showing:
- Tool calls in real-time (Read, Edit, Write, Bash, etc.)
- Task operations (create, update, close)
- File changes and git operations
- Session timeline and statistics

Also available as: `idlergear monitor` or `idlergear session monitor`

## Roadmap

**See [ROADMAP.md](docs/ROADMAP.md) for full release plan.**

IdlerGear ships **incrementally stable releases** with immediately useful features. Each milestone can be adopted independently.

| Milestone | Theme | Timeline | Key Features |
|-----------|-------|----------|--------------|
| **v0.4.0** | Test & Run Awareness | Q1 2026 (2-3 weeks) | Test coverage tracking, run history, hook integration |
| **v0.5.0** ⭐ | Planning & Foundation | Q1 2026 (2-3 weeks) | Priorities registry, GraphQL API, planning clarity, docs enforcement |
| **v0.6.0** 🎯 | Structured Information | Q2 2026 (4-5 weeks) | 70-90% token savings, query API docs/priorities, knowledge graphs |
| **v0.7.0** 🌐 | Multi-Assistant & Collaboration | Q2-Q3 2026 (4-5 weeks) | Universal AI support, GitHub Projects v2, upstream contributions |
| **v0.8.0** 💎 | Developer Experience & Polish | Q4 2026 - Q1 2027 (2-4 weeks) | Production quality, complete docs, performance optimization |

**Philosophy:** Ship features users can adopt immediately. No waiting for "v1.0" to get value.

**Quick Wins (v0.5.0):** Planning foundation ships in 2-3 weeks with priorities tracking, GraphQL API, and documentation enforcement - all features you can use right away!

## Why Not Just AGENTS.md?

AGENTS.md defines **file conventions**: "look for vision in docs/VISION.md"

IdlerGear provides a **command-based API**:

```bash
idlergear vision show    # Returns authoritative vision, wherever it's stored
```

The difference:
- **Backend-agnostic** - Same command whether data is in local file, GitHub, or Jira
- **Configurable** - Project decides where data lives, command stays the same
- **Deterministic** - No AI interpretation needed, just run the command

## Quick Start

```bash
# Install from source (development)
git clone https://github.com/marctjones/idlergear.git
cd idlergear
pip install -e .

# Or install from PyPI (once published)
# pipx install idlergear

# Or with pip
# pip install idlergear

# Initialize a project
cd my-project
idlergear init
idlergear install  # Adds CLAUDE.md, AGENTS.md, .mcp.json

# Set up AI assistant integration
idlergear hooks install      # Claude Code lifecycle hooks
idlergear goose init         # Generate .goosehints for Goose

# Use it
idlergear vision show
idlergear task create "Implement feature X"
idlergear task list
idlergear note create "Found that API requires auth header"
idlergear context --mode minimal  # Get project context (97% token savings!)

# Session management (via MCP or CLI)
idlergear session-start      # Load context + previous state
idlergear session-save       # Save progress during work
idlergear session-end        # End with smart suggestions

# Start collecting logs
idlergear otel start         # ERROR logs → notes, FATAL → tasks automatically!
```

## Commands

### Core Commands
```bash
idlergear --version               # Show version
idlergear init                    # Initialize IdlerGear in project
idlergear install                 # Install AI integration files (all assistants)
idlergear uninstall               # Remove AI integration files
idlergear doctor                  # Health check and auto-fix
idlergear update                  # Self-update to latest version

# Knowledge Management
idlergear task create TEXT        # Create a task
idlergear task list               # List all tasks
idlergear task close ID           # Close a task
idlergear task show ID            # Show task details

idlergear note create TEXT        # Capture a note
idlergear note list               # List all notes
idlergear note promote ID --to task  # Promote note to task

idlergear vision show             # Show project vision
idlergear vision edit             # Edit vision (opens editor)

idlergear plan create NAME        # Create a plan
idlergear plan list               # List all plans
idlergear plan show [NAME]        # Show a plan (current if no name)
idlergear plan switch NAME        # Switch to a plan
idlergear plan edit NAME          # Edit plan title/body/state
idlergear plan delete NAME        # Delete a plan
idlergear plan complete NAME      # Mark plan as completed

idlergear reference add TITLE     # Add reference documentation
idlergear reference list          # List all references
idlergear reference show TITLE    # Show a reference

idlergear search QUERY            # Search across all knowledge types

# Context Management (Token-Efficient!)
idlergear context                 # Show context (default: minimal, ~570 tokens)
idlergear context --mode standard # Standard verbosity (~7K tokens)
idlergear context --mode detailed # Detailed (~11.5K tokens)
idlergear context --mode full     # Full context (~17K tokens)

# Session Management
idlergear session-start           # Load context + previous state
idlergear session-save            # Save current work state
idlergear session-end             # End with smart suggestions
idlergear session-status          # View current session state
idlergear session-clear           # Clear session state

# Test Framework Integration (NEW!)
idlergear test detect             # Detect test framework
idlergear test status             # Show last test run results
idlergear test run                # Run tests and parse results
idlergear test coverage FILE      # Check if file has tests
idlergear test uncovered          # Find files without tests
idlergear test changed            # Tests for changed files

# Secrets Management (CLI-only for security)
# Note: Intentionally no MCP tools - AI assistants should not access secrets
idlergear secrets init            # Initialize encrypted storage
idlergear secrets set KEY         # Store a secret (prompts for value)
idlergear secrets get KEY         # Retrieve a secret
idlergear secrets list            # List stored secrets
idlergear secrets env CMD         # Run command with secrets as env vars

# AI Assistant Integration
idlergear hooks install           # Install Claude Code lifecycle hooks
idlergear hooks test              # Test hooks work correctly
idlergear hooks list              # List installed hooks

idlergear goose init              # Generate .goosehints for Goose
idlergear goose register          # Show Goose GUI registration instructions

idlergear agents init             # Generate AGENTS.md
idlergear agents check            # Validate AGENTS.md

# MCP Configuration (NEW!)
idlergear mcp generate            # Generate .mcp.json
idlergear mcp show                # Show current MCP config
idlergear mcp add NAME CMD        # Add an MCP server
idlergear mcp remove NAME         # Remove an MCP server
idlergear mcp test                # Test MCP server connectivity

# OpenTelemetry Logging
idlergear otel start              # Start OTel collector daemon
idlergear otel stop               # Stop collector
idlergear otel status             # Show collector status
idlergear otel logs               # Query collected logs
idlergear otel config             # Manage configuration

# Watch Mode
idlergear watch check             # One-shot project analysis
idlergear watch check --act       # Auto-create tasks from TODOs

# Background Runs
idlergear run start "command"     # Start background process
idlergear run list                # List all runs
idlergear run status NAME         # Check run status
idlergear run logs NAME           # View output (--stderr for errors)
idlergear run stop NAME           # Stop a running process
idlergear run exec "command"      # Run with PTY passthrough

# Configuration
idlergear config set KEY VAL      # Configure settings
idlergear config get KEY          # Get config value
```

### MCP Tools (132 total - use via AI assistants)

See [MCP Tools Reference](#mcp-tools-reference) below for complete details.

## MCP Tools Reference

IdlerGear provides **132 MCP tools** across 16 categories. All tools are **100% Python** with **zero Node.js dependencies**.

### Session Management (4 tools) ⚡ **Start here!**

| Tool | Description |
|------|-------------|
| `idlergear_session_start` | **⚡ Call first!** Load context + previous state + recommendations |
| `idlergear_session_save` | Save current work state (task ID, files, notes) |
| `idlergear_session_end` | End session with smart suggestions for next time |
| `idlergear_session_status` | View current session state |

**Example:**
```python
# Start of EVERY AI session
result = idlergear_session_start(context_mode="minimal")
# Returns: vision, plan, tasks, notes + previous session state + recommendations
```

**Benefits**: Perfect continuity, ~570 tokens (vs 17K!), eliminates "where did we leave off?" questions

---

### Knowledge Graph (6 tools) ⭐ **NEW in v0.5.0!**

| Tool | Description |
|------|-------------|
| `idlergear_graph_query_task` | Get task context: related files, commits, symbols |
| `idlergear_graph_query_file` | Get file context: tasks, imports, symbols, changes |
| `idlergear_graph_query_symbols` | Search code symbols by name pattern |
| `idlergear_graph_populate_git` | Index git history into graph |
| `idlergear_graph_populate_code` | Index code symbols (Python AST) |
| `idlergear_graph_schema_info` | Get schema and statistics |

**Token Savings**: 95-98% reduction for context queries!
- Traditional: 15,000 tokens (grep + file reads)
- Graph: 200 tokens (structured query)

**Example:**
```python
# Get all files and commits related to task #123
result = idlergear_graph_query_task(task_id=123)
# Returns: files, commits, symbols in <40ms
```

**Documentation**: [docs/guides/knowledge-graph.md](docs/guides/knowledge-graph.md)

---

### Project Boards (9 tools) ⭐ **NEW in v0.5.0!**

| Tool | Description |
|------|-------------|
| `idlergear_project_create` | Create Kanban board |
| `idlergear_project_list` | List all project boards |
| `idlergear_project_show` | Show project with columns and tasks |
| `idlergear_project_delete` | Delete project board |
| `idlergear_project_add_task` | Add task to board |
| `idlergear_project_remove_task` | Remove task from board |
| `idlergear_project_move_task` | Move task to different column |
| `idlergear_project_sync` | Sync to GitHub Projects v2 |
| `idlergear_project_link` | Link to existing GitHub Project |

**Auto-Add Configuration**: Configure `projects.auto_add = true` to automatically assign new tasks to project boards.

**Example:**
```python
# Create project and configure auto-add
idlergear_project_create(title="Sprint Backlog")
# Configure: projects.auto_add = true, projects.default_project = "sprint-backlog"
# Now: idlergear_task_create() returns {task: {...}, added_to_project: true}
```

**Documentation**: [docs/guides/github-projects.md](docs/guides/github-projects.md)

---

### Filesystem Operations (11 tools)

| Tool | Description |
|------|-------------|
| `idlergear_fs_read_file` | Read file contents |
| `idlergear_fs_read_multiple` | Batch read multiple files |
| `idlergear_fs_write_file` | Write file contents |
| `idlergear_fs_create_directory` | Create directories |
| `idlergear_fs_list_directory` | List directory contents |
| `idlergear_fs_directory_tree` | Recursive tree structure (gitignore-aware) |
| `idlergear_fs_move_file` | Move/rename files |
| `idlergear_fs_search_files` | Pattern search (respects .gitignore) |
| `idlergear_fs_file_info` | File metadata (size, modified, permissions) |
| `idlergear_fs_file_checksum` | Calculate checksums (MD5, SHA1, SHA256) |
| `idlergear_fs_allowed_directories` | View security boundaries |

**Replaces**: `@modelcontextprotocol/server-filesystem` (Node.js)

---

### Git + Task Integration (18 tools) 🎯 **Unique to IdlerGear!**

| Tool | Description |
|------|-------------|
| **Core Git Operations** | |
| `idlergear_git_status` | Structured status (branch, staged, modified, untracked) |
| `idlergear_git_diff` | Configurable diffs (staged/unstaged, context lines) |
| `idlergear_git_log` | Commit history with filtering |
| `idlergear_git_add` | Stage files or all changes |
| `idlergear_git_commit` | Create commits |
| `idlergear_git_reset` | Unstage files or hard reset |
| `idlergear_git_show` | Show commit details with diff |
| `idlergear_git_branch_list` | List branches |
| `idlergear_git_branch_create` | Create branches |
| `idlergear_git_branch_checkout` | Switch branches |
| `idlergear_git_branch_delete` | Delete branches |
| **IdlerGear-Specific** 🔥 | |
| `idlergear_git_commit_task` | **Auto-link commits to tasks** |
| `idlergear_git_status_for_task` | Filter status by task files |
| `idlergear_git_task_commits` | Find all commits mentioning a task |
| `idlergear_git_sync_tasks` | Update task status from commit messages |

**Replaces**: `cyanheads/git-mcp-server` (Node.js)
**Unique**: First MCP git server with automatic commit-task linking!

**Example:**
```python
# Commit and link to task in one operation
idlergear_git_commit_task(
    task_id=42,
    message="Fix authentication bug",
    files=["auth.py"]
)
# Creates commit with "Task: #42" in message
```

---

### Process Management (11 tools)

| Tool | Description |
|------|-------------|
| `idlergear_pm_list` | List running processes |
| `idlergear_pm_get` | Get specific process info |
| `idlergear_pm_kill` | Kill a process |
| `idlergear_pm_run_start` | Start IdlerGear run |
| `idlergear_pm_run_list` | List IdlerGear runs |
| `idlergear_pm_run_status` | Get run status |
| `idlergear_pm_run_logs` | Get run logs |
| `idlergear_pm_run_stop` | Stop a run |
| `idlergear_pm_system_info` | CPU, memory, disk usage |
| `idlergear_pm_cpu_percent` | Current CPU usage |
| `idlergear_pm_memory_info` | Memory usage breakdown |

**Replaces**: `pm-mcp` (Node.js)
**Integrates**: IdlerGear's existing `runs` system for task-aware process management

---

### Environment Detection (5 tools) 🎯 **Auto-Activates Python, Rust & .NET!**

| Tool | Description |
|------|-------------|
| `idlergear_env_info` | **Consolidated environment snapshot** (Python, Node, venv, PATH) |
| `idlergear_env_which` | Enhanced `which` showing ALL PATH matches |
| `idlergear_env_detect` | Project type detection (Python, Node, Rust, .NET, Go, etc.) |
| `idlergear_env_find_venv` | Find virtual environments (venv, poetry, conda) |
| `idlergear_env_active` | Show currently active environments (Python/Rust/.NET) ⭐ NEW! |

**Killer Feature**: The MCP server **automatically detects and activates** development environments on startup:
- **Python**: venv, poetry, pipenv → Sets VIRTUAL_ENV, prepends to PATH
- **Rust**: rust-toolchain.toml, rust-toolchain → Sets RUSTUP_TOOLCHAIN
- **.NET**: global.json → Detected for dotnet CLI to use

**No more AI assistants installing packages globally or using wrong toolchains!**

**Fills Gap**: No other MCP server provides this!
**Token Savings**: ~60% vs multiple shell commands

**Example:**
```python
# One call instead of 10+ shell commands
idlergear_env_info()
# Returns: Python 3.11, venv active, Node 20.x, Rust 1.75, etc.

# Check which environments were auto-activated
idlergear_env_active()
# Returns: {
#   environments: [
#     {language: "python", active: true, path: "/project/venv"},
#     {language: "rust", active: true, toolchain: "stable"},
#     {language: "dotnet", active: true, version: "8.0.100"}
#   ]
# }
```

---

### OpenTelemetry Logs (3 tools) 🔥 **Auto Error Capture!**

| Tool | Description |
|------|-------------|
| `idlergear_otel_query_logs` | Query logs with filters (severity, service, time range, full-text search) |
| `idlergear_otel_stats` | Statistics breakdown by severity/service |
| `idlergear_otel_recent_errors` | Quick error checking |

**Killer Feature**: ERROR logs automatically become notes, FATAL logs become high-priority tasks!

**Example:**
```python
# Start OTel collector (via CLI)
$ idlergear otel start

# Configure Goose to send logs
$ export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"

# Run Goose - errors automatically create tasks!
# ERROR logs → idlergear note create (tagged 'error', 'otel')
# FATAL logs → idlergear task create (labeled 'bug', 'automated')

# Query logs later
idlergear_otel_query_logs(severity="ERROR", service="goose", limit=20)
```

---

### Knowledge Management (built into all tools)

All 62+ MCP tools integrate with IdlerGear's knowledge system:
- Context-aware operations
- Task linkage where relevant
- Automatic knowledge capture (OTel)
- Token-efficient outputs

## Configuration

Configure backends in `.idlergear/config.toml`:

```toml
[backends]
task = "github"      # Use GitHub Issues for tasks
note = "local"       # Keep notes local
vision = "github"    # Sync vision to repo
```

## Documentation

**[Full Wiki](https://github.com/marctjones/idlergear/wiki)**

### Core
- [Getting Started](https://github.com/marctjones/idlergear/wiki/Getting-Started) - Installation and setup
- [Knowledge Types](https://github.com/marctjones/idlergear/wiki/Knowledge-Types) - All 6 knowledge types
- [Commands Reference](https://github.com/marctjones/idlergear/wiki/Commands-Reference) - Full CLI reference
- [MCP Server](https://github.com/marctjones/idlergear/wiki/MCP-Server) - 126 MCP tools
- [Roadmap](docs/ROADMAP.md) - Release plan with 5 incremental milestones

### AI Assistant Guides
- [AI Assistant Comparison](https://github.com/marctjones/idlergear/wiki/AI-Assistant-Comparison) - Feature comparison
- [Built-in Tools Comparison](https://github.com/marctjones/idlergear/wiki/Built-in-Tools-Comparison) - What each assistant provides
- [Claude Code Integration](https://github.com/marctjones/idlergear/wiki/Claude-Code-Integration) - Full setup guide
- [Slash Commands](https://github.com/marctjones/idlergear/wiki/Slash-Commands) - `/ig-*` command reference

### Backends
- [GitHub Integration](https://github.com/marctjones/idlergear/wiki/GitHub-Integration) - GitHub backend setup
- [GitHub Label Conventions](docs/github-labels.md) - Label categories, setup, and best practices

See [DESIGN.md](DESIGN.md) for the full knowledge model and architecture.

## The Key Insight

**Context management is an AI problem. Project management is a human problem. IdlerGear synchronizes them.**

## License

**All Rights Reserved.** This code is not open source. No license is granted for use, modification, or distribution without explicit written permission from the author.

# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**IdlerGear is a knowledge management API that synchronizes AI context management with human project management.**

It provides a **command-based API** (not file conventions like AGENTS.md):
- `idlergear vision show` - not "look for VISION.md in docs/"
- `idlergear task list` - not "check GitHub Issues or TODO.md"
- Same commands everywhere, configurable backends

See `DESIGN.md` for the full vision, knowledge model (6 types), and architecture.

## Development

```bash
source venv/bin/activate
./run.sh  # format, lint, test
```

See DEVELOPMENT.md for practices.

## Automatic Environment Activation

**The IdlerGear MCP server automatically detects and activates your project's development environments.**

When the MCP server starts, it detects and activates:

### Python
- Searches for: `venv`, `.venv`, `env`, `virtualenv`, `poetry.lock`, `Pipfile`
- Activates by: Setting `VIRTUAL_ENV`, prepending venv/bin to `PATH`
- All subprocess calls use the project's Python interpreter and packages

### Rust
- Searches for: `rust-toolchain.toml`, `rust-toolchain`, `Cargo.toml`
- Activates by: Setting `RUSTUP_TOOLCHAIN` environment variable
- cargo and rustc commands use the specified toolchain

### .NET
- Searches for: `global.json`, `*.csproj`, `*.sln`
- Detection only: dotnet CLI automatically reads `global.json`
- Ensures correct SDK version is used

**This prevents AI assistants from:**
- Installing packages globally on the host system
- Using the wrong interpreter or toolchain
- Missing project-specific dependencies
- Using incorrect SDK versions

Use `idlergear_env_active` tool to verify which environments are active.

## CRITICAL: IdlerGear Usage Rules

### Session Start

**ALWAYS run this command at the start of EVERY conversation:**

```bash
idlergear context
```

This provides the project vision, current plan, and open tasks. Do NOT skip this step.

### FORBIDDEN: File-Based Knowledge

**DO NOT create any of these files:**
- `TODO.md`, `TODO.txt`, `TASKS.md`
- `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
- `FEATURE_IDEAS.md`, `RESEARCH.md`, `BACKLOG.md`
- Any markdown file for tracking work or capturing thoughts

**ALWAYS use IdlerGear commands instead.**

### FORBIDDEN: Inline TODOs

**DO NOT write inline TODO comments:**
- `// TODO: ...`
- `# FIXME: ...`
- `/* HACK: ... */`

**INSTEAD:** Create a task with `idlergear task create "..." --label technical-debt`

### REQUIRED: Use IdlerGear Commands

| Instead of... | Use this command |
|---------------|------------------|
| Creating TODO.md | `idlergear task create "description"` |
| Writing notes to files | `idlergear note create "content"` |
| Adding TODO comments | `idlergear task create "..." --label technical-debt` |
| Creating VISION.md | `idlergear vision edit` |
| Documenting findings | `idlergear reference add "title" --body "..."` |

### During Development

| Action | Command |
|--------|---------|
| Found a bug | `idlergear task create "..." --label bug` |
| Had an idea | `idlergear note create "..."` |
| Research question | `idlergear note create "..." --tag explore` |
| Completed work | `idlergear task close <id>` |
| Check project goals | `idlergear vision show` |
| View open tasks | `idlergear task list` |
| Start background process | `idlergear run start "command" --name <name>` |
| Check background runs | `idlergear run list` |

### MANDATORY: File Annotations (Proactive)

**You MUST annotate files proactively to enable token-efficient discovery.**

**When to annotate** (do NOT skip these):
1. **After creating a new file** - Annotate immediately with purpose
2. **After reading a file to understand it** - Capture that knowledge
3. **When refactoring** - Update annotations to stay accurate
4. **Instead of grep for finding files** - Search annotations first

**How to annotate:**
```python
# When you create or understand a file:
idlergear_file_annotate(
    path="src/api/auth.py",
    description="REST API endpoints for user authentication, JWT generation, session management",
    tags=["api", "auth", "endpoints", "jwt"],
    components=["AuthController", "TokenManager", "login"],
    related_files=["src/models/user.py"]
)
```

**Finding files efficiently:**
```python
# Instead of: grep + reading 10 files (15,000 tokens)
# Do this: search annotations (200 tokens, 93% savings!)
result = idlergear_file_search(query="authentication")
# Returns: [{"path": "src/api/auth.py", "description": "...", "tags": ["auth"]}]

# Then read only the right file
idlergear_fs_read_file(path="src/api/auth.py")
```

**Rules:**
- ✅ Annotate new files immediately
- ✅ Search annotations before grep
- ✅ Update annotations when refactoring
- ❌ Don't leave files unannotated
- ❌ Don't use grep when annotations exist

### MANDATORY: Knowledge Graph Usage (95-98% Token Savings)

**You MUST use knowledge graph queries instead of grep/file reads for context retrieval.**

**The knowledge graph provides:**
- 95-98% token savings vs grep + file reads
- Sub-40ms query response times
- Persistent graph database at `~/.idlergear/graph.db`
- 2,003+ nodes indexed (commits, files, symbols)

**ALWAYS prefer graph queries over grep when:**
1. **Finding symbols** - Functions, classes, methods by name
2. **Getting task context** - Files, commits, symbols related to a task
3. **Understanding file relationships** - Imports, dependencies, changes
4. **Searching code** - Fast symbol lookup without reading files

**Query patterns:**

```python
# Instead of: grep -r "function_name" (7,500 tokens)
# Use: Knowledge graph symbol search (100 tokens, 98.7% savings!)
idlergear_graph_query_symbols(pattern="function_name", limit=10)
# Returns: [{"name": "...", "type": "function", "file": "...", "line": 45}]

# Instead of: Reading 5 files to find task context (5,000 tokens)
# Use: Knowledge graph task query (100 tokens, 98% savings!)
idlergear_graph_query_task(task_id=278)
# Returns: {"task": {...}, "files": [...], "commits": [...], "symbols": [...]}

# Instead of: cat + grep for file relationships (3,000 tokens)
# Use: Knowledge graph file query (150 tokens, 95% savings!)
idlergear_graph_query_file(file_path="src/idlergear/mcp_server.py")
# Returns: {"file": {...}, "tasks": [...], "symbols": [...], "imports": [...]}
```

**When graph is empty or missing data:**
```python
# Check schema/stats
idlergear_graph_schema_info()

# RECOMMENDED: Populate everything in one command (once per project)
idlergear_graph_populate_all(max_commits=100, incremental=True)
# Populates: git history, code symbols, GitHub tasks, commit-task links,
# references, and wiki documentation (2,000+ nodes in ~60 seconds)

# OR: Populate individually if needed
idlergear_graph_populate_git(max_commits=100, incremental=True)
idlergear_graph_populate_code(directory="src", incremental=True)

# Re-run populate_all periodically (incremental = skips existing data)
```

**New documentation query tools:**
```python
# Query wiki pages or reference docs by path
idlergear_graph_query_documentation(path="wiki/Feature-Name.md")
# Returns: doc content + related files/symbols/tasks

# Search documentation by keyword
idlergear_graph_search_documentation(query="authentication", limit=10)
# Returns: matching wiki pages and references
```

**Rules:**
- ✅ Use graph queries for symbol/task/file lookups
- ✅ Query graph BEFORE grepping (check if data exists)
- ✅ Fall back to grep only if graph returns no results
- ❌ Don't use grep when graph can answer the query
- ❌ Don't read multiple files when graph has the context

**Token savings comparison:**

| Query Type | Traditional | Knowledge Graph | Savings |
|------------|-------------|-----------------|---------|
| Find function | grep + read files (7,500 tokens) | graph query (100 tokens) | 98.7% |
| Task context | read 5 files (5,000 tokens) | graph query (100 tokens) | 98.0% |
| File symbols | cat + grep (3,000 tokens) | graph query (150 tokens) | 95.0% |

### Knowledge Flow

```
note → task or reference
```
- Quick thoughts go to notes (capture now, review later)
- Use `--tag explore` for research questions, `--tag idea` for ideas
- Actionable work goes to tasks (clear completion criteria)
- Use `idlergear note promote <id> --to task` to convert notes to tasks

### Data Protection

**NEVER modify `.idlergear/` files directly** - Use CLI commands only

## CRITICAL: IdlerGear Development Rules

**This section only applies when developing IdlerGear itself (this repository).**

### Source Code Locations

All IdlerGear features MUST be developed in `src/idlergear/`:

| Feature Type | Source Location | Installed To |
|--------------|-----------------|--------------|
| Hooks | `src/idlergear/hooks/ig_*.sh` | `.claude/hooks/` |
| Commands | `src/idlergear/commands/ig_*.md` | `.claude/commands/` |
| Rules | `src/idlergear/rules/*.md` | `.claude/rules/` |
| Skills | `src/idlergear/skills/idlergear/` | `.claude/skills/idlergear/` |
| MCP Server | `src/idlergear/mcp_server.py` | via `.mcp.json` |

### FORBIDDEN: Direct Editing of Installed Files

**NEVER edit files directly in these directories:**
- `.claude/hooks/` - Edit `src/idlergear/hooks/` instead
- `.claude/commands/` - Edit `src/idlergear/commands/` instead
- `.claude/rules/` - Edit `src/idlergear/rules/` instead
- `.claude/skills/` - Edit `src/idlergear/skills/` instead
- `.idlergear/` - Use CLI commands, never edit directly

**WHY:** These directories contain installed/generated files. Edits there:
1. Won't be tracked in git (or shouldn't be)
2. Will be overwritten by `idlergear install`
3. Won't benefit other users of IdlerGear

### Correct Development Workflow

```bash
# 1. Edit source files
vim src/idlergear/hooks/ig_user-prompt-submit.sh

# 2. Reinstall to update .claude/ files
idlergear install --upgrade

# 3. Test the changes
echo '{"prompt": "test"}' | .claude/hooks/ig_user-prompt-submit.sh

# 4. Commit the SOURCE files (not .claude/)
git add src/idlergear/hooks/ig_user-prompt-submit.sh
git commit -m "feat: Add message checking to user-prompt-submit hook"
```

### What Goes Where

| If you're adding... | Put it in... |
|---------------------|--------------|
| New hook | `src/idlergear/hooks/ig_<name>.sh` + update `HOOK_SCRIPTS` in `install.py` |
| New slash command | `src/idlergear/commands/ig_<name>.md` |
| New MCP tool | `src/idlergear/mcp_server.py` (in `list_tools` and `call_tool`) |
| New skill reference | `src/idlergear/skills/idlergear/references/<name>.md` |
| New CLI subcommand | `src/idlergear/cli.py` |

### .gitignore Reminder

The `.claude/` and `.idlergear/` directories should be in `.gitignore` for most projects.
For the IdlerGear repository itself, we track `.claude/` as a reference but source of truth is `src/idlergear/`.

## Multi-Agent Coordination (Daemon)

**IdlerGear daemon enables multiple AI assistants to work together on the same codebase.**

### Starting the Daemon

```bash
# Start daemon (required for multi-agent coordination)
idlergear daemon start

# Check daemon status
idlergear daemon status

# Stop daemon
idlergear daemon stop
```

### Coordination Features

**Message Passing:**
```bash
# Send message to all active AI agents
idlergear daemon send "API changed, review TaskService.ts"

# Queue command for any available agent to pick up
idlergear daemon queue "run full test suite" --priority 5

# List queued commands
idlergear daemon queue-list

# See active AI agents
idlergear daemon agents
```

**Agent Registration (Automatic via MCP):**
When using IdlerGear via Claude Code or other AI tools:
- Agent automatically registers with daemon
- Receives broadcasts from other agents
- Can pick up queued commands
- Status visible to all other agents

**Use Cases:**
1. **Long-running tasks**: Queue work while you continue on other things
2. **Multi-terminal coordination**: Claude Code + Goose + Aider all see same state
3. **Background execution**: Queue tests/builds to run asynchronously
4. **Team coordination**: Share context across multiple AI sessions

### Script Generation

Generate shell scripts that auto-register with daemon:

```bash
# Generate script that sets up dev environment
idlergear run generate-script backend "python manage.py runserver" \
    --venv ./venv \
    --requirement django \
    --env FLASK_ENV=development \
    --stream-logs

# Run the generated script (auto-registers with daemon)
./scripts/backend.sh

# Script automatically:
# - Activates venv
# - Installs dependencies
# - Registers with daemon as an agent
# - Streams logs visible to all agents
# - Unregisters on exit
```

**Pre-built templates:**
- `pytest` - Test runner
- `django-dev` - Django dev server
- `flask-dev` - Flask dev server
- `jupyter` - Jupyter Lab
- `fastapi-dev` - FastAPI with uvicorn

### Multi-Agent Workflow Example

```bash
# Terminal 1: Start daemon
idlergear daemon start

# Terminal 2: Claude Code (auto-registers)
# (Claude Code MCP automatically registers as agent)

# Terminal 3: Run backend script
./scripts/backend.sh  # Auto-registers as "backend-server"

# Terminal 4: Run frontend script
./scripts/frontend.sh  # Auto-registers as "frontend-dev"

# Now from any terminal:
idlergear daemon agents
# Shows: Claude Code, backend-server, frontend-dev

idlergear daemon send "Database schema updated"
# All three agents receive the message

idlergear daemon queue "rebuild migrations" --priority 10
# Any available agent can pick this up
```

### Token-Efficient Context

**Always use `--mode` flag for token efficiency:**

```bash
# Minimal mode (~750 tokens) - DEFAULT
idlergear context
idlergear context --mode minimal

# Standard mode (~2,500 tokens) - General dev work
idlergear context --mode standard

# Detailed mode (~7,000 tokens) - Deep planning
idlergear context --mode detailed

# Full mode (~17,000+ tokens) - Rare, comprehensive view
idlergear context --mode full
```

**Token savings on task lists:**

```bash
# Limit results
idlergear task list --limit 5

# Strip bodies (titles only)
idlergear task list --preview

# Combine for maximum efficiency (~200 tokens)
idlergear task list --preview --limit 10
```

## Project Board Automation

**IdlerGear can automatically move tasks between project board columns when their state changes.**

### Configuration

Enable automatic task movement based on state changes:

```toml
# .idlergear/config.toml
[projects]
auto_add = true              # Auto-add new tasks to default project
auto_move = true             # Auto-move tasks when state changes (default: true)
default_project = "main"     # Default project name
default_column = "Backlog"   # Column for new tasks

[projects.column_mapping]
open = "Backlog"             # Tasks with state="open" → "Backlog" column
in_progress = "In Progress"  # Tasks with state="in_progress" → "In Progress" column
completed = "Done"           # Tasks with state="completed" → "Done" column
closed = "Done"              # Tasks with state="closed" → "Done" column
```

### How It Works

1. **Task Creation**: New tasks automatically added to default project's default column
2. **State Changes**: When task state changes, automatically moves to mapped column
3. **Manual Updates**: Use `idlergear task update` or MCP tools - movement is automatic

### Examples

```bash
# Create project with custom columns
idlergear project create "Sprint Q1" --columns "Backlog,Ready,Doing,Review,Done"

# Configure as default
idlergear config set projects.default_project "Sprint Q1"
idlergear config set projects.auto_add true
idlergear config set projects.auto_move true

# Set column mapping
idlergear config set projects.column_mapping.open "Backlog"
idlergear config set projects.column_mapping.in_progress "Doing"
idlergear config set projects.column_mapping.completed "Done"

# Create task - automatically added to "Backlog"
idlergear task create "Implement login" --label enhancement

# Update state - automatically moves to "Doing"
idlergear task update 123 --state in_progress

# Close task - automatically moves to "Done"
idlergear task close 123
```

### Benefits

- **Automatic Kanban Flow**: Tasks move through board as work progresses
- **GitHub Sync**: Project boards can sync to GitHub Projects v2
- **No Manual Dragging**: State changes in IdlerGear update board position
- **Consistent Workflow**: Same behavior for CLI, MCP tools, and API

## GitHub Projects Custom Field Sync

**IdlerGear can automatically sync task metadata to GitHub Projects v2 custom fields.**

This enables rich project board data including priority, labels, and due dates to be visible in GitHub Projects UI.

### Configuration

Enable custom field sync and map IdlerGear properties to GitHub Projects fields:

```toml
# .idlergear/config.toml
[projects]
field_sync = true            # Enable custom field sync (default: true if field_mapping configured)

[projects.field_mapping]
priority = "Priority"        # Map task priority to "Priority" field in GitHub Projects
due = "Due Date"            # Map task due date to "Due Date" field
labels = "Labels"           # Map task labels to "Labels" field (comma-separated text)
```

### Field Types

IdlerGear supports these field type mappings:

| IdlerGear Property | GitHub Field Type | Example |
|--------------------|-------------------|---------|
| `priority` | Single Select | "high", "medium", "low" |
| `due` | Date | "2026-02-01" (YYYY-MM-DD) |
| `labels` | Text | "enhancement, api, urgent" (comma-separated) |

### How It Works

1. **Automatic Sync**: Fields are synced automatically on task create/update
2. **Field Detection**: IdlerGear finds GitHub Projects custom fields by name
3. **Type Validation**: Only syncs fields with matching types (e.g., priority → single-select)
4. **Graceful Failure**: Sync errors don't break task operations

### Setup Requirements

1. **GitHub Project**: Must be linked to IdlerGear project
2. **Custom Fields**: Must be created in GitHub Projects UI with exact names from config
3. **Field Options**: For single-select fields (priority), options must match IdlerGear values
4. **Task in Project**: Task must be added to project for sync to work

### Examples

```bash
# 1. Create GitHub Project fields (via GitHub UI)
#    - Add "Priority" field (single-select) with options: high, medium, low
#    - Add "Due Date" field (date)
#    - Add "Labels" field (text)

# 2. Configure field mapping
idlergear config set projects.field_sync true
idlergear config set projects.field_mapping.priority "Priority"
idlergear config set projects.field_mapping.due "Due Date"
idlergear config set projects.field_mapping.labels "Labels"

# 3. Link project to GitHub
idlergear project sync "main"

# 4. Create/update tasks - fields sync automatically
idlergear task create "Add auth" --priority high --due 2026-02-01 --label enhancement
# → Priority, Due Date, and Labels fields updated in GitHub Projects

idlergear task update 123 --priority low
# → Priority field updated in GitHub Projects

# 5. Manual sync (if needed)
idlergear_project_sync_fields(task_id=123)  # MCP tool
```

### MCP Tool

```python
# Manually sync task fields to GitHub Projects
idlergear_project_sync_fields(task_id=123)
```

### Benefits

- **Rich Project Data**: See priority, labels, and due dates in GitHub Projects UI
- **Automatic Updates**: Changes in IdlerGear immediately reflected in GitHub
- **Cross-Tool Workflow**: AI assistants and humans see same data
- **Custom Fields**: Extend with any field types GitHub Projects supports

### Troubleshooting

**Fields not syncing?**
- Check that GitHub Project is linked (`github_project_id` in project JSON)
- Verify custom field names match exactly (case-sensitive)
- Ensure task is in the project (use `idlergear project add-task`)
- Check field types match (priority → single-select, due → date, etc.)

**Priority values not mapping?**
- GitHub single-select options must match IdlerGear priority values exactly
- Options: "high", "medium", "low" (case-insensitive)

## IdlerGear Usage Quick Reference

**ALWAYS run at session start:**
```bash
idlergear context --mode minimal
```

**FORBIDDEN files:** `TODO.md`, `NOTES.md`, `SESSION_*.md`, `SCRATCH.md`
**FORBIDDEN comments:** `// TODO:`, `# FIXME:`, `/* HACK: */`

**Use instead:**
- `idlergear task create "..."` - Create actionable tasks
- `idlergear note create "..."` - Capture quick thoughts
- `idlergear note create "..." --tag explore` - Research questions
- `idlergear vision show` - Check project goals
- `idlergear run start "cmd" --name <n>` - Background processes
- `idlergear run logs <name>` - View run output

See AGENTS.md for full command reference.

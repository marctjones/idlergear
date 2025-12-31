# Commands Reference

Complete reference for all IdlerGear CLI commands.

## Global Options

```bash
idlergear --version, -V    # Show version and exit
idlergear --help           # Show help message
```

## Project Commands

### init

Initialize IdlerGear in the current directory.

```bash
idlergear init
```

Creates:
- `.idlergear/` directory
- `.idlergear/config.toml` - Project configuration
- `.idlergear/vision.md` - Initial vision statement

### install

Install AI integration files.

```bash
idlergear install
```

Creates:
- `CLAUDE.md` - Rules and context for Claude Code
- `AGENTS.md` - Universal AI agent instructions
- `.mcp.json` - MCP server configuration
- `.claude/rules/idlergear.md` - Session rules

### uninstall

Remove AI integration files.

```bash
idlergear uninstall
```

Removes all files created by `install`.

### context

Show full project context for AI sessions.

```bash
idlergear context
```

Outputs vision, open tasks, recent notes, and project state.

## Task Commands

### task create

Create a new task.

```bash
idlergear task create "Description of the task"
idlergear task create "Fix bug" --priority high --label backend
```

### task list

List all tasks.

```bash
idlergear task list              # All open tasks
idlergear task list --all        # Including closed
idlergear task list --label bug  # Filter by label
```

### task show

Show task details.

```bash
idlergear task show 1
```

### task complete / close

Mark a task as complete.

```bash
idlergear task complete 1
idlergear task close 1    # Alias
```

### task reopen

Reopen a closed task.

```bash
idlergear task reopen 1
```

## Note Commands

### note create

Capture a quick note.

```bash
idlergear note create "API requires auth header"
```

### note list

List all notes.

```bash
idlergear note list
```

### note promote

Promote a note to another knowledge type.

```bash
idlergear note promote 1 --to task
idlergear note promote 1 --to explore
```

## Exploration Commands

### explore create

Start a new exploration.

```bash
idlergear explore create "Should we support Windows?"
```

### explore list

List all explorations.

```bash
idlergear explore list
idlergear explore list --all  # Including closed
```

### explore show

Show exploration details.

```bash
idlergear explore show 1
```

### explore close

Close an exploration.

```bash
idlergear explore close 1
```

## Vision Commands

### vision show

Display the project vision.

```bash
idlergear vision show
```

### vision edit

Edit the vision (opens in $EDITOR).

```bash
idlergear vision edit
```

## Plan Commands

### plan create

Create a new plan.

```bash
idlergear plan create "auth-system" --title "Authentication System"
```

### plan list

List all plans.

```bash
idlergear plan list
```

### plan show

Show plan details.

```bash
idlergear plan show auth-system
```

### plan switch

Switch active plan context.

```bash
idlergear plan switch auth-system
```

## Reference Commands

### reference add

Add a reference document.

```bash
idlergear reference add "GGUF-Format" --body "GGUF is..."
```

### reference list

List all references.

```bash
idlergear reference list
idlergear reference search "quantization"
```

## Run Commands

### run

Execute a command and track output.

```bash
idlergear run ./train.sh --name training
idlergear run "pytest tests/" --name tests
```

### run status

Check status of running processes.

```bash
idlergear run status
idlergear run status training
```

### run logs

View logs from a run.

```bash
idlergear run logs training
idlergear run logs training --tail 50
```

## Configuration Commands

### config set

Set a configuration value.

```bash
idlergear config set backends.task github
idlergear config set backends.note local
```

### config get

Get a configuration value.

```bash
idlergear config get backends.task
```

### config list

Show all configuration.

```bash
idlergear config list
```

## Backend Configuration

Configure backends in `.idlergear/config.toml`:

```toml
[backends]
task = "github"      # Use GitHub Issues
note = "local"       # Keep notes local
vision = "github"    # Sync vision to repo
explore = "local"    # Local explorations
plan = "github"      # Use GitHub Projects
reference = "github" # Use GitHub Wiki
```

Available backends:
- `local` - JSON files in `.idlergear/`
- `github` - GitHub Issues, Projects, Wiki via `gh` CLI

---
id: 1
title: Commands-Reference
created: '2026-01-07T00:09:07.134363Z'
updated: '2026-01-07T00:09:07.134381Z'
---
# Commands Reference

Complete reference for all IdlerGear CLI commands.

## Global Options

```bash
idlergear --output json    # JSON output (auto-detected for MCP)
idlergear --output human   # Human-readable output
idlergear --version        # Show version
idlergear --no-upgrade     # Skip upgrade check
```

---

## Task Management

Tasks represent work to be done. Syncs with GitHub Issues.

### task create

Create a new task.

```bash
idlergear task create "Fix parser bug"
idlergear task create "Add authentication" --body "Implement OAuth2 flow"
idlergear task create "Critical fix" --priority high
idlergear task create "Bug fix" --label bug --label urgent
```

Options:
- `--body` - Task description
- `--priority` - high, medium, low
- `--label` - Labels (can repeat)

### task list

List tasks.

```bash
idlergear task list                    # All open tasks
idlergear task list --state closed     # Closed tasks
idlergear task list --state all        # All tasks
idlergear task list --priority high    # Filter by priority
idlergear task list --limit 5          # Limit results
idlergear task list --preview          # Titles only (token-efficient)
```

### task show

Show a task.

```bash
idlergear task show 42
```

### task close

Close a task.

```bash
idlergear task close 42
```

### task edit

Edit a task.

```bash
idlergear task edit 42 --title "New title"
idlergear task edit 42 --body "Updated description"
idlergear task edit 42 --priority high
idlergear task edit 42 --label bug --label priority
```

### task sync

Sync tasks with GitHub Issues.

```bash
idlergear task sync
```

---

## Note Management

Notes are for quick capture - observations, ideas, questions. Optionally syncs to GitHub Issues with a "note" label.

### note create

Create a quick note.

```bash
idlergear note create "Parser quirk with compound words"
idlergear note create "Should we support Windows?" --tag explore
idlergear note create "What if we cached the AST?" --tag idea
```

Tags:
- `explore` - Research questions
- `idea` - Ideas to flesh out later

### note list

List notes.

```bash
idlergear note list               # All notes
idlergear note list --tag idea    # Filter by tag
idlergear note list --limit 5     # Limit results
```

### note show

Show a note.

```bash
idlergear note show 1
```

### note delete

Delete a note.

```bash
idlergear note delete 1
```

### note promote

Promote a note to a task or reference.

```bash
idlergear note promote 1 --to task
idlergear note promote 1 --to reference
```

---

## Vision Management

The vision is the project's purpose and direction. Rarely changes.

### vision show

Show the project vision.

```bash
idlergear vision show
```

### vision edit

Edit the project vision.

```bash
idlergear vision edit           # Opens in $EDITOR
idlergear vision edit --content "New vision content"
```

---

## Plan Management

Plans define how to achieve goals. Groups related tasks.

### plan create

Create a plan.

```bash
idlergear plan create auth-system --title "Authentication System"
idlergear plan create auth-system --body "Implement OAuth2..."
```

### plan list

List all plans.

```bash
idlergear plan list
```

### plan show

Show a plan.

```bash
idlergear plan show auth-system    # Specific plan
idlergear plan show                # Current plan
```

### plan switch

Switch to a different plan.

```bash
idlergear plan switch auth-system
```

---

## Reference Management

References are permanent documentation. Syncs with GitHub Wiki.

### reference add

Add a reference document.

```bash
idlergear reference add "GGUF Format"
idlergear reference add "API Design" --body "Our REST API follows..."
```

### reference list

List references.

```bash
idlergear reference list
idlergear reference list --preview    # Titles only
```

### reference show

Show a reference.

```bash
idlergear reference show "GGUF Format"
```

### reference edit

Edit a reference.

```bash
idlergear reference edit "GGUF Format"
```

### reference search

Search references.

```bash
idlergear reference search "quantization"
```

### reference sync

Sync with GitHub Wiki.

```bash
idlergear reference sync
```

---

## Run Management

Runs track script execution and logs.

### run start

Start a script/command in the background.

```bash
idlergear run start "./train.sh"
idlergear run start "python server.py" --name backend
```

### run exec

Execute a command with PTY passthrough (interactive).

```bash
idlergear run exec "./interactive-script.sh"
```

### run list

List runs.

```bash
idlergear run list
```

### run status

Check run status.

```bash
idlergear run status backend
```

### run logs

Show run logs.

```bash
idlergear run logs backend
idlergear run logs backend --tail 50
idlergear run logs backend --stream stderr
```

### run stop

Stop a running process.

```bash
idlergear run stop backend
```

### run generate-script

Generate a dev environment script.

```bash
idlergear run generate-script backend "python manage.py runserver" \
    --venv ./venv \
    --requirement django
```

---

## Test Management

Test framework detection and status tracking.

### test detect

Detect the test framework in use.

```bash
idlergear test detect
```

Supports: pytest, cargo test, dotnet test, jest, vitest, go test, rspec.

### test run

Run tests and cache results.

```bash
idlergear test run
idlergear test run --args "-k auth"    # Pass args to test runner
```

### test status

Show last test run status.

```bash
idlergear test status
```

### test history

Show test run history.

```bash
idlergear test history
idlergear test history --limit 5
```

### test list

List all tests in the project.

```bash
idlergear test list
idlergear test list --files-only
```

### test coverage

Show test coverage mapping.

```bash
idlergear test coverage
idlergear test coverage --file src/parser.py
```

### test uncovered

List source files without tests.

```bash
idlergear test uncovered
```

### test changed

Show or run tests for changed files.

```bash
idlergear test changed                  # Show affected tests
idlergear test changed --run            # Run them
idlergear test changed --since main     # Since branch point
```

---

## Session Management

Session state persistence across AI sessions.

### session-start

Start a new session and load context.

```bash
idlergear session-start
idlergear session-start --mode standard    # More context
```

### session-save

Save current session state.

```bash
idlergear session-save --task 42 --files "src/api.py,src/models.py"
idlergear session-save --notes "Finished auth, need to add tests"
```

### session-end

End session and save state.

```bash
idlergear session-end --task 42 --notes "Completed OAuth implementation"
```

### session-status

Show current session state.

```bash
idlergear session-status
```

---

## Watch Mode

Proactive knowledge capture from code changes.

### watch check

One-shot analysis with suggestions.

```bash
idlergear watch check
idlergear watch check --act    # Auto-create tasks from TODO comments
```

### watch start

Start continuous watching.

```bash
idlergear watch start
```

### watch status

Show watch statistics.

```bash
idlergear watch status
```

---

## Doctor

Health checks for IdlerGear installation.

```bash
idlergear doctor              # Run health checks
idlergear doctor -v           # Show all checks
idlergear doctor --fix        # Auto-fix issues
```

---

## Project Boards

Kanban boards for task organization. Syncs with GitHub Projects v2.

### project create

Create a project board.

```bash
idlergear project create "Sprint 1"
idlergear project create "Sprint 1" --columns "Todo,Doing,Done"
idlergear project create "Sprint 1" --create-on-github
```

### project show

Show a project board.

```bash
idlergear project show sprint-1
```

### project add-task

Add a task to a project.

```bash
idlergear project add-task sprint-1 42
idlergear project add-task sprint-1 42 --column "In Progress"
```

### project move

Move a task to a different column.

```bash
idlergear project move sprint-1 42 "Done"
```

---

## Daemon

Multi-agent coordination.

### daemon start

Start the daemon.

```bash
idlergear daemon start
```

### daemon stop

Stop the daemon.

```bash
idlergear daemon stop
```

### daemon status

Check daemon status.

```bash
idlergear daemon status
```

### daemon agents

List connected AI agents.

```bash
idlergear daemon agents
```

### daemon send

Broadcast to all agents.

```bash
idlergear daemon send "API schema changed, review TaskService.ts"
```

### daemon queue

Queue a command for any agent.

```bash
idlergear daemon queue "run full test suite" --priority 5
```

---

## Context & Status

### context

Show project context for AI sessions.

```bash
idlergear context                    # Minimal (~750 tokens)
idlergear context --mode minimal     # ~750 tokens
idlergear context --mode standard    # ~2500 tokens
idlergear context --mode detailed    # ~7000 tokens
idlergear context --mode full        # ~17000+ tokens
```

### status

Quick status dashboard.

```bash
idlergear status
idlergear status --detailed
```

---

## Configuration

### config get

Get a configuration value.

```bash
idlergear config get backend.task
```

### config set

Set a configuration value.

```bash
idlergear config set backend.task github
idlergear config set backend.reference local
```

### config backend

Show or set backend configuration.

```bash
idlergear config backend show
idlergear config backend set task github
```

---

## Setup Commands

### init

Initialize IdlerGear in a project.

```bash
idlergear init
```

### install

Install Claude Code integration.

```bash
idlergear install
idlergear install --upgrade    # Update existing installation
```

### new

Create a new project with full integration.

```bash
idlergear new my-project
```

### setup-github

Configure GitHub backends.

```bash
idlergear setup-github
```

### uninstall

Remove IdlerGear from project.

```bash
idlergear uninstall
```

---

## Utility Commands

### search

Search across all knowledge types.

```bash
idlergear search "authentication"
```

### check

Check for policy violations.

```bash
idlergear check
```

### update

Update IdlerGear itself.

```bash
idlergear update
idlergear update --check    # Just check, don't install
```

### serve

Start the MCP server manually.

```bash
idlergear serve
```

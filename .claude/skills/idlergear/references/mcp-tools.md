# IdlerGear MCP Tools Reference

Complete reference for all 126 MCP tools provided by IdlerGear.

## Session Management (4 tools)

### idlergear_session_start
Start a new session, loading context and previous state.

**Parameters:**
- `context_mode`: "minimal" (default) | "standard" | "detailed" | "full"
- `load_state`: boolean (default: true)

**Returns:** Vision, plan, tasks, notes, session state, recommendations.

### idlergear_session_end
End session and save state for next time.

**Parameters:**
- `current_task_id`: integer (optional)
- `working_files`: list of strings (optional)
- `notes`: string (optional)

### idlergear_session_save
Save session state manually.

**Parameters:**
- `name`: string (optional, defaults to timestamp)
- `next_steps`: string (optional)
- `blockers`: string (optional)

### idlergear_session_restore
Restore a saved session.

**Parameters:**
- `name`: string (optional, restores most recent if omitted)

## Context & Status (3 tools)

### idlergear_context
Get project context with configurable verbosity.

**Parameters:**
- `mode`: "minimal" (~750 tokens) | "standard" (~2500) | "detailed" (~7000) | "full" (~17000)
- `include_refs`: boolean (default: false)

### idlergear_status
Quick project status dashboard.

**Parameters:**
- `detailed`: boolean (default: false)

### idlergear_search
Search across all knowledge types.

**Parameters:**
- `query`: string (required)
- `types`: list of "task" | "note" | "reference" | "plan"

## Task Management (5 tools)

### idlergear_task_create
Create a new task.

**Parameters:**
- `title`: string (required)
- `body`: string (optional)
- `labels`: list of strings (optional)
- `priority`: "high" | "medium" | "low" (optional)
- `due`: "YYYY-MM-DD" (optional)

### idlergear_task_list
List tasks.

**Parameters:**
- `state`: "open" (default) | "closed" | "all"

### idlergear_task_show
Show task details.

**Parameters:**
- `id`: integer (required)

### idlergear_task_update
Update a task.

**Parameters:**
- `id`: integer (required)
- `title`: string (optional)
- `body`: string (optional)
- `labels`: list of strings (optional)
- `priority`: "high" | "medium" | "low" | "" (optional)
- `due`: "YYYY-MM-DD" | "" (optional)

### idlergear_task_close
Close a task.

**Parameters:**
- `id`: integer (required)

## Note Management (5 tools)

### idlergear_note_create
Create a note.

**Parameters:**
- `content`: string (required)
- `tags`: list of strings (optional) - "explore", "idea", "bug"

### idlergear_note_list
List notes.

**Parameters:**
- `tag`: string (optional) - filter by tag

### idlergear_note_show
Show note details.

**Parameters:**
- `id`: integer (required)

### idlergear_note_delete
Delete a note.

**Parameters:**
- `id`: integer (required)

### idlergear_note_promote
Promote note to task or reference.

**Parameters:**
- `id`: integer (required)
- `to`: "task" | "reference" (required)

## Vision & Plans (5 tools)

### idlergear_vision_show
Show project vision.

### idlergear_vision_edit
Update project vision.

**Parameters:**
- `content`: string (required)

### idlergear_plan_create
Create a plan.

**Parameters:**
- `name`: string (required)
- `title`: string (optional)
- `body`: string (optional)

### idlergear_plan_list
List all plans.

### idlergear_plan_show
Show a plan.

**Parameters:**
- `name`: string (optional, shows current if omitted)

## Reference Management (4 tools)

### idlergear_reference_add
Add reference document.

**Parameters:**
- `title`: string (required)
- `body`: string (optional)

### idlergear_reference_list
List all references.

### idlergear_reference_show
Show a reference.

**Parameters:**
- `title`: string (required)

### idlergear_reference_search
Search references.

**Parameters:**
- `query`: string (required)

## Filesystem (11 tools)

- `idlergear_fs_read_file(path)` - Read file
- `idlergear_fs_read_multiple(paths)` - Read multiple files
- `idlergear_fs_write_file(path, content)` - Write file
- `idlergear_fs_create_directory(path)` - Create directory
- `idlergear_fs_list_directory(path?, exclude_patterns?)` - List directory
- `idlergear_fs_directory_tree(path?, max_depth?, exclude_patterns?)` - Directory tree
- `idlergear_fs_move_file(source, destination)` - Move/rename
- `idlergear_fs_search_files(pattern?, path?, use_gitignore?)` - Glob search
- `idlergear_fs_file_info(path)` - File metadata
- `idlergear_fs_file_checksum(path, algorithm?)` - File hash
- `idlergear_fs_allowed_directories()` - Security boundary

## Git Integration (18 tools)

- `idlergear_git_status(repo_path?)` - Structured status
- `idlergear_git_diff(staged?, files?, context_lines?, repo_path?)` - Diff
- `idlergear_git_log(max_count?, author?, grep?, since?, until?, repo_path?)` - History
- `idlergear_git_add(files, all?, repo_path?)` - Stage files
- `idlergear_git_commit(message, task_id?, repo_path?)` - Commit
- `idlergear_git_reset(files?, hard?, repo_path?)` - Unstage/reset
- `idlergear_git_show(commit, repo_path?)` - Show commit
- `idlergear_git_branch_list(repo_path?)` - List branches
- `idlergear_git_branch_create(name, checkout?, repo_path?)` - Create branch
- `idlergear_git_branch_checkout(name, repo_path?)` - Switch branch
- `idlergear_git_branch_delete(name, force?, repo_path?)` - Delete branch
- `idlergear_git_commit_task(task_id, message, auto_add?, repo_path?)` - Commit with task link
- `idlergear_git_status_for_task(task_id, repo_path?)` - Task-filtered status
- `idlergear_git_task_commits(task_id, max_count?, repo_path?)` - Find task commits
- `idlergear_git_sync_tasks(since?, repo_path?)` - Sync from commits

## Process Management (11 tools)

- `idlergear_pm_list_processes(filter_name?, filter_user?, sort_by?)` - List processes
- `idlergear_pm_get_process(pid)` - Process details
- `idlergear_pm_kill_process(pid, force?)` - Kill process
- `idlergear_pm_system_info()` - System stats
- `idlergear_pm_start_run(command, name?, task_id?)` - Background run
- `idlergear_pm_list_runs()` - List runs
- `idlergear_pm_get_run_status(name)` - Run status
- `idlergear_pm_get_run_logs(name, stream?, tail?)` - Run logs
- `idlergear_pm_stop_run(name)` - Stop run
- `idlergear_pm_task_runs(task_id)` - Runs for task
- `idlergear_pm_quick_start(executable, args?)` - Foreground process

## Environment (4 tools)

- `idlergear_env_info()` - Python/Node/Rust versions, venvs, PATH
- `idlergear_env_which(command)` - Find all matches in PATH
- `idlergear_env_detect(path?)` - Detect project type
- `idlergear_env_find_venv(path?)` - Find virtual environments

## OpenTelemetry (3 tools)

- `idlergear_otel_query_logs(service?, severity?, search?, start_time?, end_time?, limit?)` - Query logs
- `idlergear_otel_stats()` - Log statistics
- `idlergear_otel_recent_errors(service?, limit?)` - Recent errors

## Documentation (6 tools)

### idlergear_docs_check
Check if pdoc is available for documentation generation.

**Returns:** `{available: boolean}`

### idlergear_docs_module
Generate documentation for a single Python module.

**Parameters:**
- `module`: string (required) - Module name (e.g., "json", "idlergear.tasks")

**Returns:** Structured JSON with functions, classes, docstrings.

### idlergear_docs_generate
Generate full documentation for a Python package.

**Parameters:**
- `package`: string (required) - Package name
- `format`: "json" | "markdown" (default: "json")
- `include_private`: boolean (default: false)
- `max_depth`: integer (optional)

### idlergear_docs_summary ⚡
**TOKEN-EFFICIENT**: Generate compact API summary for AI consumption.

**Parameters:**
- `package`: string (required) - Package name
- `mode`: "minimal" (~500 tokens) | "standard" (~2k) | "detailed" (~5k)
- `include_private`: boolean (default: false)
- `max_depth`: integer (optional)

**Use this to quickly understand an API without consuming many tokens.**

### idlergear_docs_build
Build HTML documentation using pdoc.

**Parameters:**
- `package`: string (optional, auto-detects if not provided)
- `output_dir`: string (default: "docs/api")
- `logo`: string (optional)
- `favicon`: string (optional)

**Returns:** `{success, output_dir, files, count}`

### idlergear_docs_detect
Detect Python project configuration.

**Parameters:**
- `path`: string (default: current directory)

**Returns:** `{detected, name, version, config_file, source_dir, packages}`

## Test Framework (10 tools)

- `idlergear_test_detect(path?)` - Detect test framework (pytest, cargo test, jest, etc.)
- `idlergear_test_status(path?)` - Show last test run results
- `idlergear_test_run(path?, args?)` - Run tests and parse results
- `idlergear_test_history(path?, limit?)` - Show test run history
- `idlergear_test_list(path?, files_only?)` - List all tests in project
- `idlergear_test_coverage(path?, file?)` - Show test coverage mapping
- `idlergear_test_uncovered(path?)` - List files without tests
- `idlergear_test_changed(path?, since?, run?)` - Tests for changed files
- `idlergear_test_sync(path?)` - Import external test runs
- `idlergear_test_staleness(path?)` - Check how stale test results are

## Watch Mode (3 tools)

- `idlergear_watch_check(act?)` - One-shot project analysis (TODO/FIXME/HACK detection)
- `idlergear_watch_act(suggestion_id)` - Execute action for a specific suggestion
- `idlergear_watch_stats()` - Quick watch statistics (changed files, TODOs count)

## Health & Utility (3 tools)

- `idlergear_doctor(fix?)` - Check installation health and auto-fix issues
- `idlergear_version()` - Show MCP server version
- `idlergear_reload()` - Reload MCP server to pick up code changes

## Configuration & Backend (4 tools)

- `idlergear_config_get(key)` - Get a configuration value
- `idlergear_config_set(key, value)` - Set a configuration value
- `idlergear_backend_show()` - Show configured backends for all knowledge types
- `idlergear_backend_set(type, backend)` - Set backend for a knowledge type

## Run Management (5 tools)

- `idlergear_run_start(command, name?)` - Start background script/command
- `idlergear_run_list(limit?)` - List all runs
- `idlergear_run_status(name)` - Get run status
- `idlergear_run_logs(name, stream?, tail?)` - Get run logs
- `idlergear_run_stop(name)` - Stop a running process

## Project Boards (9 tools)

- `idlergear_project_create(title, columns?, create_on_github?)` - Create Kanban board
- `idlergear_project_list(include_github?)` - List all project boards
- `idlergear_project_show(name)` - Show project with columns and tasks
- `idlergear_project_delete(name, delete_on_github?)` - Delete project board
- `idlergear_project_add_task(project_name, task_id, column?)` - Add task to board
- `idlergear_project_remove_task(project_name, task_id)` - Remove task from board
- `idlergear_project_move_task(project_name, task_id, column)` - Move task to column
- `idlergear_project_sync(name)` - Sync to GitHub Projects v2
- `idlergear_project_link(name, github_project_number)` - Link to existing GitHub Project

## Multi-Agent Messaging (7 tools)

- `idlergear_message_send(to_agent, message, ...)` - Send message to another agent
- `idlergear_message_list(agent_id?, unread_only?, delivery?, limit?)` - Check inbox
- `idlergear_message_process(agent_id?, create_tasks?)` - Process inbox messages
- `idlergear_message_mark_read(agent_id?, message_ids?)` - Mark messages as read
- `idlergear_message_clear(agent_id?, all_messages?)` - Clear read messages
- `idlergear_message_test(test_message?)` - Test messaging pipeline

## Daemon & Coordination (6 tools)

- `idlergear_daemon_register_agent(name, agent_type?, metadata?)` - Register with daemon
- `idlergear_daemon_list_agents()` - List active AI agents
- `idlergear_daemon_queue_command(command, priority?, wait_for_result?)` - Queue command
- `idlergear_daemon_broadcast(message, delivery?)` - Broadcast to all agents
- `idlergear_daemon_update_status(agent_id, status)` - Update agent status
- `idlergear_daemon_list_queue()` - List queued commands

## Script Generation (3 tools)

- `idlergear_generate_dev_script(name, command, ...)` - Generate dev environment script
- `idlergear_list_script_templates()` - List available script templates
- `idlergear_get_script_template(template_name)` - Get template details

"""MCP Server for IdlerGear - exposes knowledge management as AI tools."""

import json
import os
import signal
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from idlergear import __version__
from idlergear.config import find_idlergear_root, get_config_value, set_config_value
from idlergear.git import GitServer
from idlergear.pm import ProcessManager

# Global flag for reload request
_reload_requested = False

# Registered agent ID for this MCP server session
# Set when idlergear_daemon_register_agent is called successfully
_registered_agent_id: str | None = None

# PID file for external reload triggers
def _get_pid_file() -> Path:
    """Get path to PID file for this MCP server."""
    return Path("/tmp") / f"idlergear-mcp-{os.getpid()}.pid"


def _write_pid_file() -> None:
    """Write PID file for external reload triggers."""
    pid_file = _get_pid_file()
    pid_file.write_text(str(os.getpid()))


def _cleanup_pid_file() -> None:
    """Remove PID file on exit."""
    try:
        _get_pid_file().unlink(missing_ok=True)
    except Exception:
        pass


def _signal_handler(signum: int, frame: Any) -> None:
    """Handle reload signal (SIGUSR1).

    When we receive SIGUSR1, we flush all output and exec ourselves.
    This replaces the current process with a fresh one, inheriting
    the stdin/stdout file descriptors.
    """
    import sys

    # Flush all output before exec
    sys.stdout.flush()
    sys.stderr.flush()

    # Clean up
    _cleanup_pid_file()

    # Re-execute ourselves
    _do_reload()


def _setup_reload_signal() -> None:
    """Set up signal handler for reload."""
    if hasattr(signal, "SIGUSR1"):
        signal.signal(signal.SIGUSR1, _signal_handler)


def _do_reload() -> None:
    """Reload the MCP server by re-executing the process."""
    # Clean up PID file
    _cleanup_pid_file()

    # Get the executable and arguments
    python = sys.executable

    # Re-execute with the same arguments
    # This replaces the current process completely
    os.execv(python, [python, "-m", "idlergear.mcp_server"] + sys.argv[1:])


# Notes now use backend system via get_backend("note")
from idlergear.projects import (
    add_task_to_project,
    create_project,
    delete_project,
    get_project,
    link_to_github_project,
    list_github_projects,
    list_projects,
    move_task,
    remove_task_from_project,
    sync_project_to_github,
)
# Plans now use backend system via get_backend("plan")
# References now use backend system via get_backend("reference")
from idlergear.runs import get_run_logs, get_run_status, list_runs, start_run, stop_run
from idlergear.search import search_all
from idlergear.backends.registry import get_backend
from idlergear.env import (
    detect_project_type,
    find_virtualenv,
    get_environment_info,
    which_enhanced,
)
from idlergear.fs import FilesystemServer
# Vision now uses backend system via get_backend("vision")

# Initialize filesystem server
fs_server = None

def _get_fs_server() -> FilesystemServer:
    """Get or create filesystem server instance."""
    global fs_server
    if fs_server is None:
        fs_server = FilesystemServer()
    return fs_server

# Initialize servers
git_server = None
pm_server = None

def _get_git_server() -> GitServer:
    """Get or create git server instance."""
    global git_server
    if git_server is None:
        git_server = GitServer()
    return git_server

def _get_pm_server() -> ProcessManager:
    """Get or create process manager instance."""
    global pm_server
    if pm_server is None:
        pm_server = ProcessManager()
    return pm_server

# Create the MCP server with enhanced instructions
server = Server(
    "idlergear",
    instructions="""IdlerGear is a knowledge management system for AI development sessions.

⚡ RECOMMENDED FIRST CALL: idlergear_session_start() ⚡

At the start of EVERY session, call idlergear_session_start() to:
- Load project context (vision, plan, tasks, notes)
- Restore previous session state (current task, working files)
- Get recommendations for what to work on

This ensures perfect session continuity and saves you from asking "where did we leave off?"

At the end of your session, call idlergear_session_end() to save state for next time.

Available tool categories:
- Session Management (4 tools) - Start/end sessions with state persistence
- Context & Knowledge (6 tools) - Vision, plans, tasks, notes, references
- Filesystem (11 tools) - File operations with gitignore support
- Git Integration (18 tools) - Git operations + task linking
- Process Management (11 tools) - System info, process control
- Environment (4 tools) - Python/Node/Rust detection, venv finder
- OpenTelemetry (3 tools) - Log collection and querying

All tools return structured JSON for token efficiency."""
)


def _format_result(data: Any) -> list[TextContent]:
    """Format a result as JSON text content."""
    if data is None:
        return [TextContent(type="text", text="null")]
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


def _check_initialized() -> None:
    """Check if IdlerGear is initialized."""
    if find_idlergear_root() is None:
        raise ValueError("IdlerGear not initialized. Run 'idlergear init' first.")


# Define all tools
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available IdlerGear tools."""
    return [
        # Task tools
        Tool(
            name="idlergear_task_create",
            description="MANDATORY: Create a task. You MUST call this when you: 1) Find a bug (add --label bug), 2) Make a design decision (add --label decision), 3) Leave technical debt (add --label tech-debt), 4) Identify work to be done. NEVER write TODO comments or create TODO.md files - use this tool instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "body": {"type": "string", "description": "Task body/description"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Labels for the task",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Task priority",
                    },
                    "due": {
                        "type": "string",
                        "description": "Due date (YYYY-MM-DD)",
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="idlergear_task_list",
            description="List tasks. CALL AT SESSION START to see open work items. Check this before starting any new work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "enum": ["open", "closed", "all"],
                        "description": "Filter by state",
                        "default": "open",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (for token efficiency)",
                    },
                    "preview": {
                        "type": "boolean",
                        "description": "Strip task bodies for token efficiency (default: false)",
                        "default": False,
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Filter by priority",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_task_show",
            description="Show a task by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Task ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="idlergear_task_close",
            description="Close a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Task ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="idlergear_task_update",
            description="Update a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Task ID"},
                    "title": {"type": "string", "description": "New title"},
                    "body": {"type": "string", "description": "New body"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New labels",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["high", "medium", "low", ""],
                        "description": "Task priority (empty string to clear)",
                    },
                    "due": {
                        "type": "string",
                        "description": "Due date (YYYY-MM-DD, empty string to clear)",
                    },
                },
                "required": ["id"],
            },
        ),
        # Note tools
        Tool(
            name="idlergear_note_create",
            description="MANDATORY: Create a note to persist knowledge for future sessions. CALL THIS WHEN YOU: 1) Discover how something works, 2) Find a quirk or gotcha, 3) Learn an API behavior, 4) Have an idea worth remembering. Use tags: 'explore' for research questions, 'idea' for concepts. This note WILL be available in your next session. NEVER write to NOTES.md, SESSION_*.md - use this tool instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Note content"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags (e.g., ['explore'], ['idea'])",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="idlergear_note_list",
            description="List notes, optionally filtered by tag",
            inputSchema={
                "type": "object",
                "properties": {
                    "tag": {
                        "type": "string",
                        "description": "Filter by tag (e.g., 'explore', 'idea')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (for token efficiency)",
                    },
                    "preview": {
                        "type": "boolean",
                        "description": "Strip note content for token efficiency (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_note_show",
            description="Show a note by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Note ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="idlergear_note_delete",
            description="Delete a note",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Note ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="idlergear_note_promote",
            description="Promote a note to task or reference",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Note ID"},
                    "to": {
                        "type": "string",
                        "enum": ["task", "reference"],
                        "description": "Target type",
                    },
                },
                "required": ["id", "to"],
            },
        ),
        # Exploration tools (deprecated - aliases for notes with 'explore' tag)
        Tool(
            name="idlergear_explore_create",
            description="DEPRECATED: Use idlergear_note_create with tags=['explore'] instead. Creates an exploration note.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Exploration title"},
                    "body": {"type": "string", "description": "Exploration body"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="idlergear_explore_list",
            description="DEPRECATED: Use idlergear_note_list with tag='explore' instead. Lists exploration notes.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_explore_delete",
            description="DEPRECATED: Use idlergear_note_delete instead. Deletes an exploration note.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Note ID to delete"},
                },
                "required": ["id"],
            },
        ),
        # Vision tools
        Tool(
            name="idlergear_vision_show",
            description="REQUIRED AT SESSION START: Show the project vision. You MUST call this or idlergear_context at the beginning of every session to understand project goals. Check this before making any major decisions.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_vision_edit",
            description="Update the project vision",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "New vision content"},
                },
                "required": ["content"],
            },
        ),
        # Plan tools
        Tool(
            name="idlergear_plan_create",
            description="Create a plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plan name (identifier)"},
                    "title": {"type": "string", "description": "Plan title"},
                    "body": {"type": "string", "description": "Plan description"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_plan_list",
            description="List all plans",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Limit number of results"},
                },
            },
        ),
        Tool(
            name="idlergear_plan_show",
            description="Show a plan (current if no name given)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plan name"},
                },
            },
        ),
        Tool(
            name="idlergear_plan_switch",
            description="Switch to a plan",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Plan name"},
                },
                "required": ["name"],
            },
        ),
        # Reference tools
        Tool(
            name="idlergear_reference_add",
            description="Store permanent documentation. USE THIS WHEN YOU: 1) Explain a design decision, 2) Document an API or protocol, 3) Describe architecture that others should understand. References persist across sessions and are searchable.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Reference title"},
                    "body": {"type": "string", "description": "Reference body"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="idlergear_reference_list",
            description="List all reference documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Limit number of results"},
                    "preview": {"type": "boolean", "default": False, "description": "Strip bodies for token efficiency (default: false)"},
                },
            },
        ),
        Tool(
            name="idlergear_reference_show",
            description="Show a reference document",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Reference title"},
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="idlergear_reference_search",
            description="Search reference documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        ),
        # Run tools
        Tool(
            name="idlergear_run_start",
            description="Start a script/command in the background",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to run"},
                    "name": {"type": "string", "description": "Run name"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="idlergear_run_list",
            description="List all runs",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Limit number of results"},
                },
            },
        ),
        Tool(
            name="idlergear_run_status",
            description="Get run status",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_run_logs",
            description="Get run logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                    "tail": {"type": "integer", "description": "Last N lines"},
                    "stream": {
                        "type": "string",
                        "enum": ["stdout", "stderr"],
                        "description": "Log stream",
                        "default": "stdout",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_run_stop",
            description="Stop a running process",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                },
                "required": ["name"],
            },
        ),
        # Config tools
        Tool(
            name="idlergear_config_get",
            description="Get a configuration value",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Config key (dot notation)"},
                },
                "required": ["key"],
            },
        ),
        Tool(
            name="idlergear_config_set",
            description="Set a configuration value",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Config key (dot notation)"},
                    "value": {"type": "string", "description": "Config value"},
                },
                "required": ["key", "value"],
            },
        ),
        # Context tool - session start
        Tool(
            name="idlergear_context",
            description="MANDATORY AT SESSION START: Get project context. You MUST call this at the beginning of EVERY session BEFORE doing any work. Returns vision, current plan, open tasks, explorations, and recent notes. Do NOT skip this step. Default mode is 'minimal' (~750 tokens) for efficiency.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Context verbosity mode (default: minimal). Options: minimal (~750 tokens, session start), standard (~2500 tokens, general dev), detailed (~7000 tokens, deep planning), full (~17000+ tokens, rare use)",
                        "enum": ["minimal", "standard", "detailed", "full"],
                        "default": "minimal",
                    },
                    "include_refs": {
                        "type": "boolean",
                        "description": "Include reference documents (overridden by mode in minimal/standard)",
                        "default": False,
                    },
                },
            },
        ),
        # Status tool - quick project overview
        Tool(
            name="idlergear_status",
            description="Get quick project status dashboard (tasks, notes, runs, git). Use this for a quick overview of current state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "description": "Show detailed dashboard",
                        "default": False,
                    },
                },
            },
        ),
        # Search tool
        Tool(
            name="idlergear_search",
            description="PREFER THIS over file search. Search across all IdlerGear knowledge (tasks, notes, references, plans). Use this BEFORE searching files when looking for project information, decisions, or context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["task", "note", "reference", "plan"],
                        },
                        "description": "Types to search (default: all)",
                    },
                },
                "required": ["query"],
            },
        ),
        # Backend configuration tool
        Tool(
            name="idlergear_backend_show",
            description="Show configured backends for all knowledge types",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_backend_set",
            description="Set the backend for a knowledge type",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["task", "note", "reference", "plan", "vision"],
                        "description": "Knowledge type to configure",
                    },
                    "backend": {
                        "type": "string",
                        "description": "Backend name (e.g., local, github)",
                    },
                },
                "required": ["type", "backend"],
            },
        ),
        # Server management tools
        Tool(
            name="idlergear_version",
            description="Show IdlerGear MCP server version and PID",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_reload",
            description="Reload the IdlerGear MCP server to pick up code changes. Call this after IdlerGear has been updated (e.g., after git pull or pip install) to use the new version without restarting Claude Code. The server will re-execute itself with the latest code.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # Project tools (Kanban boards)
        Tool(
            name="idlergear_project_create",
            description="Create a Kanban project board for organizing tasks into columns. Use this to track work across stages (Backlog, In Progress, Review, Done). Optionally syncs to GitHub Projects v2.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Project title"},
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Custom columns (default: Backlog, In Progress, Review, Done)",
                    },
                    "create_on_github": {
                        "type": "boolean",
                        "description": "Also create on GitHub Projects v2",
                        "default": False,
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="idlergear_project_list",
            description="List all project boards",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_github": {
                        "type": "boolean",
                        "description": "Also list GitHub Projects",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_project_show",
            description="Show a project board with all columns and tasks",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name or slug"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_project_delete",
            description="Delete a project board",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name or slug"},
                    "delete_on_github": {
                        "type": "boolean",
                        "description": "Also delete from GitHub",
                        "default": False,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_project_add_task",
            description="Add a task to a project board column",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Project name or slug"},
                    "task_id": {"type": "string", "description": "Task ID to add"},
                    "column": {"type": "string", "description": "Target column (default: first column)"},
                },
                "required": ["project_name", "task_id"],
            },
        ),
        Tool(
            name="idlergear_project_remove_task",
            description="Remove a task from a project board",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Project name or slug"},
                    "task_id": {"type": "string", "description": "Task ID to remove"},
                },
                "required": ["project_name", "task_id"],
            },
        ),
        Tool(
            name="idlergear_project_move_task",
            description="Move a task to a different column in the project board",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Project name or slug"},
                    "task_id": {"type": "string", "description": "Task ID to move"},
                    "column": {"type": "string", "description": "Target column"},
                },
                "required": ["project_name", "task_id", "column"],
            },
        ),
        Tool(
            name="idlergear_project_sync",
            description="Sync a local project to GitHub Projects v2",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name or slug"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_project_link",
            description="Link a local project to an existing GitHub Project",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Local project name or slug"},
                    "github_project_number": {"type": "integer", "description": "GitHub Project number"},
                },
                "required": ["name", "github_project_number"],
            },
        ),
        # Daemon coordination tools
        Tool(
            name="idlergear_daemon_register_agent",
            description="Register an AI agent with the daemon for multi-agent coordination. Returns agent ID for future operations. Use this when starting work on a codebase to enable coordination with other AI assistants.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Agent name (e.g., 'Claude Code Session', 'Goose Terminal')"},
                    "agent_type": {"type": "string", "description": "Agent type (e.g., 'claude-code', 'goose', 'aider')"},
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (optional)",
                        "additionalProperties": True,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_daemon_list_agents",
            description="List all active AI agents registered with the daemon. Use this to see what other AI assistants are working on the codebase.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_daemon_queue_command",
            description="Queue a command for execution by any available AI agent. Use this to delegate work to other agents or queue long-running tasks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "priority": {"type": "integer", "description": "Priority (higher = more urgent, default: 1)"},
                    "wait_for_result": {"type": "boolean", "description": "Wait for command completion (default: False)"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="idlergear_daemon_broadcast",
            description="Broadcast a message to all active AI agents. Use this to coordinate work across multiple AI assistants. For sending to a specific agent, use idlergear_message_send instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message to broadcast to all agents"},
                    "delivery": {
                        "type": "string",
                        "enum": ["context", "notification", "deferred"],
                        "description": "Delivery type for all recipients (default: notification)",
                        "default": "notification",
                    },
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="idlergear_daemon_update_status",
            description="Update agent status (active/idle/busy). Use this to signal your current state to other agents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID from registration"},
                    "status": {
                        "type": "string",
                        "enum": ["active", "idle", "busy"],
                        "description": "New status",
                    },
                },
                "required": ["agent_id", "status"],
            },
        ),
        Tool(
            name="idlergear_daemon_list_queue",
            description="List queued commands awaiting execution. Shows what work is pending across all agents.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # Cross-agent messaging tools (inbox-based, works without persistent connections)
        Tool(
            name="idlergear_message_send",
            description="""Send a message to another AI agent's inbox. Messages are routed by delivery type:
- context: Injected into recipient's context (they will see and act on it)
- notification (default): Converted to a task with [message] label (informational)
- deferred: Queued for end-of-session review

Use 'all' as to_agent to broadcast to all registered agents.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "to_agent": {"type": "string", "description": "Target agent ID (e.g., 'claude-code-abc123') or 'all' to broadcast"},
                    "message": {"type": "string", "description": "Message content - can be a request, question, or information"},
                    "delivery": {
                        "type": "string",
                        "enum": ["context", "notification", "deferred"],
                        "description": "Delivery type: context=inject into context, notification=create task, deferred=queue for later (default: notification)",
                    },
                    "message_type": {
                        "type": "string",
                        "enum": ["info", "request", "alert", "question"],
                        "description": "Message type: info, request, alert, or question (default: info)",
                    },
                    "action_requested": {"type": "boolean", "description": "Whether you need the recipient to DO something (default: false)"},
                    "context": {
                        "type": "object",
                        "description": "Related context (e.g., {task_id: 45, files: ['api.py']})",
                    },
                    "from_agent": {"type": "string", "description": "Your agent ID (optional, auto-detected if registered)"},
                },
                "required": ["to_agent", "message"],
            },
        ),
        Tool(
            name="idlergear_message_process",
            description="""Process inbox messages and route by delivery type. Call this at session start to:
- Inject context messages into your context (returns them)
- Convert notification messages to tasks with [message] label
- Queue deferred messages for later review

This ensures messages don't derail your work - only context ones are shown immediately.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Your agent ID (optional, auto-detected)"},
                    "create_tasks": {"type": "boolean", "description": "Create tasks for normal-priority messages (default: true)"},
                },
            },
        ),
        Tool(
            name="idlergear_message_list",
            description="Check your inbox for messages from other AI agents. Call this at session start to see if other agents have sent you requests.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Your agent ID (optional, uses registered ID if available)"},
                    "unread_only": {"type": "boolean", "description": "Only show unread messages (default: true)", "default": True},
                    "delivery": {
                        "type": "string",
                        "enum": ["context", "notification", "deferred"],
                        "description": "Filter by delivery type",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results (for token efficiency)",
                    },
                    "preview": {
                        "type": "boolean",
                        "description": "Strip message content, show only metadata (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_message_mark_read",
            description="Mark messages as read after processing them.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Your agent ID"},
                    "message_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Message IDs to mark as read (omit to mark all)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_message_clear",
            description="Clear read messages from your inbox.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Your agent ID"},
                    "all_messages": {"type": "boolean", "description": "Clear all messages, not just read ones (default: false)"},
                },
            },
        ),
        Tool(
            name="idlergear_message_test",
            description="Test messaging by sending a message to yourself and retrieving it. This exercises the full messaging pipeline: send_message() -> inbox storage -> list_messages(). Use this to verify messaging is working correctly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_message": {
                        "type": "string",
                        "description": "Custom test message content (optional, defaults to a timestamp-based message)",
                    },
                },
            },
        ),
        # Script generation tools
        Tool(
            name="idlergear_generate_dev_script",
            description="Generate a shell script that sets up a dev environment, registers with daemon, and streams logs. Use this to create standardized setup scripts for long-running processes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Script name (e.g., 'backend-server')"},
                    "command": {"type": "string", "description": "Command to run (e.g., 'python manage.py runserver')"},
                    "template": {
                        "type": "string",
                        "enum": ["pytest", "django-dev", "flask-dev", "jupyter", "fastapi-dev"],
                        "description": "Use a pre-built template (optional)",
                    },
                    "venv_path": {"type": "string", "description": "Virtual environment path (e.g., './venv')"},
                    "requirements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Python packages to install (e.g., ['flask', 'pytest'])",
                    },
                    "env_vars": {
                        "type": "object",
                        "description": "Environment variables to set (e.g., {'FLASK_ENV': 'development'})",
                        "additionalProperties": {"type": "string"},
                    },
                    "stream_logs": {
                        "type": "boolean",
                        "description": "Enable log streaming to daemon (default: False)",
                    },
                },
                "required": ["name", "command"],
            },
        ),
        Tool(
            name="idlergear_list_script_templates",
            description="List all available script templates with their descriptions. Use this to see what pre-built templates are available.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_get_script_template",
            description="Get details about a specific script template. Shows what the template includes and how to use it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_name": {"type": "string", "description": "Template name"},
                },
                "required": ["template_name"],
            },
        ),
        # Environment detection tools
        Tool(
            name="idlergear_env_info",
            description="Get consolidated environment information (Python, Node, Rust, .NET versions, virtual environments, PATH). This provides ~60% token savings vs running multiple commands separately! Use this to quickly understand the development environment.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="idlergear_env_which",
            description="Enhanced 'which' command showing ALL matches for a command across PATH, not just the first one. Useful for debugging PATH issues and finding all installed versions of a tool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command name to search for"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="idlergear_env_detect",
            description="Detect project type based on files present (Python, Node, Rust, .NET, Go, Java, Ruby). Useful for understanding what kind of project you're working in.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Project directory to analyze (default: current directory)"},
                },
            },
        ),
        Tool(
            name="idlergear_env_find_venv",
            description="Find and identify virtual environments in the project directory. Detects venv, poetry, pipenv automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Project directory to search (default: current directory)"},
                },
            },
        ),
        # Filesystem tools
        Tool(
            name="idlergear_fs_read_file",
            description="Read file contents. Returns content, path, and size. Use this instead of cat or Read tool for better performance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_fs_read_multiple",
            description="Read multiple files at once. More efficient than calling read_file multiple times.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths",
                    },
                },
                "required": ["paths"],
            },
        ),
        Tool(
            name="idlergear_fs_write_file",
            description="Write file contents. Creates parent directories if needed. Use this instead of Write tool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to file"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="idlergear_fs_create_directory",
            description="Create directory and parent directories if needed. Use this instead of mkdir.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to directory"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_fs_list_directory",
            description="List directory contents with metadata (size, modified time). Excludes common patterns (.git, __pycache__, etc) automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (default: current directory)", "default": "."},
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional patterns to exclude (gitignore-style)",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_fs_directory_tree",
            description="Generate recursive directory tree structure. Returns nested JSON with file/directory metadata. Much more efficient than recursive ls.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Root directory (default: current)", "default": "."},
                    "max_depth": {"type": "integer", "description": "Maximum recursion depth (default: 3)", "default": 3},
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Patterns to exclude",
                    },
                },
            },
        ),
        Tool(
            name="idlergear_fs_move_file",
            description="Move or rename file/directory. Use this instead of mv.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source path"},
                    "destination": {"type": "string", "description": "Destination path"},
                },
                "required": ["source", "destination"],
            },
        ),
        Tool(
            name="idlergear_fs_search_files",
            description="Search for files matching glob pattern. Respects .gitignore automatically. Much faster than find.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Root directory to search (default: current)", "default": "."},
                    "pattern": {"type": "string", "description": "Glob pattern (e.g., '*.py', 'test_*.py')", "default": "*"},
                    "exclude_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional patterns to exclude",
                    },
                    "use_gitignore": {"type": "boolean", "description": "Respect .gitignore files (default: true)", "default": True},
                },
            },
        ),
        Tool(
            name="idlergear_fs_file_info",
            description="Get file metadata (size, timestamps, permissions). Use this instead of stat.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_fs_file_checksum",
            description="Calculate file checksum (MD5, SHA1, SHA256). Useful for verifying file integrity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "algorithm": {
                        "type": "string",
                        "enum": ["md5", "sha1", "sha256"],
                        "description": "Hash algorithm (default: sha256)",
                        "default": "sha256",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="idlergear_fs_allowed_directories",
            description="List all directories that can be accessed by filesystem operations. Security boundary check.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # Git tools
        Tool(
            name="idlergear_git_status",
            description="Get git repository status with structured output (branch, ahead/behind, staged/modified/untracked files). Much more efficient than parsing 'git status' output!",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Repository path (default: current directory)"},
                },
            },
        ),
        Tool(
            name="idlergear_git_diff",
            description="Get git diff with configurable context lines and file filtering. Supports both staged and unstaged changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "staged": {"type": "boolean", "description": "Show staged changes (git diff --cached)", "default": False},
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Specific files to diff"},
                    "context_lines": {"type": "integer", "description": "Number of context lines", "default": 3},
                },
            },
        ),
        Tool(
            name="idlergear_git_log",
            description="Get git commit history with structured output. Supports filtering by date, author, and commit message.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "max_count": {"type": "integer", "description": "Maximum number of commits", "default": 10},
                    "since": {"type": "string", "description": "Show commits since date"},
                    "until": {"type": "string", "description": "Show commits until date"},
                    "author": {"type": "string", "description": "Filter by author"},
                    "grep": {"type": "string", "description": "Filter by commit message"},
                },
            },
        ),
        Tool(
            name="idlergear_git_add",
            description="Stage files for commit. Supports staging specific files or all changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Files to stage"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "all": {"type": "boolean", "description": "Stage all changes (git add -A)", "default": False},
                },
                "required": ["files"],
            },
        ),
        Tool(
            name="idlergear_git_commit",
            description="Create a commit. Optionally link to an IdlerGear task by providing task_id.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "task_id": {"type": "integer", "description": "Optional task ID to link"},
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="idlergear_git_reset",
            description="Unstage files or reset repository. WARNING: Use hard=true with caution as it discards changes!",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}, "description": "Files to unstage (None = all)"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "hard": {"type": "boolean", "description": "Hard reset (WARNING: discards changes)", "default": False},
                },
            },
        ),
        Tool(
            name="idlergear_git_show",
            description="Show commit details including diff. Use this to inspect a specific commit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "commit": {"type": "string", "description": "Commit hash or reference (e.g., 'HEAD', 'abc123')"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                },
                "required": ["commit"],
            },
        ),
        Tool(
            name="idlergear_git_branch_list",
            description="List all branches with current branch indicator and upstream tracking info.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Repository path"},
                },
            },
        ),
        Tool(
            name="idlergear_git_branch_create",
            description="Create a new branch, optionally checking it out immediately.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Branch name"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "checkout": {"type": "boolean", "description": "Checkout after creation", "default": True},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_git_branch_checkout",
            description="Checkout (switch to) a branch.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Branch name"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_git_branch_delete",
            description="Delete a branch. Use force=true to delete unmerged branches.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Branch name"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "force": {"type": "boolean", "description": "Force delete (even if not merged)", "default": False},
                },
                "required": ["name"],
            },
        ),
        # IdlerGear-specific git+task integration tools
        Tool(
            name="idlergear_git_commit_task",
            description="Commit with automatic task linking (IdlerGear-specific). Automatically stages all changes and links to a task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID to link"},
                    "message": {"type": "string", "description": "Commit message"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "auto_add": {"type": "boolean", "description": "Automatically stage all changes", "default": True},
                },
                "required": ["task_id", "message"],
            },
        ),
        Tool(
            name="idlergear_git_status_for_task",
            description="Get git status filtered by task files (IdlerGear-specific). Shows only files relevant to a specific task.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="idlergear_git_task_commits",
            description="Find all commits linked to a task (IdlerGear-specific). Searches commit messages for task references.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"},
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "max_count": {"type": "integer", "description": "Maximum commits to search", "default": 50},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="idlergear_git_sync_tasks",
            description="Sync task status from commit messages (IdlerGear-specific). Finds tasks mentioned in commits and reports sync summary.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Repository path"},
                    "since": {"type": "string", "description": "Only process commits since this date"},
                },
            },
        ),
        # === Process Management Tools ===
        Tool(
            name="idlergear_pm_list_processes",
            description="List running processes with optional filtering and sorting. Returns structured JSON with PID, name, user, CPU%, memory%, and status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter_name": {"type": "string", "description": "Filter by process name (substring match)"},
                    "filter_user": {"type": "string", "description": "Filter by username"},
                    "sort_by": {"type": "string", "enum": ["cpu", "memory", "pid", "name"], "description": "Sort by field (default: cpu)"},
                },
            },
        ),
        Tool(
            name="idlergear_pm_get_process",
            description="Get detailed information about a specific process by PID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pid": {"type": "integer", "description": "Process ID"},
                },
                "required": ["pid"],
            },
        ),
        Tool(
            name="idlergear_pm_kill_process",
            description="Kill a process by PID. Use SIGTERM by default or SIGKILL with force=true.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pid": {"type": "integer", "description": "Process ID"},
                    "force": {"type": "boolean", "description": "Use SIGKILL instead of SIGTERM"},
                },
                "required": ["pid"],
            },
        ),
        Tool(
            name="idlergear_pm_system_info",
            description="Get system information including CPU, memory, and disk usage.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="idlergear_pm_start_run",
            description="Start a background run (IdlerGear-specific). Executes command in background with stdout/stderr logging.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "name": {"type": "string", "description": "Run name (auto-generated if not provided)"},
                    "task_id": {"type": "integer", "description": "Optional task ID to associate with run"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="idlergear_pm_list_runs",
            description="List all IdlerGear background runs with their status (running/stopped/completed/failed).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="idlergear_pm_get_run_status",
            description="Get detailed status of a specific run including timestamps and log sizes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_pm_get_run_logs",
            description="Get logs from a run (stdout or stderr).",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                    "tail": {"type": "integer", "description": "Number of lines from end (all if not specified)"},
                    "stream": {"type": "string", "enum": ["stdout", "stderr"], "description": "Log stream (default: stdout)"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_pm_stop_run",
            description="Stop a running background process.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Run name"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="idlergear_pm_task_runs",
            description="Get all runs associated with a specific task (IdlerGear-specific).",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Task ID"},
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="idlergear_pm_quick_start",
            description="Start a process in the foreground (not as a background run). Returns immediately with PID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "executable": {"type": "string", "description": "Path to executable or command name"},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "Command arguments"},
                },
                "required": ["executable"],
            },
        ),
        # === OpenTelemetry Log Tools ===
        Tool(
            name="idlergear_otel_query_logs",
            description="Query OpenTelemetry logs with filtering, full-text search, and time range. Returns structured log entries with severity, service, message, attributes, and trace context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "description": "Filter by severity (DEBUG, INFO, WARN, ERROR, FATAL)", "enum": ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]},
                    "service": {"type": "string", "description": "Filter by service name (e.g., 'goose', 'claude-code')"},
                    "start_time": {"type": "string", "description": "Start time (ISO format or relative like '1h', '30m', '24h')"},
                    "end_time": {"type": "string", "description": "End time (ISO format)"},
                    "search": {"type": "string", "description": "Full-text search query (searches message field)"},
                    "limit": {"type": "integer", "description": "Maximum number of results (default: 100)"},
                },
            },
        ),
        Tool(
            name="idlergear_otel_stats",
            description="Get statistics about collected OpenTelemetry logs including total count, severity breakdown, service breakdown, and recent activity.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="idlergear_otel_recent_errors",
            description="Get recent ERROR and FATAL logs (last N entries). Useful for quickly checking for problems.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of recent errors to return (default: 20)"},
                    "service": {"type": "string", "description": "Filter by service name"},
                },
            },
        ),
        # === Session Management Tools ===
        Tool(
            name="idlergear_session_start",
            description="⚡ RECOMMENDED FIRST CALL ⚡ Start a new session by loading project context AND previous session state (current task, working files, notes). This is the BEST way to begin any session - combines context loading with session continuity. Returns context + session state + recommendations for what to work on.",
            inputSchema={
                "type": "object",
                "properties": {
                    "context_mode": {
                        "type": "string",
                        "description": "Context verbosity (minimal=570 tokens [DEFAULT], standard=7K, detailed=11K, full=17K)",
                        "enum": ["minimal", "standard", "detailed", "full"],
                    },
                    "load_state": {"type": "boolean", "description": "Load previous session state (default: true)"},
                },
            },
        ),
        Tool(
            name="idlergear_session_save",
            description="Save current session state (task, files, notes) for next session. Call this before ending work to enable session continuity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "current_task_id": {"type": "integer", "description": "ID of task currently being worked on"},
                    "working_files": {"type": "array", "items": {"type": "string"}, "description": "List of files currently being edited"},
                    "notes": {"type": "string", "description": "Free-form notes about current session (what was accomplished, next steps, etc.)"},
                },
            },
        ),
        Tool(
            name="idlergear_session_end",
            description="End current session - saves state and provides suggestions for next session. Convenience wrapper for session_save with auto-suggestions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "current_task_id": {"type": "integer", "description": "ID of task being worked on"},
                    "working_files": {"type": "array", "items": {"type": "string"}, "description": "Files being worked on"},
                    "notes": {"type": "string", "description": "Session notes"},
                },
            },
        ),
        Tool(
            name="idlergear_session_status",
            description="Get current session state summary (task, files, notes, timestamp).",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # === Watch Mode Tools ===
        Tool(
            name="idlergear_watch_check",
            description="Analyze project for issues: TODO/FIXME/HACK comments in diff, uncommitted changes, stale references. Returns suggestions for knowledge capture. Use --act to automatically create tasks from TODOs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "act": {
                        "type": "boolean",
                        "description": "Automatically create tasks from TODO/FIXME/HACK comments (default: false)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="idlergear_watch_act",
            description="Execute action for a specific suggestion from watch_check. Use this to selectively act on individual suggestions (e.g., create a task from a specific TODO comment).",
            inputSchema={
                "type": "object",
                "properties": {
                    "suggestion_id": {
                        "type": "string",
                        "description": "Suggestion ID from watch_check results (e.g., 's1', 's2')",
                    },
                },
                "required": ["suggestion_id"],
            },
        ),
        Tool(
            name="idlergear_watch_stats",
            description="Get quick watch statistics: changed files/lines, TODO/FIXME/HACK counts, time since last commit.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        _check_initialized()

        # Task handlers - use configured backend
        if name == "idlergear_task_create":
            backend = get_backend("task")
            result = backend.create(
                arguments["title"],
                body=arguments.get("body"),
                labels=arguments.get("labels"),
                priority=arguments.get("priority"),
                due=arguments.get("due"),
            )
            return _format_result(result)

        elif name == "idlergear_task_list":
            backend = get_backend("task")
            result = backend.list(state=arguments.get("state", "open"))
            # Filter by priority if specified
            priority = arguments.get("priority")
            if priority:
                result = [t for t in result if t.get("priority") == priority]
            # Apply limit if specified
            limit = arguments.get("limit")
            if limit:
                result = result[:limit]
            # Strip bodies if preview mode (token-efficient)
            if arguments.get("preview", False):
                for task in result:
                    task["body"] = None
            return _format_result(result)

        elif name == "idlergear_task_show":
            backend = get_backend("task")
            result = backend.get(arguments["id"])
            if result is None:
                raise ValueError(f"Task #{arguments['id']} not found")
            return _format_result(result)

        elif name == "idlergear_task_close":
            backend = get_backend("task")
            result = backend.close(arguments["id"])
            if result is None:
                raise ValueError(f"Task #{arguments['id']} not found")
            return _format_result(result)

        elif name == "idlergear_task_update":
            backend = get_backend("task")
            result = backend.update(
                arguments["id"],
                title=arguments.get("title"),
                body=arguments.get("body"),
                labels=arguments.get("labels"),
                priority=arguments.get("priority"),
                due=arguments.get("due"),
            )
            if result is None:
                raise ValueError(f"Task #{arguments['id']} not found")
            return _format_result(result)

        # Note handlers (using backend)
        elif name == "idlergear_note_create":
            backend = get_backend("note")
            result = backend.create(
                arguments["content"],
                tags=arguments.get("tags"),
            )
            return _format_result(result)

        elif name == "idlergear_note_list":
            backend = get_backend("note")
            result = backend.list(tag=arguments.get("tag"))
            limit = arguments.get("limit")
            preview = arguments.get("preview", False)
            if limit and len(result) > limit:
                result = result[:limit]
            if preview:
                result = [{"id": n.get("id"), "tags": n.get("tags", []), "created": n.get("created")} for n in result]
            return _format_result(result)

        elif name == "idlergear_note_show":
            backend = get_backend("note")
            result = backend.get(arguments["id"])
            if result is None:
                raise ValueError(f"Note #{arguments['id']} not found")
            return _format_result(result)

        elif name == "idlergear_note_delete":
            backend = get_backend("note")
            if not backend.delete(arguments["id"]):
                raise ValueError(f"Note #{arguments['id']} not found")
            return _format_result({"deleted": True, "id": arguments["id"]})

        elif name == "idlergear_note_promote":
            backend = get_backend("note")
            result = backend.promote(arguments["id"], arguments["to"])
            if result is None:
                raise ValueError(f"Note #{arguments['id']} not found")
            return _format_result(result)

        # Exploration handlers (deprecated - redirect to notes with 'explore' tag)
        elif name == "idlergear_explore_create":
            # Combine title and body into note content
            content = arguments["title"]
            if arguments.get("body"):
                content = f"{content}\n\n{arguments['body']}"
            backend = get_backend("note")
            result = backend.create(content, tags=["explore"])
            result["deprecated"] = "Use idlergear_note_create with tags=['explore'] instead"
            return _format_result(result)

        elif name == "idlergear_explore_list":
            backend = get_backend("note")
            notes = backend.list(tag="explore")
            result = {
                "notes": notes,
                "deprecated": "Use idlergear_note_list with tag='explore' instead",
            }
            return _format_result(result)

        elif name == "idlergear_explore_delete":
            note_id = arguments["id"]
            backend = get_backend("note")
            success = backend.delete(note_id)
            result = {
                "deleted": success,
                "deprecated": "Use idlergear_note_delete instead",
            }
            if not success:
                result["error"] = f"Note #{note_id} not found"
            return _format_result(result)

        # Vision handlers (using backend)
        elif name == "idlergear_vision_show":
            backend = get_backend("vision")
            result = backend.get()
            return _format_result({"content": result})

        elif name == "idlergear_vision_edit":
            backend = get_backend("vision")
            backend.set(arguments["content"])
            return _format_result({"updated": True})

        # Plan handlers (using backend)
        elif name == "idlergear_plan_create":
            backend = get_backend("plan")
            result = backend.create(
                arguments["name"],
                title=arguments.get("title"),
                body=arguments.get("body"),
            )
            return _format_result(result)

        elif name == "idlergear_plan_list":
            backend = get_backend("plan")
            result = backend.list()
            # Apply limit if specified
            limit = arguments.get("limit")
            if limit:
                result = result[:limit]
            return _format_result(result)

        elif name == "idlergear_plan_show":
            backend = get_backend("plan")
            name_arg = arguments.get("name")
            if name_arg:
                result = backend.get(name_arg)
            else:
                result = backend.get_current()
            return _format_result(result)

        elif name == "idlergear_plan_switch":
            backend = get_backend("plan")
            result = backend.switch(arguments["name"])
            if result is None:
                raise ValueError(f"Plan '{arguments['name']}' not found")
            return _format_result(result)

        # Reference handlers (using backend)
        elif name == "idlergear_reference_add":
            backend = get_backend("reference")
            result = backend.add(
                arguments["title"],
                body=arguments.get("body"),
            )
            return _format_result(result)

        elif name == "idlergear_reference_list":
            backend = get_backend("reference")
            result = backend.list()
            # Apply limit if specified
            limit = arguments.get("limit")
            if limit:
                result = result[:limit]
            # Strip bodies if preview mode (token-efficient)
            if arguments.get("preview", False):
                for ref in result:
                    ref["body"] = None
            return _format_result(result)

        elif name == "idlergear_reference_show":
            backend = get_backend("reference")
            result = backend.get(arguments["title"])
            if result is None:
                raise ValueError(f"Reference '{arguments['title']}' not found")
            return _format_result(result)

        elif name == "idlergear_reference_search":
            backend = get_backend("reference")
            result = backend.search(arguments["query"])
            return _format_result(result)

        # Run handlers
        elif name == "idlergear_run_start":
            result = start_run(
                arguments["command"],
                name=arguments.get("name"),
            )
            return _format_result(result)

        elif name == "idlergear_run_list":
            result = list_runs()
            # Apply limit if specified
            limit = arguments.get("limit")
            if limit:
                result = result[:limit]
            return _format_result(result)

        elif name == "idlergear_run_status":
            result = get_run_status(arguments["name"])
            if result is None:
                raise ValueError(f"Run '{arguments['name']}' not found")
            return _format_result(result)

        elif name == "idlergear_run_logs":
            result = get_run_logs(
                arguments["name"],
                tail=arguments.get("tail"),
                stream=arguments.get("stream", "stdout"),
            )
            if result is None:
                raise ValueError(f"Run '{arguments['name']}' not found")
            return _format_result({"logs": result})

        elif name == "idlergear_run_stop":
            if not stop_run(arguments["name"]):
                raise ValueError(f"Run '{arguments['name']}' is not running or not found")
            return _format_result({"stopped": True, "name": arguments["name"]})

        # Config handlers
        elif name == "idlergear_config_get":
            result = get_config_value(arguments["key"])
            return _format_result({"key": arguments["key"], "value": result})

        elif name == "idlergear_config_set":
            set_config_value(arguments["key"], arguments["value"])
            return _format_result(
                {"key": arguments["key"], "value": arguments["value"], "set": True}
            )

        # Context handler
        elif name == "idlergear_context":
            from idlergear.context import format_context_json, gather_context

            ctx = gather_context(
                include_references=arguments.get("include_refs", False),
                mode=arguments.get("mode", "minimal"),
            )
            return _format_result(format_context_json(ctx))

        # Status handler
        elif name == "idlergear_status":
            from idlergear.status import get_project_status

            status = get_project_status()
            if arguments.get("detailed", False):
                from idlergear.status import format_detailed_status
                return _format_result({"detailed": format_detailed_status(status)})
            else:
                return _format_result({
                    "summary": status.summary(),
                    **status.to_dict()
                })

        # Search handler
        elif name == "idlergear_search":
            result = search_all(
                arguments["query"],
                types=arguments.get("types"),
            )
            return _format_result(result)

        # Backend handlers
        elif name == "idlergear_backend_show":
            from idlergear.backends import get_configured_backend_name, list_available_backends

            all_types = ["task", "note", "reference", "plan", "vision"]
            result = {}
            for t in all_types:
                result[t] = {
                    "current": get_configured_backend_name(t),
                    "available": list_available_backends(t),
                }
            return _format_result(result)

        elif name == "idlergear_backend_set":
            from idlergear.backends import list_available_backends

            backend_type = arguments["type"]
            backend_name = arguments["backend"]

            available = list_available_backends(backend_type)
            if backend_name not in available:
                raise ValueError(
                    f"Unknown backend '{backend_name}' for {backend_type}. "
                    f"Available: {', '.join(available)}"
                )

            set_config_value(f"backends.{backend_type}", backend_name)
            return _format_result({
                "type": backend_type,
                "backend": backend_name,
                "set": True,
            })

        # Server management handlers
        elif name == "idlergear_version":
            return _format_result({
                "version": __version__,
                "pid": os.getpid(),
                "python": sys.executable,
            })

        elif name == "idlergear_reload":
            import threading
            import time

            def delayed_reload():
                """Send reload signal after a short delay to allow response to be sent."""
                time.sleep(0.1)  # Wait for response to be flushed
                if hasattr(signal, "SIGUSR1"):
                    os.kill(os.getpid(), signal.SIGUSR1)

            # Start delayed reload in background thread
            threading.Thread(target=delayed_reload, daemon=True).start()

            return _format_result({
                "status": "reload_triggered",
                "message": "MCP server will reload in 100ms. The new version will be active for subsequent tool calls.",
                "current_version": __version__,
                "pid": os.getpid(),
            })

        # Project handlers
        elif name == "idlergear_project_create":
            result = create_project(
                arguments["title"],
                columns=arguments.get("columns"),
                create_on_github=arguments.get("create_on_github", False),
            )
            return _format_result(result)

        elif name == "idlergear_project_list":
            projects = list_projects()
            result = {"projects": projects}
            if arguments.get("include_github"):
                result["github_projects"] = list_github_projects()
            return _format_result(result)

        elif name == "idlergear_project_show":
            result = get_project(arguments["name"])
            if result is None:
                raise ValueError(f"Project '{arguments['name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_delete":
            if not delete_project(
                arguments["name"],
                delete_on_github=arguments.get("delete_on_github", False),
            ):
                raise ValueError(f"Project '{arguments['name']}' not found")
            return _format_result({"deleted": True, "name": arguments["name"]})

        elif name == "idlergear_project_add_task":
            result = add_task_to_project(
                arguments["project_name"],
                arguments["task_id"],
                column=arguments.get("column"),
            )
            if result is None:
                raise ValueError(f"Project '{arguments['project_name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_remove_task":
            result = remove_task_from_project(
                arguments["project_name"],
                arguments["task_id"],
            )
            if result is None:
                raise ValueError(f"Project '{arguments['project_name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_move_task":
            result = move_task(
                arguments["project_name"],
                arguments["task_id"],
                arguments["column"],
            )
            if result is None:
                raise ValueError(f"Project '{arguments['project_name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_sync":
            result = sync_project_to_github(arguments["name"])
            if result is None:
                raise ValueError(f"Project '{arguments['name']}' not found")
            return _format_result(result)

        elif name == "idlergear_project_link":
            result = link_to_github_project(
                arguments["name"],
                arguments["github_project_number"],
            )
            if result is None:
                raise ValueError(f"Project '{arguments['name']}' not found")
            return _format_result(result)

        # Daemon coordination handlers
        elif name == "idlergear_daemon_register_agent":
            global _registered_agent_id
            from idlergear.daemon.mcp_handlers import handle_register_agent
            result = handle_register_agent(arguments)
            # Store the agent_id for use in message operations
            if "agent_id" in result:
                _registered_agent_id = result["agent_id"]
            return _format_result(result)

        elif name == "idlergear_daemon_list_agents":
            from idlergear.daemon.mcp_handlers import handle_list_agents
            result = handle_list_agents()
            return _format_result(result)

        elif name == "idlergear_daemon_queue_command":
            from idlergear.daemon.mcp_handlers import handle_queue_command
            result = handle_queue_command(arguments)
            return _format_result(result)

        elif name == "idlergear_daemon_broadcast":
            from idlergear.daemon.mcp_handlers import handle_send_message
            result = handle_send_message(arguments)
            return _format_result(result)

        elif name == "idlergear_daemon_update_status":
            from idlergear.daemon.mcp_handlers import handle_update_status
            result = handle_update_status(arguments)
            return _format_result(result)

        elif name == "idlergear_daemon_list_queue":
            from idlergear.daemon.mcp_handlers import handle_list_queue
            result = handle_list_queue()
            return _format_result(result)

        # Cross-agent messaging handlers (inbox-based)
        elif name == "idlergear_message_send":
            from idlergear.messaging import send_message
            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"

            # Auto-detect from_agent if not provided
            from_agent = arguments.get("from_agent")
            if not from_agent:
                # Use registered agent_id if available
                from_agent = _registered_agent_id
            if not from_agent:
                # Fallback: try to find from presence files
                agents_dir = idlergear_dir / "agents"
                if agents_dir.exists():
                    for f in agents_dir.glob("*.json"):
                        if f.name != "agents.json":
                            from_agent = f.stem
                            break

            result = send_message(
                idlergear_dir,
                to_agent=arguments["to_agent"],
                message=arguments["message"],
                from_agent=from_agent,
                delivery=arguments.get("delivery"),
                message_type=arguments.get("message_type", "info"),
                action_requested=arguments.get("action_requested", False),
                context=arguments.get("context"),
            )
            return _format_result(result)

        elif name == "idlergear_message_process":
            from idlergear.messaging import process_inbox, format_context_for_injection
            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"

            # Auto-detect agent_id
            agent_id = arguments.get("agent_id")
            if not agent_id:
                # Use registered agent_id if available
                agent_id = _registered_agent_id
            if not agent_id:
                # Fallback: try to find from presence files
                agents_dir = idlergear_dir / "agents"
                if agents_dir.exists():
                    for f in agents_dir.glob("*.json"):
                        if f.name != "agents.json":
                            agent_id = f.stem
                            break
            if not agent_id:
                return _format_result({"error": "No agent_id provided or detected. Call idlergear_daemon_register_agent first."})

            # Create task callback if requested
            should_create_tasks = arguments.get("create_tasks", True)
            task_callback = None
            if should_create_tasks:
                from idlergear.tasks import create_task as _create_task_for_callback
                def task_callback(title: str, body: str, labels: list[str]) -> int:
                    task = _create_task_for_callback(title, body=body, labels=labels, project_path=root)
                    return task.get("id") if isinstance(task, dict) else task.id

            # Process inbox
            results = process_inbox(idlergear_dir, agent_id, task_callback)

            # Format context messages for injection
            context_text = ""
            if results["context"]:
                context_text = format_context_for_injection(results["context"])

            return _format_result({
                "agent_id": agent_id,
                "context_count": len(results["context"]),
                "context_messages": context_text,
                "tasks_created": results["tasks_created"],
                "queued_for_review": results["queued"],
                "errors": results["errors"],
                "note": "Context messages returned for immediate handling. Notification messages converted to tasks." if results["context"] else "No context messages. Notification messages converted to tasks.",
            })

        elif name == "idlergear_message_list":
            from idlergear.messaging import list_messages, get_inbox_summary, _get_delivery_type
            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"
            agent_id = arguments.get("agent_id")
            if not agent_id:
                # Use registered agent_id if available
                agent_id = _registered_agent_id
            if not agent_id:
                # Fallback: try to find agent_id from presence files
                agents_dir = idlergear_dir / "agents"
                if agents_dir.exists():
                    for f in agents_dir.glob("*.json"):
                        if f.name != "agents.json":
                            agent_id = f.stem
                            break
            if not agent_id:
                return _format_result({"messages": [], "note": "No agent_id provided or detected. Call idlergear_daemon_register_agent first."})

            unread_only = arguments.get("unread_only", True)
            messages = list_messages(idlergear_dir, agent_id, unread_only=unread_only)

            # Filter by delivery type if specified
            delivery_filter = arguments.get("delivery")
            if delivery_filter:
                messages = [m for m in messages if _get_delivery_type(m) == delivery_filter]

            # Apply limit
            limit = arguments.get("limit")
            if limit and len(messages) > limit:
                messages = messages[:limit]

            # Apply preview mode
            preview = arguments.get("preview", False)
            if preview:
                messages = [{
                    "id": m.get("id"),
                    "from": m.get("from"),
                    "delivery": _get_delivery_type(m),
                    "timestamp": m.get("timestamp"),
                    "read": m.get("read", False),
                } for m in messages]

            summary = get_inbox_summary(idlergear_dir, agent_id)
            return _format_result({
                "messages": messages,
                "summary": summary,
                "agent_id": agent_id,
            })

        elif name == "idlergear_message_mark_read":
            from idlergear.messaging import mark_as_read
            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"
            agent_id = arguments.get("agent_id")
            if not agent_id:
                # Use registered agent_id if available
                agent_id = _registered_agent_id
            if not agent_id:
                raise ValueError("agent_id is required. Call idlergear_daemon_register_agent first.")
            message_ids = arguments.get("message_ids")
            count = mark_as_read(idlergear_dir, agent_id, message_ids)
            return _format_result({"marked_read": count})

        elif name == "idlergear_message_clear":
            from idlergear.messaging import clear_inbox
            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"
            agent_id = arguments.get("agent_id")
            if not agent_id:
                # Use registered agent_id if available
                agent_id = _registered_agent_id
            if not agent_id:
                raise ValueError("agent_id is required. Call idlergear_daemon_register_agent first.")
            read_only = not arguments.get("all_messages", False)
            count = clear_inbox(idlergear_dir, agent_id, read_only=read_only)
            return _format_result({"cleared": count})

        elif name == "idlergear_message_test":
            # Test messaging round-trip: send to self, then retrieve
            from datetime import datetime, timezone
            from idlergear.messaging import send_message, list_messages, mark_as_read, get_inbox_summary

            root = find_idlergear_root()
            if not root:
                raise ValueError("IdlerGear not initialized")
            idlergear_dir = root / ".idlergear"

            # Step 1: Use registered agent_id or detect from presence files
            agent_id = _registered_agent_id
            if not agent_id:
                # Fallback: try to find from presence files
                agents_dir = idlergear_dir / "agents"
                if agents_dir.exists():
                    for f in agents_dir.glob("*.json"):
                        if f.name != "agents.json":
                            agent_id = f.stem
                            break

            if not agent_id:
                return _format_result({
                    "success": False,
                    "error": "No agent registered. Call idlergear_daemon_register_agent first.",
                })

            # Step 2: Create test message
            test_content = arguments.get("test_message")
            if not test_content:
                timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                test_content = f"[TEST] Self-test message sent at {timestamp}"

            # Step 3: Send message to self using send_message()
            send_result = send_message(
                idlergear_dir,
                to_agent=agent_id,
                message=test_content,
                from_agent=agent_id,  # From self
                metadata={"test": True, "purpose": "messaging_self_test"},
            )

            # Step 4: Retrieve messages using list_messages()
            messages = list_messages(idlergear_dir, agent_id, unread_only=False, limit=10)

            # Step 5: Find our test message
            test_message_found = None
            for msg in messages:
                if msg.get("id") == send_result["message_id"]:
                    test_message_found = msg
                    break

            # Step 6: Get inbox summary using get_inbox_summary()
            summary = get_inbox_summary(idlergear_dir, agent_id)

            # Step 7: Mark test message as read using mark_as_read()
            if test_message_found:
                marked = mark_as_read(idlergear_dir, agent_id, [send_result["message_id"]])
            else:
                marked = 0

            # Return comprehensive results
            return _format_result({
                "success": test_message_found is not None,
                "agent_id": agent_id,
                "steps": {
                    "1_send": {
                        "function": "send_message()",
                        "result": send_result,
                    },
                    "2_list": {
                        "function": "list_messages()",
                        "messages_retrieved": len(messages),
                        "test_message_found": test_message_found is not None,
                    },
                    "3_summary": {
                        "function": "get_inbox_summary()",
                        "result": summary,
                    },
                    "4_mark_read": {
                        "function": "mark_as_read()",
                        "marked_count": marked,
                    },
                },
                "test_message": test_message_found,
                "note": "All messaging functions exercised successfully" if test_message_found else "Test message not found after sending",
            })

        # Script generation handlers
        elif name == "idlergear_generate_dev_script":
            from idlergear.daemon.script_handlers import handle_generate_script
            result = handle_generate_script(arguments)
            return _format_result(result)

        elif name == "idlergear_list_script_templates":
            from idlergear.daemon.script_handlers import handle_list_templates
            result = handle_list_templates()
            return _format_result(result)

        elif name == "idlergear_get_script_template":
            from idlergear.daemon.script_handlers import handle_get_template
            result = handle_get_template(arguments)
            return _format_result(result)

        # Environment detection handlers
        elif name == "idlergear_env_info":
            result = get_environment_info()
            return _format_result(result)

        elif name == "idlergear_env_which":
            result = which_enhanced(arguments["command"])
            return _format_result(result)

        elif name == "idlergear_env_detect":
            from pathlib import Path
            path = Path(arguments["path"]) if arguments.get("path") else None
            result = detect_project_type(path)
            return _format_result(result)

        elif name == "idlergear_env_find_venv":
            from pathlib import Path
            path = Path(arguments["path"]) if arguments.get("path") else None
            result = find_virtualenv(path)
            if result is None:
                result = {"found": False, "message": "No virtual environment detected"}
            return _format_result(result)

        # Filesystem handlers
        elif name == "idlergear_fs_read_file":
            fs = _get_fs_server()
            result = fs.read_file(arguments["path"])
            return _format_result(result)

        elif name == "idlergear_fs_read_multiple":
            fs = _get_fs_server()
            result = fs.read_multiple_files(arguments["paths"])
            return _format_result(result)

        elif name == "idlergear_fs_write_file":
            fs = _get_fs_server()
            result = fs.write_file(arguments["path"], arguments["content"])
            return _format_result(result)

        elif name == "idlergear_fs_create_directory":
            fs = _get_fs_server()
            result = fs.create_directory(arguments["path"])
            return _format_result(result)

        elif name == "idlergear_fs_list_directory":
            fs = _get_fs_server()
            result = fs.list_directory(
                path=arguments.get("path", "."),
                exclude_patterns=arguments.get("exclude_patterns")
            )
            return _format_result(result)

        elif name == "idlergear_fs_directory_tree":
            fs = _get_fs_server()
            result = fs.directory_tree(
                path=arguments.get("path", "."),
                max_depth=arguments.get("max_depth", 3),
                exclude_patterns=arguments.get("exclude_patterns")
            )
            return _format_result(result)

        elif name == "idlergear_fs_move_file":
            fs = _get_fs_server()
            result = fs.move_file(arguments["source"], arguments["destination"])
            return _format_result(result)

        elif name == "idlergear_fs_search_files":
            fs = _get_fs_server()
            result = fs.search_files(
                path=arguments.get("path", "."),
                pattern=arguments.get("pattern", "*"),
                exclude_patterns=arguments.get("exclude_patterns"),
                use_gitignore=arguments.get("use_gitignore", True)
            )
            return _format_result(result)

        elif name == "idlergear_fs_file_info":
            fs = _get_fs_server()
            result = fs.get_file_info(arguments["path"])
            return _format_result(result)

        elif name == "idlergear_fs_file_checksum":
            fs = _get_fs_server()
            result = fs.get_file_checksum(
                path=arguments["path"],
                algorithm=arguments.get("algorithm", "sha256")
            )
            return _format_result(result)

        elif name == "idlergear_fs_allowed_directories":
            fs = _get_fs_server()
            result = fs.list_allowed_directories()
            return _format_result(result)

        # Git handlers
        elif name == "idlergear_git_status":
            git = _get_git_server()
            status = git.status(repo_path=arguments.get("repo_path"))
            return _format_result({
                "branch": status.branch,
                "ahead": status.ahead,
                "behind": status.behind,
                "staged": status.staged,
                "modified": status.modified,
                "untracked": status.untracked,
                "conflicts": status.conflicts,
                "last_commit": status.last_commit,
            })

        elif name == "idlergear_git_diff":
            git = _get_git_server()
            result = git.diff(
                repo_path=arguments.get("repo_path"),
                staged=arguments.get("staged", False),
                files=arguments.get("files"),
                context_lines=arguments.get("context_lines", 3),
            )
            return _format_result({"diff": result})

        elif name == "idlergear_git_log":
            git = _get_git_server()
            commits = git.log(
                repo_path=arguments.get("repo_path"),
                max_count=arguments.get("max_count", 10),
                since=arguments.get("since"),
                until=arguments.get("until"),
                author=arguments.get("author"),
                grep=arguments.get("grep"),
            )
            return _format_result({
                "commits": [
                    {
                        "hash": c.hash,
                        "short_hash": c.short_hash,
                        "author": c.author,
                        "email": c.email,
                        "date": c.date,
                        "message": c.message,
                        "files": c.files,
                    }
                    for c in commits
                ]
            })

        elif name == "idlergear_git_add":
            git = _get_git_server()
            result = git.add(
                files=arguments["files"],
                repo_path=arguments.get("repo_path"),
                all=arguments.get("all", False),
            )
            return _format_result({"message": result})

        elif name == "idlergear_git_commit":
            git = _get_git_server()
            commit_hash = git.commit(
                message=arguments["message"],
                repo_path=arguments.get("repo_path"),
                task_id=arguments.get("task_id"),
            )
            return _format_result({"commit_hash": commit_hash, "message": arguments["message"]})

        elif name == "idlergear_git_reset":
            git = _get_git_server()
            result = git.reset(
                files=arguments.get("files"),
                repo_path=arguments.get("repo_path"),
                hard=arguments.get("hard", False),
            )
            return _format_result({"message": result})

        elif name == "idlergear_git_show":
            git = _get_git_server()
            result = git.show(
                commit=arguments["commit"],
                repo_path=arguments.get("repo_path"),
            )
            return _format_result(result)

        elif name == "idlergear_git_branch_list":
            git = _get_git_server()
            branches = git.branch_list(repo_path=arguments.get("repo_path"))
            return _format_result({"branches": branches})

        elif name == "idlergear_git_branch_create":
            git = _get_git_server()
            result = git.branch_create(
                name=arguments["name"],
                repo_path=arguments.get("repo_path"),
                checkout=arguments.get("checkout", True),
            )
            return _format_result({"message": result})

        elif name == "idlergear_git_branch_checkout":
            git = _get_git_server()
            result = git.branch_checkout(
                name=arguments["name"],
                repo_path=arguments.get("repo_path"),
            )
            return _format_result({"message": result})

        elif name == "idlergear_git_branch_delete":
            git = _get_git_server()
            result = git.branch_delete(
                name=arguments["name"],
                repo_path=arguments.get("repo_path"),
                force=arguments.get("force", False),
            )
            return _format_result({"message": result})

        # IdlerGear-specific git+task integration handlers
        elif name == "idlergear_git_commit_task":
            git = _get_git_server()
            commit_hash = git.commit_task(
                task_id=arguments["task_id"],
                message=arguments["message"],
                repo_path=arguments.get("repo_path"),
                auto_add=arguments.get("auto_add", True),
            )
            return _format_result({
                "commit_hash": commit_hash,
                "task_id": arguments["task_id"],
                "message": arguments["message"],
            })

        elif name == "idlergear_git_status_for_task":
            git = _get_git_server()
            result = git.status_for_task(
                task_id=arguments["task_id"],
                repo_path=arguments.get("repo_path"),
            )
            return _format_result(result)

        elif name == "idlergear_git_task_commits":
            git = _get_git_server()
            commits = git.task_commits(
                task_id=arguments["task_id"],
                repo_path=arguments.get("repo_path"),
                max_count=arguments.get("max_count", 50),
            )
            return _format_result({
                "task_id": arguments["task_id"],
                "commits": [
                    {
                        "hash": c.hash,
                        "short_hash": c.short_hash,
                        "author": c.author,
                        "email": c.email,
                        "date": c.date,
                        "message": c.message,
                        "files": c.files,
                    }
                    for c in commits
                ],
            })

        elif name == "idlergear_git_sync_tasks":
            git = _get_git_server()
            result = git.sync_tasks_from_commits(
                repo_path=arguments.get("repo_path"),
                since=arguments.get("since"),
            )
            return _format_result(result)

        # === Process Management Tools ===
        elif name == "idlergear_pm_list_processes":
            pm = _get_pm_server()
            processes = pm.list_processes(
                filter_name=arguments.get("filter_name"),
                filter_user=arguments.get("filter_user"),
                sort_by=arguments.get("sort_by", "cpu"),
            )
            return _format_result(processes)

        elif name == "idlergear_pm_get_process":
            pm = _get_pm_server()
            process = pm.get_process(arguments["pid"])
            if process is None:
                return [TextContent(type="text", text=f"Process not found: {arguments['pid']}")]
            return _format_result(process)

        elif name == "idlergear_pm_kill_process":
            pm = _get_pm_server()
            success = pm.kill_process(
                arguments["pid"],
                force=arguments.get("force", False),
            )
            return _format_result({"success": success, "pid": arguments["pid"]})

        elif name == "idlergear_pm_system_info":
            pm = _get_pm_server()
            info = pm.system_info()
            return _format_result(info)

        elif name == "idlergear_pm_start_run":
            pm = _get_pm_server()
            run_data = pm.start_run(
                command=arguments["command"],
                name=arguments.get("name"),
                task_id=arguments.get("task_id"),
            )
            return _format_result(run_data)

        elif name == "idlergear_pm_list_runs":
            pm = _get_pm_server()
            runs_list = pm.list_runs()
            return _format_result(runs_list)

        elif name == "idlergear_pm_get_run_status":
            pm = _get_pm_server()
            status = pm.get_run_status(arguments["name"])
            if status is None:
                return [TextContent(type="text", text=f"Run not found: {arguments['name']}")]
            return _format_result(status)

        elif name == "idlergear_pm_get_run_logs":
            pm = _get_pm_server()
            logs = pm.get_run_logs(
                name=arguments["name"],
                tail=arguments.get("tail"),
                stream=arguments.get("stream", "stdout"),
            )
            if logs is None:
                return [TextContent(type="text", text=f"Run not found: {arguments['name']}")]
            return [TextContent(type="text", text=logs)]

        elif name == "idlergear_pm_stop_run":
            pm = _get_pm_server()
            success = pm.stop_run(arguments["name"])
            return _format_result({"success": success, "name": arguments["name"]})

        elif name == "idlergear_pm_task_runs":
            pm = _get_pm_server()
            runs_list = pm.task_runs(arguments["task_id"])
            return _format_result(runs_list)

        elif name == "idlergear_pm_quick_start":
            pm = _get_pm_server()
            process = pm.quick_start(
                executable=arguments["executable"],
                args=arguments.get("args"),
            )
            return _format_result(process)

        # OpenTelemetry log query handlers
        elif name == "idlergear_otel_query_logs":
            from idlergear.otel_storage import OTelStorage
            from datetime import datetime, timedelta
            import re

            storage = OTelStorage()

            # Parse relative time strings like "1h", "30m", "24h"
            start_ns = None
            if "start_time" in arguments:
                start_str = arguments["start_time"]
                # Check for relative time
                relative_match = re.match(r"(\d+)([hm])", start_str)
                if relative_match:
                    value = int(relative_match.group(1))
                    unit = relative_match.group(2)
                    if unit == "h":
                        start_dt = datetime.now() - timedelta(hours=value)
                    else:  # m
                        start_dt = datetime.now() - timedelta(minutes=value)
                    start_ns = int(start_dt.timestamp() * 1e9)
                else:
                    # Assume ISO format
                    start_dt = datetime.fromisoformat(start_str)
                    start_ns = int(start_dt.timestamp() * 1e9)

            end_ns = None
            if "end_time" in arguments:
                end_dt = datetime.fromisoformat(arguments["end_time"])
                end_ns = int(end_dt.timestamp() * 1e9)

            # Query logs
            logs = storage.query(
                severity=arguments.get("severity"),
                service=arguments.get("service"),
                start_time=start_ns,
                end_time=end_ns,
                limit=arguments.get("limit", 100),
            )

            # Full-text search if requested
            if "search" in arguments:
                search_query = arguments["search"]
                logs = storage.search(search_query, limit=arguments.get("limit", 100))

            return _format_result({"logs": logs, "count": len(logs)})

        elif name == "idlergear_otel_stats":
            from idlergear.otel_storage import OTelStorage

            storage = OTelStorage()
            # Get basic stats using count()
            total = storage.count()

            # Get severity breakdown
            by_severity = {}
            for sev in ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"]:
                count = storage.count(severity=[sev])
                if count > 0:
                    by_severity[sev] = count

            # Get service breakdown
            cursor = storage.conn.execute(
                "SELECT service, COUNT(*) as count FROM logs GROUP BY service"
            )
            by_service = {row[0]: row[1] for row in cursor.fetchall()}

            stats = {
                "total": total,
                "by_severity": by_severity,
                "by_service": by_service,
            }
            return _format_result(stats)

        elif name == "idlergear_otel_recent_errors":
            from idlergear.otel_storage import OTelStorage

            storage = OTelStorage()
            errors = storage.query(
                severity="ERROR",
                service=arguments.get("service"),
                limit=arguments.get("limit", 20),
            )
            fatals = storage.query(
                severity="FATAL",
                service=arguments.get("service"),
                limit=arguments.get("limit", 20),
            )

            all_errors = errors + fatals
            # Sort by timestamp (newest first)
            all_errors.sort(key=lambda x: x["timestamp"], reverse=True)

            return _format_result({
                "errors": all_errors[:arguments.get("limit", 20)],
                "count": len(all_errors),
            })

        # === Session Management Handlers ===
        elif name == "idlergear_session_start":
            from idlergear.session import start_session

            result = start_session(
                context_mode=arguments.get("context_mode", "minimal"),
                load_state=arguments.get("load_state", True),
            )
            return _format_result(result)

        elif name == "idlergear_session_save":
            from idlergear.session import SessionState

            session = SessionState()
            state = session.save(
                current_task_id=arguments.get("current_task_id"),
                working_files=arguments.get("working_files"),
                notes=arguments.get("notes"),
            )
            return _format_result({"state": state, "message": "Session state saved"})

        elif name == "idlergear_session_end":
            from idlergear.session import end_session

            result = end_session(
                current_task_id=arguments.get("current_task_id"),
                working_files=arguments.get("working_files"),
                notes=arguments.get("notes"),
            )
            return _format_result(result)

        elif name == "idlergear_session_status":
            from idlergear.session import SessionState

            session = SessionState()
            summary = session.get_summary()
            state = session.load()
            return _format_result({
                "summary": summary,
                "state": state,
            })

        # === Watch Mode Handlers ===
        elif name == "idlergear_watch_check":
            from idlergear.watch import analyze, analyze_and_act

            if arguments.get("act", False):
                status, actions = analyze_and_act(auto_create_tasks=True)
                return _format_result({
                    "status": status.to_dict(),
                    "actions": [a.to_dict() for a in actions],
                })
            else:
                status = analyze()
                return _format_result(status.to_dict())

        elif name == "idlergear_watch_act":
            from idlergear.watch import analyze, act_on_suggestion

            suggestion_id = arguments["suggestion_id"]

            # Get current suggestions
            status = analyze()

            # Find the suggestion by ID
            suggestion = None
            for s in status.suggestions:
                if s.id == suggestion_id:
                    suggestion = s
                    break

            if suggestion is None:
                return _format_result({
                    "success": False,
                    "error": f"Suggestion '{suggestion_id}' not found. Available: {[s.id for s in status.suggestions]}",
                })

            result = act_on_suggestion(suggestion)
            return _format_result(result.to_dict())

        elif name == "idlergear_watch_stats":
            from idlergear.watch import get_watch_stats

            stats = get_watch_stats()
            return _format_result(stats)

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def run_server():
    """Run the MCP server with reload support."""
    # Set up signal handler for reload (SIGUSR1)
    _setup_reload_signal()

    # Write PID file so CLI can find and signal us
    _write_pid_file()

    try:
        async with stdio_server() as (read_stream, write_stream):
            init_options = server.create_initialization_options()
            await server.run(read_stream, write_stream, init_options)
    finally:
        _cleanup_pid_file()


def main():
    """Entry point for the MCP server."""
    import asyncio
    import atexit

    # Register cleanup
    atexit.register(_cleanup_pid_file)

    asyncio.run(run_server())


if __name__ == "__main__":
    main()

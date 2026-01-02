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

from idlergear.config import find_idlergear_root, get_config_value, set_config_value

# Version tracking for reload detection
__version__ = "0.2.0"

# Global flag for reload request
_reload_requested = False

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


from idlergear.notes import create_note, delete_note, get_note, list_notes, promote_note
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
from idlergear.plans import (
    create_plan,
    get_current_plan,
    get_plan,
    list_plans,
    switch_plan,
)
from idlergear.reference import (
    add_reference,
    get_reference,
    list_references,
    search_references,
)
from idlergear.runs import get_run_logs, get_run_status, list_runs, start_run, stop_run
from idlergear.search import search_all
from idlergear.tasks import close_task, create_task, get_task, list_tasks, update_task
from idlergear.vision import get_vision, set_vision

# Create the MCP server
server = Server("idlergear")


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
            inputSchema={"type": "object", "properties": {}},
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
            inputSchema={"type": "object", "properties": {}},
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
            inputSchema={"type": "object", "properties": {}},
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
            description="MANDATORY AT SESSION START: Get full project context. You MUST call this at the beginning of EVERY session BEFORE doing any work. Returns vision, current plan, open tasks, explorations, and recent notes. Do NOT skip this step.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_refs": {
                        "type": "boolean",
                        "description": "Include reference documents",
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
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        _check_initialized()

        # Task handlers
        if name == "idlergear_task_create":
            result = create_task(
                arguments["title"],
                body=arguments.get("body"),
                labels=arguments.get("labels"),
                priority=arguments.get("priority"),
                due=arguments.get("due"),
            )
            return _format_result(result)

        elif name == "idlergear_task_list":
            result = list_tasks(state=arguments.get("state", "open"))
            return _format_result(result)

        elif name == "idlergear_task_show":
            result = get_task(arguments["id"])
            if result is None:
                raise ValueError(f"Task #{arguments['id']} not found")
            return _format_result(result)

        elif name == "idlergear_task_close":
            result = close_task(arguments["id"])
            if result is None:
                raise ValueError(f"Task #{arguments['id']} not found")
            return _format_result(result)

        elif name == "idlergear_task_update":
            result = update_task(
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

        # Note handlers
        elif name == "idlergear_note_create":
            result = create_note(
                arguments["content"],
                tags=arguments.get("tags"),
            )
            return _format_result(result)

        elif name == "idlergear_note_list":
            result = list_notes(tag=arguments.get("tag"))
            return _format_result(result)

        elif name == "idlergear_note_show":
            result = get_note(arguments["id"])
            if result is None:
                raise ValueError(f"Note #{arguments['id']} not found")
            return _format_result(result)

        elif name == "idlergear_note_delete":
            if not delete_note(arguments["id"]):
                raise ValueError(f"Note #{arguments['id']} not found")
            return _format_result({"deleted": True, "id": arguments["id"]})

        elif name == "idlergear_note_promote":
            result = promote_note(arguments["id"], arguments["to"])
            if result is None:
                raise ValueError(f"Note #{arguments['id']} not found")
            return _format_result(result)

        # Exploration handlers (deprecated - redirect to notes with 'explore' tag)
        elif name == "idlergear_explore_create":
            # Combine title and body into note content
            content = arguments["title"]
            if arguments.get("body"):
                content = f"{content}\n\n{arguments['body']}"
            result = create_note(content, tags=["explore"])
            result["deprecated"] = "Use idlergear_note_create with tags=['explore'] instead"
            return _format_result(result)

        elif name == "idlergear_explore_list":
            notes = list_notes(tag="explore")
            result = {
                "notes": notes,
                "deprecated": "Use idlergear_note_list with tag='explore' instead",
            }
            return _format_result(result)

        elif name == "idlergear_explore_delete":
            note_id = arguments["id"]
            success = delete_note(note_id)
            result = {
                "deleted": success,
                "deprecated": "Use idlergear_note_delete instead",
            }
            if not success:
                result["error"] = f"Note #{note_id} not found"
            return _format_result(result)

        # Vision handlers
        elif name == "idlergear_vision_show":
            result = get_vision()
            return _format_result({"content": result})

        elif name == "idlergear_vision_edit":
            set_vision(arguments["content"])
            return _format_result({"updated": True})

        # Plan handlers
        elif name == "idlergear_plan_create":
            result = create_plan(
                arguments["name"],
                title=arguments.get("title"),
                body=arguments.get("body"),
            )
            return _format_result(result)

        elif name == "idlergear_plan_list":
            result = list_plans()
            return _format_result(result)

        elif name == "idlergear_plan_show":
            name_arg = arguments.get("name")
            if name_arg:
                result = get_plan(name_arg)
            else:
                result = get_current_plan()
            return _format_result(result)

        elif name == "idlergear_plan_switch":
            result = switch_plan(arguments["name"])
            if result is None:
                raise ValueError(f"Plan '{arguments['name']}' not found")
            return _format_result(result)

        # Reference handlers
        elif name == "idlergear_reference_add":
            result = add_reference(
                arguments["title"],
                body=arguments.get("body"),
            )
            return _format_result(result)

        elif name == "idlergear_reference_list":
            result = list_references()
            return _format_result(result)

        elif name == "idlergear_reference_show":
            result = get_reference(arguments["title"])
            if result is None:
                raise ValueError(f"Reference '{arguments['title']}' not found")
            return _format_result(result)

        elif name == "idlergear_reference_search":
            result = search_references(arguments["query"])
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

            ctx = gather_context(include_references=arguments.get("include_refs", False))
            return _format_result(format_context_json(ctx))

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

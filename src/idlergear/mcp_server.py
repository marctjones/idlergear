"""MCP Server for IdlerGear - exposes knowledge management as AI tools."""

import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from idlergear.config import find_idlergear_root, get_config_value, set_config_value
from idlergear.explorations import (
    close_exploration,
    create_exploration,
    get_exploration,
    list_explorations,
)
from idlergear.notes import create_note, delete_note, get_note, list_notes, promote_note
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
            description="MANDATORY: Create a note. You MUST call this to capture: thoughts, discoveries, learnings, reminders. NEVER write to NOTES.md, SESSION_*.md, or SCRATCH.md - use this tool instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Note content"},
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="idlergear_note_list",
            description="List all notes",
            inputSchema={"type": "object", "properties": {}},
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
            description="Promote a note to task, exploration, or reference",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Note ID"},
                    "to": {
                        "type": "string",
                        "enum": ["task", "explore", "reference"],
                        "description": "Target type",
                    },
                },
                "required": ["id", "to"],
            },
        ),
        # Exploration tools
        Tool(
            name="idlergear_explore_create",
            description="Create an exploration for research questions or investigations. Use this when you need to explore a topic, investigate options, or research before making a decision.",
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
            description="List explorations",
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
            name="idlergear_explore_show",
            description="Show an exploration by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Exploration ID"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="idlergear_explore_close",
            description="Close an exploration",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "Exploration ID"},
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
            description="Add a reference document",
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
            description="Search across all knowledge types (tasks, notes, explorations, references, plans)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["task", "note", "explore", "reference", "plan"],
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
                        "enum": ["task", "note", "explore", "reference", "plan", "vision"],
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
            result = create_note(arguments["content"])
            return _format_result(result)

        elif name == "idlergear_note_list":
            result = list_notes()
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

        # Exploration handlers
        elif name == "idlergear_explore_create":
            result = create_exploration(
                arguments["title"],
                body=arguments.get("body"),
            )
            return _format_result(result)

        elif name == "idlergear_explore_list":
            result = list_explorations(state=arguments.get("state", "open"))
            return _format_result(result)

        elif name == "idlergear_explore_show":
            result = get_exploration(arguments["id"])
            if result is None:
                raise ValueError(f"Exploration #{arguments['id']} not found")
            return _format_result(result)

        elif name == "idlergear_explore_close":
            result = close_exploration(arguments["id"])
            if result is None:
                raise ValueError(f"Exploration #{arguments['id']} not found")
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

            all_types = ["task", "note", "explore", "reference", "plan", "vision"]
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

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Entry point for the MCP server."""
    import asyncio

    asyncio.run(run_server())


if __name__ == "__main__":
    main()

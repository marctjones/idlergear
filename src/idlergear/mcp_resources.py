"""MCP Resources implementation for IdlerGear.

Implements the Resources primitive from MCP specification for efficient read-only
data access. Resources provide data that the AI can read but not change.

Official MCP guidance:
- Resources are app-controlled
- Provide static or semi-static data
- No tool call overhead
- Can be subscribed to for updates

See: https://modelcontextprotocol.io/specification/2025-11-25#resources
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from mcp.types import Resource, TextContent, ImageContent, EmbeddedResource


def list_resources() -> list[Resource]:
    """List all available IdlerGear resources.

    Returns:
        List of Resource objects describing available data endpoints
    """
    return [
        # Project metadata
        Resource(
            uri="idlergear://project/vision",
            name="Project Vision",
            description="High-level project goals, mission, and objectives",
            mimeType="text/markdown",
        ),

        # Context at different detail levels
        Resource(
            uri="idlergear://project/context",
            name="Project Context (Standard)",
            description="Full project context: tasks, notes, runs, references",
            mimeType="application/json",
        ),
        Resource(
            uri="idlergear://project/context/minimal",
            name="Project Context (Minimal)",
            description="Lightweight context: task counts, active runs, recent activity",
            mimeType="application/json",
        ),
        Resource(
            uri="idlergear://project/context/full",
            name="Project Context (Full)",
            description="Comprehensive context with all details",
            mimeType="application/json",
        ),

        # Task-related resources
        Resource(
            uri="idlergear://project/tasks/open",
            name="Open Tasks",
            description="List of all open tasks with metadata",
            mimeType="application/json",
        ),
        Resource(
            uri="idlergear://project/tasks/summary",
            name="Tasks Summary",
            description="Task counts by state and label",
            mimeType="application/json",
        ),

        # Run-related resources
        Resource(
            uri="idlergear://project/runs/active",
            name="Active Runs",
            description="Currently running background processes",
            mimeType="application/json",
        ),

        # Notifications
        Resource(
            uri="idlergear://project/notifications",
            name="Pending Notifications",
            description="Queued notifications for Claude (process completions, suggestions)",
            mimeType="application/json",
        ),

        # Knowledge graph stats
        Resource(
            uri="idlergear://graph/stats",
            name="Knowledge Graph Statistics",
            description="Node counts, relationship counts, indexing status",
            mimeType="application/json",
        ),

        # System status
        Resource(
            uri="idlergear://system/status",
            name="System Status",
            description="Daemon status, indexing status, background jobs",
            mimeType="application/json",
        ),
    ]


def read_resource(uri: str) -> str:
    """Read the content of a resource.

    Args:
        uri: Resource URI (e.g., "idlergear://project/vision")

    Returns:
        Resource content as string (JSON or markdown)

    Raises:
        ValueError: If URI is not recognized
    """
    if uri == "idlergear://project/vision":
        return _read_vision()

    elif uri == "idlergear://project/context":
        return _read_context(mode="standard")

    elif uri == "idlergear://project/context/minimal":
        return _read_context(mode="minimal")

    elif uri == "idlergear://project/context/full":
        return _read_context(mode="full")

    elif uri == "idlergear://project/tasks/open":
        return _read_open_tasks()

    elif uri == "idlergear://project/tasks/summary":
        return _read_task_summary()

    elif uri == "idlergear://project/runs/active":
        return _read_active_runs()

    elif uri == "idlergear://project/notifications":
        return _read_notifications()

    elif uri == "idlergear://graph/stats":
        return _read_graph_stats()

    elif uri == "idlergear://system/status":
        return _read_system_status()

    # Template-based URIs (with parameters)
    elif uri.startswith("idlergear://files/") and uri.endswith("/annotation"):
        # Extract file path from URI
        # Format: idlergear://files/{path}/annotation
        path = uri.replace("idlergear://files/", "").replace("/annotation", "")
        return _read_file_annotation(path)

    elif uri.startswith("idlergear://project/tasks/"):
        # Extract task ID from URI
        # Format: idlergear://project/tasks/{id}
        task_id = uri.replace("idlergear://project/tasks/", "")
        if task_id not in ["open", "summary"]:  # Not the special endpoints
            return _read_task(task_id)

    else:
        raise ValueError(f"Unknown resource URI: {uri}")


# Resource content readers

def _read_vision() -> str:
    """Read project vision as markdown."""
    from idlergear.vision import get_vision

    try:
        vision = get_vision()
        return vision
    except Exception as e:
        return f"# Vision Not Found\n\nError: {e}\n\nRun `idlergear vision edit` to create."


def _read_context(mode: str = "standard") -> str:
    """Read project context as JSON."""
    from idlergear.context import get_context

    try:
        context = get_context(mode=mode)
        return json.dumps(context, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


def _read_open_tasks() -> str:
    """Read open tasks as JSON."""
    from idlergear.backends.registry import get_backend

    try:
        backend = get_backend("task")
        tasks = backend.list(state="open")

        # Serialize to JSON
        tasks_data = [
            {
                "id": t.id,
                "title": t.title,
                "state": t.state,
                "labels": t.labels,
                "priority": t.priority,
                "due": t.due,
                "created_at": t.created_at,
            }
            for t in tasks
        ]

        return json.dumps({"tasks": tasks_data, "count": len(tasks_data)}, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e), "tasks": [], "count": 0}, indent=2)


def _read_task_summary() -> str:
    """Read task summary statistics as JSON."""
    from idlergear.backends.registry import get_backend

    try:
        backend = get_backend("task")
        all_tasks = backend.list()

        # Count by state
        by_state = {}
        by_label = {}
        by_priority = {}

        for task in all_tasks:
            # State counts
            state = task.state or "unknown"
            by_state[state] = by_state.get(state, 0) + 1

            # Label counts
            for label in (task.labels or []):
                by_label[label] = by_label.get(label, 0) + 1

            # Priority counts
            priority = task.priority or "none"
            by_priority[priority] = by_priority.get(priority, 0) + 1

        summary = {
            "total": len(all_tasks),
            "by_state": by_state,
            "by_label": by_label,
            "by_priority": by_priority,
        }

        return json.dumps(summary, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


def _read_task(task_id: str) -> str:
    """Read specific task details as JSON."""
    from idlergear.backends.registry import get_backend

    try:
        backend = get_backend("task")
        task = backend.get(task_id)

        if not task:
            return json.dumps({"error": f"Task {task_id} not found"}, indent=2)

        task_data = {
            "id": task.id,
            "title": task.title,
            "body": task.body,
            "state": task.state,
            "labels": task.labels,
            "priority": task.priority,
            "due": task.due,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

        return json.dumps(task_data, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


def _read_active_runs() -> str:
    """Read active background runs as JSON."""
    from idlergear.runs import list_runs

    try:
        runs = list_runs()

        # Filter to running only
        active = [r for r in runs if r.get("status") == "running"]

        return json.dumps({"runs": active, "count": len(active)}, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e), "runs": [], "count": 0}, indent=2)


def _read_notifications() -> str:
    """Read pending notifications as JSON."""
    # TODO: Implement notification queue in Phase 3.1
    # For now, return empty queue
    return json.dumps({
        "notifications": [],
        "count": 0,
        "note": "Notification queue will be implemented in Phase 3.1"
    }, indent=2)


def _read_graph_stats() -> str:
    """Read knowledge graph statistics as JSON."""
    from idlergear.graph import get_database
    from idlergear.graph.schema import get_schema_info

    try:
        db = get_database()
        schema_info = get_schema_info(db)

        stats = {
            "nodes": schema_info.get("node_counts", {}),
            "relationships": schema_info.get("relationship_counts", {}),
            "total_nodes": sum(schema_info.get("node_counts", {}).values()),
            "total_relationships": sum(schema_info.get("relationship_counts", {}).values()),
        }

        return json.dumps(stats, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


def _read_system_status() -> str:
    """Read system status as JSON."""
    from idlergear.daemon.client import get_daemon_client, DaemonNotRunning
    from idlergear.indexing import get_indexing_status
    from idlergear.config import find_idlergear_root

    status = {
        "daemon": {"running": False},
        "indexing": {},
        "root": None,
    }

    try:
        root = find_idlergear_root()
        status["root"] = str(root) if root else None

        # Check daemon
        if root:
            try:
                client = get_daemon_client(root)
                # If we can create client, daemon is likely running
                status["daemon"]["running"] = True
            except DaemonNotRunning:
                status["daemon"]["running"] = False

        # Get indexing status
        try:
            indexing_status = get_indexing_status()
            status["indexing"] = indexing_status
        except Exception as e:
            status["indexing"] = {"error": str(e)}

    except Exception as e:
        status["error"] = str(e)

    return json.dumps(status, indent=2, default=str)


def _read_file_annotation(file_path: str) -> str:
    """Read file annotation metadata as JSON."""
    from idlergear.file_annotation_storage import FileAnnotationStorage

    try:
        storage = FileAnnotationStorage()
        annotation = storage.get_annotation(file_path)

        if not annotation:
            return json.dumps({
                "error": f"No annotation found for {file_path}",
                "hint": "Run idlergear_file_annotate to create one"
            }, indent=2)

        annotation_data = {
            "path": annotation.path,
            "status": annotation.status.value if annotation.status else None,
            "description": annotation.description,
            "tags": annotation.tags,
            "components": annotation.components,
            "related_files": annotation.related_files,
            "successor": annotation.successor,
            "reason": annotation.reason,
        }

        return json.dumps(annotation_data, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

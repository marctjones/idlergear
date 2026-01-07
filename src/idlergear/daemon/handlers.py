"""Daemon method handlers for knowledge management operations."""

from __future__ import annotations

from typing import Any

from idlergear.daemon.server import Connection, DaemonServer


def register_handlers(server: DaemonServer) -> None:
    """Register all knowledge management handlers with the daemon."""

    # Task handlers
    async def task_create(params: dict[str, Any], conn: Connection) -> dict[str, Any]:
        from idlergear.tasks import create_task

        return create_task(
            title=params["title"],
            body=params.get("body"),
            labels=params.get("labels"),
            assignees=params.get("assignees"),
            priority=params.get("priority"),
            due=params.get("due"),
        )

    async def task_list(params: dict[str, Any], conn: Connection) -> list[dict]:
        from idlergear.tasks import list_tasks

        return list_tasks(state=params.get("state", "open"))

    async def task_get(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.tasks import get_task

        return get_task(params["id"])

    async def task_close(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.tasks import close_task

        result = close_task(params["id"])
        if result:
            await server.broadcast("task.closed", {"id": params["id"]})
        return result

    async def task_update(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.tasks import update_task

        result = update_task(
            params["id"],
            title=params.get("title"),
            body=params.get("body"),
            labels=params.get("labels"),
            priority=params.get("priority"),
            due=params.get("due"),
        )
        if result:
            await server.broadcast("task.updated", {"id": params["id"]})
        return result

    # Note handlers
    async def note_create(params: dict[str, Any], conn: Connection) -> dict[str, Any]:
        from idlergear.notes import create_note

        return create_note(params["content"])

    async def note_list(params: dict[str, Any], conn: Connection) -> list[dict]:
        from idlergear.notes import list_notes

        return list_notes()

    async def note_get(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.notes import get_note

        return get_note(params["id"])

    async def note_delete(params: dict[str, Any], conn: Connection) -> bool:
        from idlergear.notes import delete_note

        result = delete_note(params["id"])
        if result:
            await server.broadcast("note.deleted", {"id": params["id"]})
        return result

    async def note_promote(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.notes import promote_note

        return promote_note(params["id"], params.get("to", "task"))

    # Exploration handlers
    async def explore_create(params: dict[str, Any], conn: Connection) -> dict[str, Any]:
        from idlergear.explorations import create_exploration

        return create_exploration(params["title"], body=params.get("body"))

    async def explore_list(params: dict[str, Any], conn: Connection) -> list[dict]:
        from idlergear.explorations import list_explorations

        return list_explorations(state=params.get("state", "open"))

    async def explore_get(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.explorations import get_exploration

        return get_exploration(params["id"])

    async def explore_close(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.explorations import close_exploration

        result = close_exploration(params["id"])
        if result:
            await server.broadcast("explore.closed", {"id": params["id"]})
        return result

    # Vision handlers
    async def vision_get(params: dict[str, Any], conn: Connection) -> str | None:
        from idlergear.vision import get_vision

        return get_vision()

    async def vision_set(params: dict[str, Any], conn: Connection) -> bool:
        from idlergear.vision import set_vision

        set_vision(params["content"])
        await server.broadcast("vision.updated", {})
        return True

    # Plan handlers
    async def plan_create(params: dict[str, Any], conn: Connection) -> dict[str, Any]:
        from idlergear.plans import create_plan

        return create_plan(
            params["name"],
            title=params.get("title"),
            body=params.get("body"),
        )

    async def plan_list(params: dict[str, Any], conn: Connection) -> list[dict]:
        from idlergear.plans import list_plans

        return list_plans()

    async def plan_get(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.plans import get_plan

        return get_plan(params["name"])

    async def plan_current(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.plans import get_current_plan

        return get_current_plan()

    async def plan_switch(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.plans import switch_plan

        result = switch_plan(params["name"])
        if result:
            await server.broadcast("plan.switched", {"name": params["name"]})
        return result

    # Reference handlers
    async def reference_add(params: dict[str, Any], conn: Connection) -> dict[str, Any]:
        from idlergear.reference import add_reference

        return add_reference(params["title"], body=params.get("body"))

    async def reference_list(params: dict[str, Any], conn: Connection) -> list[dict]:
        from idlergear.reference import list_references

        return list_references()

    async def reference_get(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.reference import get_reference

        return get_reference(params["title"])

    async def reference_update(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.reference import update_reference

        result = update_reference(
            params["title"],
            new_title=params.get("new_title"),
            body=params.get("body"),
        )
        if result:
            await server.broadcast("reference.updated", {"title": params["title"]})
        return result

    async def reference_search(params: dict[str, Any], conn: Connection) -> list[dict]:
        from idlergear.reference import search_references

        return search_references(params["query"])

    # Config handlers
    async def config_get(params: dict[str, Any], conn: Connection) -> Any:
        from idlergear.config import get_config_value

        return get_config_value(params["key"])

    async def config_set(params: dict[str, Any], conn: Connection) -> bool:
        from idlergear.config import set_config_value

        set_config_value(params["key"], params["value"])
        return True

    # Run handlers
    async def run_start(params: dict[str, Any], conn: Connection) -> dict[str, Any]:
        from idlergear.runs import start_run

        return start_run(params["command"], name=params.get("name"))

    async def run_list(params: dict[str, Any], conn: Connection) -> list[dict]:
        from idlergear.runs import list_runs

        return list_runs()

    async def run_status(params: dict[str, Any], conn: Connection) -> dict[str, Any] | None:
        from idlergear.runs import get_run_status

        return get_run_status(params["name"])

    async def run_logs(params: dict[str, Any], conn: Connection) -> str | None:
        from idlergear.runs import get_run_logs

        return get_run_logs(
            params["name"],
            tail=params.get("tail"),
            stream=params.get("stream", "stdout"),
        )

    async def run_stop(params: dict[str, Any], conn: Connection) -> bool:
        from idlergear.runs import stop_run

        return stop_run(params["name"])

    # Search handler
    async def search(params: dict[str, Any], conn: Connection) -> list[dict]:
        from idlergear.search import search_all

        return search_all(params["query"], types=params.get("types"))

    # Register all handlers
    server.register_method("task.create", task_create)
    server.register_method("task.list", task_list)
    server.register_method("task.get", task_get)
    server.register_method("task.close", task_close)
    server.register_method("task.update", task_update)

    server.register_method("note.create", note_create)
    server.register_method("note.list", note_list)
    server.register_method("note.get", note_get)
    server.register_method("note.delete", note_delete)
    server.register_method("note.promote", note_promote)

    server.register_method("explore.create", explore_create)
    server.register_method("explore.list", explore_list)
    server.register_method("explore.get", explore_get)
    server.register_method("explore.close", explore_close)

    server.register_method("vision.get", vision_get)
    server.register_method("vision.set", vision_set)

    server.register_method("plan.create", plan_create)
    server.register_method("plan.list", plan_list)
    server.register_method("plan.get", plan_get)
    server.register_method("plan.current", plan_current)
    server.register_method("plan.switch", plan_switch)

    server.register_method("reference.add", reference_add)
    server.register_method("reference.list", reference_list)
    server.register_method("reference.get", reference_get)
    server.register_method("reference.update", reference_update)
    server.register_method("reference.search", reference_search)

    server.register_method("config.get", config_get)
    server.register_method("config.set", config_set)

    server.register_method("run.start", run_start)
    server.register_method("run.list", run_list)
    server.register_method("run.status", run_status)
    server.register_method("run.logs", run_logs)
    server.register_method("run.stop", run_stop)

    server.register_method("search", search)

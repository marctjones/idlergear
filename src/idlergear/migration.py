"""Backend migration utilities for IdlerGear.

Provides functionality to migrate data between different backends.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def migrate_tasks(
    source_backend: Any,
    target_backend: Any,
    *,
    state: str = "all",
    on_item: Callable[[dict[str, Any]], None] | None = None,
    on_error: Callable[[dict[str, Any], Exception], None] | None = None,
) -> dict[str, Any]:
    """Migrate tasks from source to target backend.

    Args:
        source_backend: Source backend to read from
        target_backend: Target backend to write to
        state: State filter ("open", "closed", or "all")
        on_item: Optional callback for each migrated item
        on_error: Optional callback for errors

    Returns:
        Dict with migration statistics
    """
    stats = {"total": 0, "migrated": 0, "errors": 0, "skipped": 0}

    tasks = source_backend.list(state=state)
    stats["total"] = len(tasks)

    for task in tasks:
        try:
            # Create task in target
            result = target_backend.create(
                title=task.get("title", "Untitled"),
                body=task.get("body"),
                labels=task.get("labels"),
                assignees=task.get("assignees"),
                priority=task.get("priority"),
                due=task.get("due"),
            )

            # If source task is closed, close it in target too
            if task.get("state") in ("closed", "done", "complete"):
                target_backend.close(result["id"])

            stats["migrated"] += 1

            if on_item:
                on_item({"source": task, "target": result})

        except Exception as e:
            stats["errors"] += 1
            if on_error:
                on_error(task, e)

    return stats


def migrate_explorations(
    source_backend: Any,
    target_backend: Any,
    *,
    state: str = "all",
    on_item: Callable[[dict[str, Any]], None] | None = None,
    on_error: Callable[[dict[str, Any], Exception], None] | None = None,
) -> dict[str, Any]:
    """Migrate explorations from source to target backend.

    Args:
        source_backend: Source backend to read from
        target_backend: Target backend to write to
        state: State filter ("open", "closed", or "all")
        on_item: Optional callback for each migrated item
        on_error: Optional callback for errors

    Returns:
        Dict with migration statistics
    """
    stats = {"total": 0, "migrated": 0, "errors": 0, "skipped": 0}

    explorations = source_backend.list(state=state)
    stats["total"] = len(explorations)

    for explore in explorations:
        try:
            result = target_backend.create(
                title=explore.get("title", "Untitled"),
                body=explore.get("body"),
            )

            # If source is closed, close in target
            if explore.get("state") in ("closed", "done"):
                target_backend.close(result["id"])

            stats["migrated"] += 1

            if on_item:
                on_item({"source": explore, "target": result})

        except Exception as e:
            stats["errors"] += 1
            if on_error:
                on_error(explore, e)

    return stats


def migrate_references(
    source_backend: Any,
    target_backend: Any,
    *,
    on_item: Callable[[dict[str, Any]], None] | None = None,
    on_error: Callable[[dict[str, Any], Exception], None] | None = None,
) -> dict[str, Any]:
    """Migrate references from source to target backend.

    Args:
        source_backend: Source backend to read from
        target_backend: Target backend to write to
        on_item: Optional callback for each migrated item
        on_error: Optional callback for errors

    Returns:
        Dict with migration statistics
    """
    stats = {"total": 0, "migrated": 0, "errors": 0, "skipped": 0}

    references = source_backend.list()
    stats["total"] = len(references)

    for ref in references:
        try:
            result = target_backend.add(
                title=ref.get("title", "Untitled"),
                body=ref.get("body"),
            )

            stats["migrated"] += 1

            if on_item:
                on_item({"source": ref, "target": result})

        except Exception as e:
            stats["errors"] += 1
            if on_error:
                on_error(ref, e)

    return stats


def migrate_notes(
    source_backend: Any,
    target_backend: Any,
    *,
    on_item: Callable[[dict[str, Any]], None] | None = None,
    on_error: Callable[[dict[str, Any], Exception], None] | None = None,
) -> dict[str, Any]:
    """Migrate notes from source to target backend.

    Args:
        source_backend: Source backend to read from
        target_backend: Target backend to write to
        on_item: Optional callback for each migrated item
        on_error: Optional callback for errors

    Returns:
        Dict with migration statistics
    """
    stats = {"total": 0, "migrated": 0, "errors": 0, "skipped": 0}

    notes = source_backend.list()
    stats["total"] = len(notes)

    for note in notes:
        try:
            result = target_backend.create(
                content=note.get("content", ""),
            )

            stats["migrated"] += 1

            if on_item:
                on_item({"source": note, "target": result})

        except Exception as e:
            stats["errors"] += 1
            if on_error:
                on_error(note, e)

    return stats


def migrate_backend(
    backend_type: str,
    source_name: str,
    target_name: str,
    project_path: Path | None = None,
    *,
    state: str = "all",
    on_item: Callable[[dict[str, Any]], None] | None = None,
    on_error: Callable[[dict[str, Any], Exception], None] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Migrate data from one backend to another.

    Args:
        backend_type: Type of backend (task, explore, reference, note)
        source_name: Name of source backend (e.g., "local", "github")
        target_name: Name of target backend
        project_path: Optional project path
        state: State filter for tasks/explorations
        on_item: Callback for each migrated item
        on_error: Callback for errors
        dry_run: If True, don't actually migrate

    Returns:
        Migration statistics
    """
    from idlergear.backends.registry import (
        _backend_classes,
        _try_load_shell_backend,
    )
    from idlergear.config import find_idlergear_root

    if project_path is None:
        project_path = find_idlergear_root()

    # Get backend classes
    if backend_type not in _backend_classes:
        raise ValueError(f"Unknown backend type: {backend_type}")

    # Create source backend
    if source_name in _backend_classes[backend_type]:
        source_class = _backend_classes[backend_type][source_name]
        source_backend = source_class(project_path=project_path)
    else:
        source_backend = _try_load_shell_backend(
            backend_type, source_name, project_path
        )
        if source_backend is None:
            raise ValueError(
                f"Unknown source backend '{source_name}' for type '{backend_type}'"
            )

    # Create target backend
    if target_name in _backend_classes[backend_type]:
        target_class = _backend_classes[backend_type][target_name]
        target_backend = target_class(project_path=project_path)
    else:
        target_backend = _try_load_shell_backend(
            backend_type, target_name, project_path
        )
        if target_backend is None:
            raise ValueError(
                f"Unknown target backend '{target_name}' for type '{backend_type}'"
            )

    # Get count for dry run
    if dry_run:
        if backend_type in ("task", "explore"):
            items = source_backend.list(state=state)
        else:
            items = source_backend.list()
        return {
            "total": len(items),
            "migrated": 0,
            "errors": 0,
            "skipped": 0,
            "dry_run": True,
        }

    # Perform migration
    migrate_funcs = {
        "task": migrate_tasks,
        "explore": migrate_explorations,
        "reference": migrate_references,
        "note": migrate_notes,
    }

    if backend_type not in migrate_funcs:
        raise ValueError(f"Migration not supported for type: {backend_type}")

    migrate_func = migrate_funcs[backend_type]

    if backend_type in ("task", "explore"):
        return migrate_func(
            source_backend,
            target_backend,
            state=state,
            on_item=on_item,
            on_error=on_error,
        )
    else:
        return migrate_func(
            source_backend,
            target_backend,
            on_item=on_item,
            on_error=on_error,
        )

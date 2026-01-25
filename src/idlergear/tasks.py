"""Task management for IdlerGear.

In v0.3+, tasks are stored in .idlergear/issues/.
For backward compatibility, also checks .idlergear/tasks/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.storage import (
    get_next_id,
    now_iso,
    parse_frontmatter,
    render_frontmatter,
    slugify,
)


def get_tasks_dir(project_path: Path | None = None) -> Path | None:
    """Get the tasks directory path.

    Returns the issues/ directory (v0.3+) if it exists, otherwise
    falls back to tasks/ (legacy) for backward compatibility.
    New projects will use issues/.
    """
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None

    idlergear_dir = project_path / ".idlergear"

    # Prefer v0.3 issues/ directory
    issues_dir = idlergear_dir / "issues"
    if issues_dir.exists():
        return issues_dir

    # Fall back to legacy tasks/ directory
    tasks_dir = idlergear_dir / "tasks"
    if tasks_dir.exists():
        return tasks_dir

    # For new projects, use issues/
    return issues_dir


def create_task(
    title: str,
    body: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    priority: str | None = None,
    due: str | None = None,
    milestone: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any]:
    """Create a new task.

    Args:
        title: Task title
        body: Task body/description
        labels: List of labels
        assignees: List of assignees
        priority: Priority level (high, medium, low, or None)
        due: Due date as ISO date string (YYYY-MM-DD) or None
        milestone: Milestone name or number (local backend stores as string)
        project_path: Optional project path override

    Returns the created task data including its ID.
    """
    tasks_dir = get_tasks_dir(project_path)
    if tasks_dir is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    tasks_dir.mkdir(parents=True, exist_ok=True)

    task_id = get_next_id(tasks_dir)
    slug = slugify(title)
    filename = f"{task_id:03d}-{slug}.md"
    filepath = tasks_dir / filename

    frontmatter = {
        "id": task_id,
        "title": title,
        "state": "open",
        "created": now_iso(),
        "accessed": None,
        "access_count": 0,
        "relevance_score": 1.0,
    }

    if labels:
        frontmatter["labels"] = labels
    if assignees:
        frontmatter["assignees"] = assignees
    if priority:
        frontmatter["priority"] = priority
    if due:
        frontmatter["due"] = due
    if milestone:
        frontmatter["milestone"] = milestone

    content = render_frontmatter(frontmatter, (body or "").strip() + "\n")
    filepath.write_text(content)

    task_data = {
        "id": task_id,
        "title": title,
        "body": body,
        "state": "open",
        "labels": labels or [],
        "assignees": assignees or [],
        "priority": priority,
        "due": due,
        "created": frontmatter["created"],
        "accessed": frontmatter["accessed"],
        "access_count": frontmatter["access_count"],
        "relevance_score": frontmatter["relevance_score"],
        "path": str(filepath),
    }

    # Sync fields to GitHub Projects if configured
    from idlergear.projects import sync_task_fields_to_github

    sync_task_fields_to_github(task_id, task_data, project_path)

    return task_data


def list_tasks(
    state: str = "open", project_path: Path | None = None
) -> list[dict[str, Any]]:
    """List tasks filtered by state.

    State can be 'open', 'closed', or 'all'.
    Returns list of task data dicts sorted by ID.
    """
    tasks_dir = get_tasks_dir(project_path)
    if tasks_dir is None or not tasks_dir.exists():
        return []

    tasks = []
    for filepath in sorted(tasks_dir.glob("*.md")):
        task = load_task_from_file(filepath)
        if task:
            if state == "all" or task.get("state") == state:
                tasks.append(task)

    return sorted(tasks, key=lambda t: t.get("id", 0))


def load_task_from_file(filepath: Path) -> dict[str, Any] | None:
    """Load a task from a file path."""
    if not filepath.exists():
        return None

    content = filepath.read_text()
    frontmatter, body = parse_frontmatter(content)

    return {
        "id": frontmatter.get("id"),
        "title": frontmatter.get("title", "Untitled"),
        "body": body.strip() if body else None,
        "state": frontmatter.get("state", "open"),
        "labels": frontmatter.get("labels", []),
        "assignees": frontmatter.get("assignees", []),
        "priority": frontmatter.get("priority"),
        "due": frontmatter.get("due"),
        "created": frontmatter.get("created"),
        "accessed": frontmatter.get("accessed"),
        "access_count": frontmatter.get("access_count", 0),
        "relevance_score": frontmatter.get("relevance_score", 1.0),
        "github_issue": frontmatter.get("github_issue"),
        "path": str(filepath),
    }


def get_task(
    task_id: int,
    project_path: Path | None = None,
    update_access: bool = True,
) -> dict[str, Any] | None:
    """Get a task by ID.

    Args:
        task_id: ID of the task to retrieve
        project_path: Optional project path override
        update_access: If True, updates access timestamp and relevance score

    Returns the task data, or None if not found.
    """
    tasks_dir = get_tasks_dir(project_path)
    if tasks_dir is None:
        return None

    # Scan directory for matching ID
    for filepath in tasks_dir.glob("*.md"):
        task = load_task_from_file(filepath)
        if task and task.get("id") == task_id:
            # Update access tracking if requested
            if update_access:
                from datetime import datetime, timezone
                from idlergear.relevance import calculate_relevance
                from idlergear.storage import parse_iso

                # Update access metadata
                content = filepath.read_text()
                frontmatter, body = parse_frontmatter(content)

                frontmatter["accessed"] = now_iso()
                frontmatter["access_count"] = frontmatter.get("access_count", 0) + 1

                # Recalculate relevance score
                created = parse_iso(frontmatter.get("created", ""))
                if created:
                    frontmatter["relevance_score"] = calculate_relevance(
                        created=created,
                        accessed=datetime.now(timezone.utc),
                        access_count=frontmatter["access_count"],
                    )

                # Save updated task
                new_content = render_frontmatter(frontmatter, body.strip() + "\n")
                filepath.write_text(new_content)

                # Reload to get updated data
                task = load_task_from_file(filepath)

            return task

    return None


def update_task(
    task_id: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    priority: str | None = None,
    due: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any] | None:
    """Update a task.

    Args:
        task_id: ID of the task to update
        title: New title (None to keep existing)
        body: New body (None to keep existing)
        state: New state (None to keep existing)
        labels: New labels list (None to keep existing)
        assignees: New assignees list (None to keep existing)
        priority: New priority (None to keep existing, empty string to clear)
        due: New due date (None to keep existing, empty string to clear)
        project_path: Optional project path override

    Returns the updated task data, or None if not found.
    """
    task = get_task(task_id, project_path, update_access=False)
    if task is None:
        return None

    filepath = Path(task["path"])
    content = filepath.read_text()
    frontmatter, old_body = parse_frontmatter(content)

    # Update access metadata
    from datetime import datetime, timezone
    from idlergear.relevance import calculate_relevance
    from idlergear.storage import parse_iso

    frontmatter["accessed"] = now_iso()
    frontmatter["access_count"] = frontmatter.get("access_count", 0) + 1

    # Recalculate relevance score
    created = parse_iso(frontmatter.get("created", ""))
    if created:
        frontmatter["relevance_score"] = calculate_relevance(
            created=created,
            accessed=datetime.now(timezone.utc),
            access_count=frontmatter["access_count"],
        )

    # Update fields if provided
    if title is not None:
        frontmatter["title"] = title
    if state is not None:
        frontmatter["state"] = state
    if labels is not None:
        frontmatter["labels"] = labels
    if assignees is not None:
        frontmatter["assignees"] = assignees
    if priority is not None:
        if priority == "":
            frontmatter.pop("priority", None)
        else:
            frontmatter["priority"] = priority
    if due is not None:
        if due == "":
            frontmatter.pop("due", None)
        else:
            frontmatter["due"] = due

    new_body = body if body is not None else old_body

    new_content = render_frontmatter(frontmatter, new_body.strip() + "\n")
    filepath.write_text(new_content)

    updated_task = load_task_from_file(filepath)

    # Auto-move task in project board if state changed
    if state is not None:
        from idlergear.projects import auto_move_task_on_state_change

        auto_move_task_on_state_change(task_id, state, project_path)

    # Sync fields to GitHub Projects if configured
    from idlergear.projects import sync_task_fields_to_github

    sync_task_fields_to_github(task_id, updated_task, project_path)

    return updated_task


def close_task(task_id: int, project_path: Path | None = None) -> dict[str, Any] | None:
    """Close a task.

    Returns the updated task data, or None if not found.
    """
    return update_task(task_id, state="closed", project_path=project_path)


def reopen_task(
    task_id: int, project_path: Path | None = None
) -> dict[str, Any] | None:
    """Reopen a closed task.

    Returns the updated task data, or None if not found.
    """
    return update_task(task_id, state="open", project_path=project_path)

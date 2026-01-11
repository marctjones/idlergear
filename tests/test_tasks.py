"""Tests for task management."""

from idlergear.tasks import (
    close_task,
    create_task,
    get_task,
    list_tasks,
    update_task,
)


def test_create_task(temp_project):
    """Test creating a task."""
    task = create_task("Fix bug", body="Description here", labels=["bug"])

    assert task["id"] == 1
    assert task["title"] == "Fix bug"
    assert task["body"] == "Description here"
    assert task["state"] == "open"
    assert task["labels"] == ["bug"]


def test_list_tasks(temp_project):
    """Test listing tasks."""
    create_task("Task 1")
    create_task("Task 2")
    create_task("Task 3")

    tasks = list_tasks()
    assert len(tasks) == 3
    assert tasks[0]["title"] == "Task 1"
    assert tasks[1]["title"] == "Task 2"
    assert tasks[2]["title"] == "Task 3"


def test_list_tasks_by_state(temp_project):
    """Test filtering tasks by state."""
    create_task("Open task")
    task2 = create_task("Closed task")
    close_task(task2["id"])

    open_tasks = list_tasks(state="open")
    assert len(open_tasks) == 1
    assert open_tasks[0]["title"] == "Open task"

    closed_tasks = list_tasks(state="closed")
    assert len(closed_tasks) == 1
    assert closed_tasks[0]["title"] == "Closed task"

    all_tasks = list_tasks(state="all")
    assert len(all_tasks) == 2


def test_get_task(temp_project):
    """Test getting a task by ID."""
    created = create_task("My task", body="Body text")

    task = get_task(created["id"])
    assert task is not None
    assert task["title"] == "My task"
    assert task["body"] == "Body text"


def test_get_nonexistent_task(temp_project):
    """Test getting a task that doesn't exist."""
    task = get_task(999)
    assert task is None


def test_close_task(temp_project):
    """Test closing a task."""
    created = create_task("Task to close")

    closed = close_task(created["id"])
    assert closed is not None
    assert closed["state"] == "closed"

    # Verify it's persisted
    task = get_task(created["id"])
    assert task["state"] == "closed"


def test_update_task(temp_project):
    """Test updating a task."""
    created = create_task("Original title", body="Original body")

    updated = update_task(
        created["id"],
        title="New title",
        body="New body",
        labels=["updated"],
    )

    assert updated is not None
    assert updated["title"] == "New title"
    assert updated["body"] == "New body"
    assert updated["labels"] == ["updated"]


def test_create_task_with_priority(temp_project):
    """Test creating a task with priority."""
    task = create_task("High priority task", priority="high")

    assert task["priority"] == "high"

    # Verify it's persisted
    loaded = get_task(task["id"])
    assert loaded["priority"] == "high"


def test_create_task_with_due(temp_project):
    """Test creating a task with due date."""
    task = create_task("Deadline task", due="2025-01-15")

    assert task["due"] == "2025-01-15"

    # Verify it's persisted
    loaded = get_task(task["id"])
    assert loaded["due"] == "2025-01-15"


def test_create_task_with_priority_and_due(temp_project):
    """Test creating a task with both priority and due date."""
    task = create_task("Urgent task", priority="high", due="2025-01-10")

    assert task["priority"] == "high"
    assert task["due"] == "2025-01-10"


def test_update_task_priority(temp_project):
    """Test updating a task's priority."""
    created = create_task("Task")

    updated = update_task(created["id"], priority="medium")
    assert updated["priority"] == "medium"

    # Clear priority with empty string
    updated = update_task(created["id"], priority="")
    assert updated["priority"] is None


def test_update_task_due(temp_project):
    """Test updating a task's due date."""
    created = create_task("Task")

    updated = update_task(created["id"], due="2025-02-01")
    assert updated["due"] == "2025-02-01"

    # Clear due date with empty string
    updated = update_task(created["id"], due="")
    assert updated["due"] is None


def test_task_priority_levels(temp_project):
    """Test that all priority levels work correctly."""
    for priority in ["high", "medium", "low"]:
        task = create_task(f"{priority} priority task", priority=priority)
        assert task["priority"] == priority

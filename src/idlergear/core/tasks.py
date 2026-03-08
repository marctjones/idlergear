"""
Task Service - Core task management logic

This service provides task operations used by both CLI and MCP server.
"""

from typing import Optional


class TaskService:
    """Core task management service"""

    def __init__(self, backend=None):
        """
        Initialize task service

        Args:
            backend: Task backend instance (defaults to auto-detected backend)
        """
        if backend is None:
            from idlergear.backends.registry import get_backend

            backend = get_backend("task")
        self.backend = backend

    def list_tasks(
        self,
        state: str = "open",
        priority: Optional[str] = None,
        labels: Optional[list[str]] = None,
        limit: Optional[int] = None,
        preview: bool = False,
    ) -> list[dict]:
        """
        List tasks with filtering

        Args:
            state: Filter by state (open/closed/all)
            priority: Filter by priority (high/medium/low)
            labels: Filter by labels (list of label names)
            limit: Maximum number of results
            preview: Strip task bodies for token efficiency

        Returns:
            List of task dictionaries
        """
        # Get tasks from backend
        tasks = self.backend.list(state=state)

        # Filter by priority if specified
        if priority:
            tasks = [t for t in tasks if t.get("priority") == priority]

        # Filter by labels if specified
        if labels:
            tasks = [
                t
                for t in tasks
                if any(label in t.get("labels", []) for label in labels)
            ]

        # Apply limit if specified
        if limit:
            tasks = tasks[:limit]

        # Strip task bodies if preview mode (token-efficient)
        if preview:
            for task in tasks:
                task["body"] = None

        return tasks

    def get_task(self, task_id: int) -> dict:
        """
        Get a single task by ID

        Args:
            task_id: Task ID

        Returns:
            Task dictionary
        """
        return self.backend.get(task_id)

    def create_task(
        self,
        title: str,
        body: Optional[str] = None,
        labels: Optional[list[str]] = None,
        priority: Optional[str] = None,
        due: Optional[str] = None,
    ) -> dict:
        """
        Create a new task

        Args:
            title: Task title
            body: Task description
            labels: Task labels
            priority: Task priority (high/medium/low)
            due: Due date (YYYY-MM-DD)

        Returns:
            Created task dictionary
        """
        return self.backend.create(
            title=title, body=body, labels=labels or [], priority=priority, due=due
        )

    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        labels: Optional[list[str]] = None,
        priority: Optional[str] = None,
        due: Optional[str] = None,
    ) -> dict:
        """
        Update a task

        Args:
            task_id: Task ID
            title: New title
            body: New body
            labels: New labels
            priority: New priority
            due: New due date

        Returns:
            Updated task dictionary
        """
        return self.backend.update(
            task_id,
            title=title,
            body=body,
            labels=labels,
            priority=priority,
            due=due,
        )

    def close_task(self, task_id: int) -> dict:
        """
        Close a task

        Args:
            task_id: Task ID

        Returns:
            Closed task dictionary
        """
        return self.backend.close(task_id)

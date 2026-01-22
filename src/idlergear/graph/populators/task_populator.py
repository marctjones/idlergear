"""Populates graph database with IdlerGear tasks (GitHub Issues)."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Set

from ..database import GraphDatabase
from idlergear.tasks import list_tasks


class TaskPopulator:
    """Populates graph database with tasks from IdlerGear backend.

    Indexes GitHub Issues or local tasks as Task nodes, enabling
    task-commit-file relationship queries.

    Example:
        >>> from idlergear.graph import get_database
        >>> db = get_database()
        >>> populator = TaskPopulator(db)
        >>> populator.populate()
    """

    def __init__(self, db: GraphDatabase, project_path: Optional[Path] = None):
        """Initialize task populator.

        Args:
            db: Graph database instance
            project_path: Path to project (defaults to current directory)
        """
        self.db = db
        self.project_path = project_path or Path.cwd()
        self._processed_tasks: Set[int] = set()

    def populate(
        self,
        state: str = "all",
        incremental: bool = True,
    ) -> Dict[str, int]:
        """Populate graph with tasks.

        Args:
            state: Task state filter ('open', 'closed', 'all')
            incremental: If True, skip tasks already in database

        Returns:
            Dictionary with counts: tasks, relationships
        """
        tasks = list_tasks(state=state, project_path=self.project_path)

        tasks_added = 0
        tasks_updated = 0
        relationships_added = 0

        conn = self.db.get_connection()

        for task in tasks:
            task_id = task.get("id")
            if not task_id:
                continue

            # Skip if already processed (incremental mode)
            if incremental and self._is_task_in_db(task_id):
                # Update if task was modified
                if self._should_update_task(task):
                    self._update_task(task)
                    tasks_updated += 1
                continue

            # Insert task node
            self._insert_task(task)
            tasks_added += 1

        return {
            "tasks": tasks_added,
            "updated": tasks_updated,
            "relationships": relationships_added,
        }

    def _is_task_in_db(self, task_id: int) -> bool:
        """Check if task already exists in database."""
        conn = self.db.get_connection()
        try:
            result = conn.execute(
                "MATCH (t:Task {id: $id}) RETURN t",
                {"id": task_id}
            )
            return result.has_next()
        except Exception:
            return False

    def _should_update_task(self, task: Dict[str, Any]) -> bool:
        """Check if task should be updated (state changed, etc.)."""
        task_id = task.get("id")
        conn = self.db.get_connection()

        try:
            result = conn.execute(
                "MATCH (t:Task {id: $id}) RETURN t.state as state",
                {"id": task_id}
            )
            if result.has_next():
                row = result.get_next()
                existing_state = row[0]
                new_state = task.get("state", "open")
                return existing_state != new_state
        except Exception:
            pass

        return False

    def _insert_task(self, task: Dict[str, Any]) -> None:
        """Insert task node into database."""
        conn = self.db.get_connection()

        # Parse timestamps
        created_at = task.get("created")
        updated_at = task.get("updated")
        closed_at = task.get("closed_at")

        # Convert to timestamp format
        created_ts = self._parse_timestamp(created_at) if created_at else None
        updated_ts = self._parse_timestamp(updated_at) if updated_at else created_ts
        closed_ts = self._parse_timestamp(closed_at) if closed_at else None

        # Labels list
        labels = task.get("labels", [])
        if isinstance(labels, str):
            labels = [labels]

        try:
            conn.execute("""
                CREATE (t:Task {
                    id: $id,
                    title: $title,
                    body: $body,
                    state: $state,
                    priority: $priority,
                    labels: $labels,
                    created_at: $created_at,
                    updated_at: $updated_at,
                    closed_at: $closed_at,
                    source: $source
                })
            """, {
                "id": task.get("id"),
                "title": task.get("title", "Untitled"),
                "body": task.get("body", ""),
                "state": task.get("state", "open"),
                "priority": task.get("priority"),
                "labels": labels,
                "created_at": created_ts,
                "updated_at": updated_ts,
                "closed_at": closed_ts,
                "source": "github" if task.get("github_issue") else "local"
            })
        except Exception as e:
            print(f"Error inserting task {task.get('id')}: {e}")

    def _update_task(self, task: Dict[str, Any]) -> None:
        """Update existing task node."""
        conn = self.db.get_connection()

        updated_at = self._parse_timestamp(task.get("updated")) if task.get("updated") else None
        closed_at = self._parse_timestamp(task.get("closed_at")) if task.get("closed_at") else None

        try:
            conn.execute("""
                MATCH (t:Task {id: $id})
                SET t.state = $state,
                    t.updated_at = $updated_at,
                    t.closed_at = $closed_at
            """, {
                "id": task.get("id"),
                "state": task.get("state", "open"),
                "updated_at": updated_at,
                "closed_at": closed_at,
            })
        except Exception as e:
            print(f"Error updating task {task.get('id')}: {e}")

    def _parse_timestamp(self, ts_str: Any) -> Optional[datetime]:
        """Parse timestamp string to datetime."""
        if not ts_str:
            return None

        if isinstance(ts_str, datetime):
            return ts_str

        try:
            # Try ISO format
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try common formats
                return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")
            except (ValueError, AttributeError):
                return None

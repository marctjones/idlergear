"""Local file-based backend implementations.

These wrap the existing IdlerGear modules to provide backend implementations
that store data in local .idlergear/ directories.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class LocalTaskBackend:
    """Local file-based task backend."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path

    def create(
        self,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        priority: str | None = None,
        due: str | None = None,
        milestone: str | None = None,
    ) -> dict[str, Any]:
        from idlergear.tasks import create_task

        return create_task(
            title,
            body=body,
            labels=labels,
            assignees=assignees,
            priority=priority,
            due=due,
            milestone=milestone,
            project_path=self.project_path,
        )

    def list(self, state: str = "open") -> list[dict[str, Any]]:
        from idlergear.tasks import list_tasks

        return list_tasks(state=state, project_path=self.project_path)

    def get(self, task_id: int) -> dict[str, Any] | None:
        from idlergear.tasks import get_task

        return get_task(task_id, project_path=self.project_path)

    def update(
        self,
        task_id: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        priority: str | None = None,
        due: str | None = None,
    ) -> dict[str, Any] | None:
        from idlergear.tasks import update_task

        return update_task(
            task_id,
            title=title,
            body=body,
            state=state,
            labels=labels,
            assignees=assignees,
            priority=priority,
            due=due,
            project_path=self.project_path,
        )

    def close(self, task_id: int, comment: str | None = None) -> dict[str, Any] | None:
        """Close a task.

        Args:
            task_id: Task ID to close
            comment: Optional closing comment (not stored in local backend)
        """
        from idlergear.tasks import close_task

        # Local backend doesn't support comments - just close the task
        return close_task(task_id, project_path=self.project_path)

    def reopen(self, task_id: int) -> dict[str, Any] | None:
        from idlergear.tasks import reopen_task

        return reopen_task(task_id, project_path=self.project_path)


class LocalNoteBackend:
    """Local file-based note backend."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path

    def create(
        self,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        from idlergear.notes import create_note

        return create_note(content, tags=tags, project_path=self.project_path)

    def list(self, tag: str | None = None) -> list[dict[str, Any]]:
        from idlergear.notes import list_notes

        return list_notes(tag=tag, project_path=self.project_path)

    def get(self, note_id: int) -> dict[str, Any] | None:
        from idlergear.notes import get_note

        return get_note(note_id, project_path=self.project_path)

    def delete(self, note_id: int) -> bool:
        from idlergear.notes import delete_note

        return delete_note(note_id, project_path=self.project_path)

    def promote(self, note_id: int, to_type: str) -> dict[str, Any] | None:
        from idlergear.notes import promote_note

        return promote_note(note_id, to_type, project_path=self.project_path)


class LocalExploreBackend:
    """Local file-based exploration backend."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path

    def create(
        self,
        title: str,
        body: str | None = None,
    ) -> dict[str, Any]:
        from idlergear.explorations import create_exploration

        return create_exploration(title, body=body, project_path=self.project_path)

    def list(self, state: str = "open") -> list[dict[str, Any]]:
        from idlergear.explorations import list_explorations

        return list_explorations(state=state, project_path=self.project_path)

    def get(self, explore_id: int) -> dict[str, Any] | None:
        from idlergear.explorations import get_exploration

        return get_exploration(explore_id, project_path=self.project_path)

    def update(
        self,
        explore_id: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any] | None:
        from idlergear.explorations import update_exploration

        return update_exploration(
            explore_id,
            title=title,
            body=body,
            state=state,
            project_path=self.project_path,
        )

    def close(self, explore_id: int) -> dict[str, Any] | None:
        from idlergear.explorations import close_exploration

        return close_exploration(explore_id, project_path=self.project_path)

    def reopen(self, explore_id: int) -> dict[str, Any] | None:
        from idlergear.explorations import reopen_exploration

        return reopen_exploration(explore_id, project_path=self.project_path)


class LocalReferenceBackend:
    """Local file-based reference backend."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path

    def add(
        self,
        title: str,
        body: str | None = None,
    ) -> dict[str, Any]:
        from idlergear.reference import add_reference

        return add_reference(title, body=body, project_path=self.project_path)

    def list(self) -> list[dict[str, Any]]:
        from idlergear.reference import list_references

        return list_references(project_path=self.project_path)

    def get(self, title: str) -> dict[str, Any] | None:
        from idlergear.reference import get_reference

        return get_reference(title, project_path=self.project_path)

    def get_by_id(self, ref_id: int) -> dict[str, Any] | None:
        from idlergear.reference import get_reference_by_id

        return get_reference_by_id(ref_id, project_path=self.project_path)

    def update(
        self,
        title: str,
        new_title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any] | None:
        from idlergear.reference import update_reference

        return update_reference(
            title, new_title=new_title, body=body, project_path=self.project_path
        )

    def search(self, query: str) -> list[dict[str, Any]]:
        from idlergear.reference import search_references

        return search_references(query, project_path=self.project_path)


class LocalPlanBackend:
    """Local file-based plan backend."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path

    def create(
        self,
        name: str,
        title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        from idlergear.plans import create_plan
        from pathlib import Path

        # Map old interface (title/body) to new interface (description)
        # Use title as description, or body if title not provided
        description = title or body or "No description"

        plan = create_plan(
            name=name,
            description=description,
            root=self.project_path or Path.cwd(),
        )

        # Convert Plan object to dict for backward compatibility
        return {
            "name": plan.name,
            "description": plan.description,
            "status": plan.status,
            "type": plan.type,
            "created": plan.created,
        }

    def list(self) -> list[dict[str, Any]]:
        from idlergear.plans import list_plans
        from pathlib import Path

        plans = list_plans(root=self.project_path or Path.cwd())

        # Convert Plan objects to dicts
        return [
            {
                "name": p.name,
                "description": p.description,
                "status": p.status,
                "type": p.type,
                "created": p.created,
            }
            for p in plans
        ]

    def get(self, name: str) -> dict[str, Any] | None:
        from idlergear.plans import load_plan
        from pathlib import Path

        try:
            plan = load_plan(name, root=self.project_path or Path.cwd())
            return {
                "name": plan.name,
                "description": plan.description,
                "status": plan.status,
                "type": plan.type,
                "created": plan.created,
            }
        except FileNotFoundError:
            return None

    def get_current(self) -> dict[str, Any] | None:
        """Get current plan (deprecated - Plan Objects doesn't have current plan concept)."""
        from idlergear.plans import list_plans
        from pathlib import Path

        # Return first active plan as a fallback
        plans = list_plans(root=self.project_path or Path.cwd(), status="active")
        if plans:
            p = plans[0]
            return {
                "name": p.name,
                "description": p.description,
                "status": p.status,
                "type": p.type,
                "created": p.created,
            }
        return None

    def switch(self, name: str) -> dict[str, Any] | None:
        """Switch plan (deprecated - Plan Objects doesn't have switch concept)."""
        # Just return the plan if it exists
        return self.get(name)

    def update(
        self,
        name: str,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any] | None:
        from idlergear.plans import update_plan
        from pathlib import Path

        updates = {}
        if title:
            updates["description"] = title
        if state:
            updates["status"] = state

        try:
            plan = update_plan(
                name=name,
                root=self.project_path or Path.cwd(),
                **updates
            )
            return {
                "name": plan.name,
                "description": plan.description,
                "status": plan.status,
                "type": plan.type,
                "created": plan.created,
            }
        except FileNotFoundError:
            return None


class LocalVisionBackend:
    """Local file-based vision backend."""

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path

    def get(self) -> str | None:
        from idlergear.vision import get_vision

        return get_vision(project_path=self.project_path)

    def set(self, content: str) -> None:
        from idlergear.vision import set_vision

        set_vision(content, project_path=self.project_path)

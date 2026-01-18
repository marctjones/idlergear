"""Backend protocol definitions for IdlerGear.

These protocols define the interface that all backends must implement.
Each knowledge type has its own protocol.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class TaskBackend(Protocol):
    """Protocol for task management backends."""

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
        """Create a new task."""
        ...

    def list(self, state: str = "open") -> list[dict[str, Any]]:
        """List tasks filtered by state (open, closed, all)."""
        ...

    def get(self, task_id: int) -> dict[str, Any] | None:
        """Get a task by ID."""
        ...

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
        """Update a task."""
        ...

    def close(self, task_id: int, comment: str | None = None) -> dict[str, Any] | None:
        """Close a task.

        Args:
            task_id: Task ID to close
            comment: Optional closing comment
        """
        ...

    def reopen(self, task_id: int) -> dict[str, Any] | None:
        """Reopen a closed task."""
        ...


@runtime_checkable
class NoteBackend(Protocol):
    """Protocol for note management backends."""

    def create(
        self,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new note with optional tags."""
        ...

    def list(self, tag: str | None = None) -> list[dict[str, Any]]:
        """List notes, optionally filtered by tag."""
        ...

    def get(self, note_id: int) -> dict[str, Any] | None:
        """Get a note by ID."""
        ...

    def delete(self, note_id: int) -> bool:
        """Delete a note. Returns True if deleted."""
        ...

    def promote(self, note_id: int, to_type: str) -> dict[str, Any] | None:
        """Promote a note to another type (task, explore, reference)."""
        ...


@runtime_checkable
class ExploreBackend(Protocol):
    """Protocol for exploration management backends."""

    def create(
        self,
        title: str,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Create a new exploration."""
        ...

    def list(self, state: str = "open") -> list[dict[str, Any]]:
        """List explorations filtered by state."""
        ...

    def get(self, explore_id: int) -> dict[str, Any] | None:
        """Get an exploration by ID."""
        ...

    def update(
        self,
        explore_id: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any] | None:
        """Update an exploration."""
        ...

    def close(self, explore_id: int) -> dict[str, Any] | None:
        """Close an exploration."""
        ...

    def reopen(self, explore_id: int) -> dict[str, Any] | None:
        """Reopen an exploration."""
        ...


@runtime_checkable
class ReferenceBackend(Protocol):
    """Protocol for reference document backends."""

    def add(
        self,
        title: str,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Add a new reference document."""
        ...

    def list(self) -> list[dict[str, Any]]:
        """List all reference documents."""
        ...

    def get(self, title: str) -> dict[str, Any] | None:
        """Get a reference by title."""
        ...

    def get_by_id(self, ref_id: int) -> dict[str, Any] | None:
        """Get a reference by ID."""
        ...

    def update(
        self,
        title: str,
        new_title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a reference document."""
        ...

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search reference documents."""
        ...


@runtime_checkable
class PlanBackend(Protocol):
    """Protocol for plan management backends."""

    def create(
        self,
        name: str,
        title: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Create a new plan."""
        ...

    def list(self) -> list[dict[str, Any]]:
        """List all plans."""
        ...

    def get(self, name: str) -> dict[str, Any] | None:
        """Get a plan by name."""
        ...

    def get_current(self) -> dict[str, Any] | None:
        """Get the current active plan."""
        ...

    def switch(self, name: str) -> dict[str, Any] | None:
        """Switch to a plan."""
        ...

    def update(
        self,
        name: str,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a plan."""
        ...


@runtime_checkable
class VisionBackend(Protocol):
    """Protocol for vision management backends."""

    def get(self) -> str | None:
        """Get the project vision."""
        ...

    def set(self, content: str) -> None:
        """Set the project vision."""
        ...

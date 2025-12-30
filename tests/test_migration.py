"""Tests for backend migration functionality."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from idlergear.migration import (
    migrate_backend,
    migrate_explorations,
    migrate_notes,
    migrate_references,
    migrate_tasks,
)


class MockTaskBackend:
    """Mock task backend for testing."""

    def __init__(self, tasks: list[dict] | None = None):
        self.tasks = tasks or []
        self.created = []
        self.closed = []

    def list(self, state: str = "open") -> list[dict]:
        if state == "all":
            return self.tasks
        return [t for t in self.tasks if t.get("state") == state]

    def create(
        self,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
        priority: str | None = None,
        due: str | None = None,
    ) -> dict:
        task = {
            "id": len(self.created) + 1,
            "title": title,
            "body": body,
            "labels": labels or [],
            "assignees": assignees or [],
            "priority": priority,
            "due": due,
            "state": "open",
        }
        self.created.append(task)
        return task

    def close(self, task_id: int) -> dict | None:
        self.closed.append(task_id)
        for task in self.created:
            if task["id"] == task_id:
                task["state"] = "closed"
                return task
        return None


class MockExploreBackend:
    """Mock explore backend for testing."""

    def __init__(self, explorations: list[dict] | None = None):
        self.explorations = explorations or []
        self.created = []
        self.closed = []

    def list(self, state: str = "open") -> list[dict]:
        if state == "all":
            return self.explorations
        return [e for e in self.explorations if e.get("state") == state]

    def create(self, title: str, body: str | None = None) -> dict:
        explore = {
            "id": len(self.created) + 1,
            "title": title,
            "body": body,
            "state": "open",
        }
        self.created.append(explore)
        return explore

    def close(self, explore_id: int) -> dict | None:
        self.closed.append(explore_id)
        for e in self.created:
            if e["id"] == explore_id:
                e["state"] = "closed"
                return e
        return None


class MockReferenceBackend:
    """Mock reference backend for testing."""

    def __init__(self, references: list[dict] | None = None):
        self.references = references or []
        self.added = []

    def list(self) -> list[dict]:
        return self.references

    def add(self, title: str, body: str | None = None) -> dict:
        ref = {
            "id": len(self.added) + 1,
            "title": title,
            "body": body,
        }
        self.added.append(ref)
        return ref


class MockNoteBackend:
    """Mock note backend for testing."""

    def __init__(self, notes: list[dict] | None = None):
        self.notes = notes or []
        self.created = []

    def list(self) -> list[dict]:
        return self.notes

    def create(self, content: str) -> dict:
        note = {
            "id": len(self.created) + 1,
            "content": content,
        }
        self.created.append(note)
        return note


class TestMigrateTasks:
    """Tests for migrate_tasks function."""

    def test_migrate_empty(self) -> None:
        """Test migrating with no tasks."""
        source = MockTaskBackend([])
        target = MockTaskBackend()

        stats = migrate_tasks(source, target)

        assert stats["total"] == 0
        assert stats["migrated"] == 0
        assert stats["errors"] == 0

    def test_migrate_open_tasks(self) -> None:
        """Test migrating open tasks."""
        source = MockTaskBackend([
            {"id": 1, "title": "Task 1", "body": "Body 1", "state": "open"},
            {"id": 2, "title": "Task 2", "body": "Body 2", "state": "open"},
        ])
        target = MockTaskBackend()

        stats = migrate_tasks(source, target, state="all")

        assert stats["total"] == 2
        assert stats["migrated"] == 2
        assert len(target.created) == 2
        assert target.created[0]["title"] == "Task 1"

    def test_migrate_closed_tasks(self) -> None:
        """Test migrating closed tasks preserves state."""
        source = MockTaskBackend([
            {"id": 1, "title": "Closed Task", "state": "closed"},
        ])
        target = MockTaskBackend()

        stats = migrate_tasks(source, target, state="all")

        assert stats["migrated"] == 1
        # Task should be closed in target
        assert 1 in target.closed

    def test_migrate_with_labels_and_priority(self) -> None:
        """Test migrating tasks with metadata."""
        source = MockTaskBackend([
            {
                "id": 1,
                "title": "Task",
                "body": "Body",
                "labels": ["bug", "urgent"],
                "priority": "high",
                "due": "2024-12-31",
                "state": "open",
            },
        ])
        target = MockTaskBackend()

        migrate_tasks(source, target, state="all")

        created = target.created[0]
        assert created["labels"] == ["bug", "urgent"]
        assert created["priority"] == "high"
        assert created["due"] == "2024-12-31"

    def test_migrate_with_callback(self) -> None:
        """Test migrate callback is called."""
        source = MockTaskBackend([
            {"id": 1, "title": "Task 1", "state": "open"},
        ])
        target = MockTaskBackend()

        items = []
        def on_item(info: dict) -> None:
            items.append(info)

        migrate_tasks(source, target, state="all", on_item=on_item)

        assert len(items) == 1
        assert items[0]["source"]["id"] == 1
        assert items[0]["target"]["id"] == 1

    def test_migrate_with_error_callback(self) -> None:
        """Test error callback is called on failure."""
        source = MockTaskBackend([
            {"id": 1, "title": "Task 1", "state": "open"},
        ])
        target = MagicMock()
        target.create.side_effect = Exception("Create failed")

        errors = []
        def on_error(item: dict, error: Exception) -> None:
            errors.append((item, error))

        stats = migrate_tasks(source, target, state="all", on_error=on_error)

        assert stats["errors"] == 1
        assert len(errors) == 1
        assert errors[0][0]["id"] == 1


class TestMigrateExplorations:
    """Tests for migrate_explorations function."""

    def test_migrate_explorations(self) -> None:
        """Test migrating explorations."""
        source = MockExploreBackend([
            {"id": 1, "title": "Explore 1", "body": "Body", "state": "open"},
        ])
        target = MockExploreBackend()

        stats = migrate_explorations(source, target, state="all")

        assert stats["migrated"] == 1
        assert target.created[0]["title"] == "Explore 1"

    def test_migrate_closed_exploration(self) -> None:
        """Test closed exploration is closed in target."""
        source = MockExploreBackend([
            {"id": 1, "title": "Done Explore", "state": "closed"},
        ])
        target = MockExploreBackend()

        migrate_explorations(source, target, state="all")

        assert 1 in target.closed


class TestMigrateReferences:
    """Tests for migrate_references function."""

    def test_migrate_references(self) -> None:
        """Test migrating references."""
        source = MockReferenceBackend([
            {"id": 1, "title": "Ref 1", "body": "Content 1"},
            {"id": 2, "title": "Ref 2", "body": "Content 2"},
        ])
        target = MockReferenceBackend()

        stats = migrate_references(source, target)

        assert stats["migrated"] == 2
        assert target.added[0]["title"] == "Ref 1"


class TestMigrateNotes:
    """Tests for migrate_notes function."""

    def test_migrate_notes(self) -> None:
        """Test migrating notes."""
        source = MockNoteBackend([
            {"id": 1, "content": "Note 1"},
            {"id": 2, "content": "Note 2"},
        ])
        target = MockNoteBackend()

        stats = migrate_notes(source, target)

        assert stats["migrated"] == 2
        assert target.created[0]["content"] == "Note 1"


class TestMigrateBackend:
    """Tests for migrate_backend function."""

    def test_migrate_backend_invalid_type(self) -> None:
        """Test error on invalid backend type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / ".idlergear").mkdir()

            with pytest.raises(ValueError) as exc_info:
                migrate_backend("invalid", "local", "github", project)

            assert "Unknown backend type" in str(exc_info.value)

    def test_migrate_backend_invalid_source(self) -> None:
        """Test error on invalid source backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / ".idlergear").mkdir()

            with pytest.raises(ValueError) as exc_info:
                migrate_backend("task", "nonexistent", "local", project)

            assert "Unknown source backend" in str(exc_info.value)

    def test_migrate_backend_invalid_target(self) -> None:
        """Test error on invalid target backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            (project / ".idlergear").mkdir()

            with pytest.raises(ValueError) as exc_info:
                migrate_backend("task", "local", "nonexistent", project)

            assert "Unknown target backend" in str(exc_info.value)

    def test_migrate_backend_dry_run(self) -> None:
        """Test dry run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)
            idlergear_dir = project / ".idlergear"
            idlergear_dir.mkdir()

            # Create some tasks
            tasks_dir = idlergear_dir / "tasks"
            tasks_dir.mkdir()
            (tasks_dir / "0001-test-task.md").write_text("""---
id: 1
title: Test Task
state: open
labels: []
assignees: []
---

Task body
""")

            stats = migrate_backend(
                "task", "local", "local", project, dry_run=True
            )

            assert stats["dry_run"] is True
            assert stats["total"] == 1
            assert stats["migrated"] == 0

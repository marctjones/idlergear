"""Tests for backend abstraction layer."""

import pytest

from idlergear.backends import (
    ExploreBackend,
    NoteBackend,
    PlanBackend,
    ReferenceBackend,
    TaskBackend,
    VisionBackend,
    clear_backend_cache,
    get_backend,
    get_configured_backend_name,
    list_available_backends,
)
from idlergear.backends.local import (
    LocalExploreBackend,
    LocalNoteBackend,
    LocalPlanBackend,
    LocalReferenceBackend,
    LocalTaskBackend,
    LocalVisionBackend,
)


class TestBackendRegistry:
    """Tests for backend registry functions."""

    def test_get_task_backend(self, temp_project):
        """Get task backend returns local by default."""
        backend = get_backend("task")
        assert isinstance(backend, LocalTaskBackend)

    def test_get_note_backend(self, temp_project):
        """Get note backend returns local by default."""
        backend = get_backend("note")
        assert isinstance(backend, LocalNoteBackend)

    def test_get_explore_backend(self, temp_project):
        """Get explore backend returns local by default."""
        backend = get_backend("explore")
        assert isinstance(backend, LocalExploreBackend)

    def test_get_reference_backend(self, temp_project):
        """Get reference backend returns local by default."""
        backend = get_backend("reference")
        assert isinstance(backend, LocalReferenceBackend)

    def test_get_plan_backend(self, temp_project):
        """Get plan backend returns local by default."""
        backend = get_backend("plan")
        assert isinstance(backend, LocalPlanBackend)

    def test_get_vision_backend(self, temp_project):
        """Get vision backend returns local by default."""
        backend = get_backend("vision")
        assert isinstance(backend, LocalVisionBackend)

    def test_backend_caching(self, temp_project):
        """Backend instances are cached."""
        backend1 = get_backend("task")
        backend2 = get_backend("task")
        assert backend1 is backend2

    def test_clear_cache(self, temp_project):
        """Clear cache creates new instances."""
        backend1 = get_backend("task")
        clear_backend_cache()
        backend2 = get_backend("task")
        assert backend1 is not backend2

    def test_get_configured_backend_name(self, temp_project):
        """Get configured backend name returns local by default."""
        name = get_configured_backend_name("task")
        assert name == "local"

    def test_list_available_backends(self, temp_project):
        """List available backends includes local."""
        backends = list_available_backends("task")
        assert "local" in backends

    def test_unknown_backend_type(self, temp_project):
        """Unknown backend type raises error."""
        with pytest.raises(ValueError, match="Unknown backend type"):
            get_backend("invalid_type")


class TestProtocolCompliance:
    """Tests that local backends implement protocols correctly."""

    def test_task_backend_protocol(self, temp_project):
        """LocalTaskBackend implements TaskBackend protocol."""
        backend = LocalTaskBackend()
        assert isinstance(backend, TaskBackend)

    def test_note_backend_protocol(self, temp_project):
        """LocalNoteBackend implements NoteBackend protocol."""
        backend = LocalNoteBackend()
        assert isinstance(backend, NoteBackend)

    def test_explore_backend_protocol(self, temp_project):
        """LocalExploreBackend implements ExploreBackend protocol."""
        backend = LocalExploreBackend()
        assert isinstance(backend, ExploreBackend)

    def test_reference_backend_protocol(self, temp_project):
        """LocalReferenceBackend implements ReferenceBackend protocol."""
        backend = LocalReferenceBackend()
        assert isinstance(backend, ReferenceBackend)

    def test_plan_backend_protocol(self, temp_project):
        """LocalPlanBackend implements PlanBackend protocol."""
        backend = LocalPlanBackend()
        assert isinstance(backend, PlanBackend)

    def test_vision_backend_protocol(self, temp_project):
        """LocalVisionBackend implements VisionBackend protocol."""
        backend = LocalVisionBackend()
        assert isinstance(backend, VisionBackend)


class TestLocalTaskBackend:
    """Tests for LocalTaskBackend."""

    def test_create_task(self, temp_project):
        """Create task through backend."""
        backend = get_backend("task")
        task = backend.create("Test task", body="Description")

        assert task["id"] == 1
        assert task["title"] == "Test task"
        assert task["body"] == "Description"

    def test_list_tasks(self, temp_project):
        """List tasks through backend."""
        backend = get_backend("task")
        backend.create("Task 1")
        backend.create("Task 2")

        tasks = backend.list()
        assert len(tasks) == 2

    def test_get_task(self, temp_project):
        """Get task through backend."""
        backend = get_backend("task")
        created = backend.create("Test")

        task = backend.get(created["id"])
        assert task["title"] == "Test"

    def test_update_task(self, temp_project):
        """Update task through backend."""
        backend = get_backend("task")
        created = backend.create("Original")

        updated = backend.update(created["id"], title="Updated")
        assert updated["title"] == "Updated"

    def test_close_task(self, temp_project):
        """Close task through backend."""
        backend = get_backend("task")
        created = backend.create("Test")

        closed = backend.close(created["id"])
        assert closed["state"] == "closed"

    def test_reopen_task(self, temp_project):
        """Reopen task through backend."""
        backend = get_backend("task")
        created = backend.create("Test")
        backend.close(created["id"])

        reopened = backend.reopen(created["id"])
        assert reopened["state"] == "open"

    def test_task_with_priority_and_due(self, temp_project):
        """Create task with priority and due through backend."""
        backend = get_backend("task")
        task = backend.create("Urgent", priority="high", due="2025-01-15")

        assert task["priority"] == "high"
        assert task["due"] == "2025-01-15"


class TestLocalNoteBackend:
    """Tests for LocalNoteBackend."""

    def test_create_note(self, temp_project):
        """Create note through backend."""
        backend = get_backend("note")
        note = backend.create("Test note content")

        assert note["id"] == 1
        assert note["content"] == "Test note content"

    def test_list_notes(self, temp_project):
        """List notes through backend."""
        backend = get_backend("note")
        backend.create("Note 1")
        backend.create("Note 2")

        notes = backend.list()
        assert len(notes) == 2

    def test_delete_note(self, temp_project):
        """Delete note through backend."""
        backend = get_backend("note")
        note = backend.create("To delete")

        assert backend.delete(note["id"]) is True
        assert backend.get(note["id"]) is None


class TestLocalExploreBackend:
    """Tests for LocalExploreBackend."""

    def test_create_exploration(self, temp_project):
        """Create exploration through backend."""
        backend = get_backend("explore")
        exp = backend.create("Test exploration", body="Details")

        assert exp["id"] == 1
        assert exp["title"] == "Test exploration"

    def test_close_exploration(self, temp_project):
        """Close exploration through backend."""
        backend = get_backend("explore")
        exp = backend.create("Test")

        closed = backend.close(exp["id"])
        assert closed["state"] == "closed"


class TestLocalReferenceBackend:
    """Tests for LocalReferenceBackend."""

    def test_add_reference(self, temp_project):
        """Add reference through backend."""
        backend = get_backend("reference")
        ref = backend.add("API Guide", body="Documentation")

        assert ref["title"] == "API Guide"
        assert ref["body"] == "Documentation"

    def test_search_references(self, temp_project):
        """Search references through backend."""
        backend = get_backend("reference")
        backend.add("Python Guide", body="Python tips")
        backend.add("Other Doc")

        results = backend.search("python")
        assert len(results) == 1


class TestLocalPlanBackend:
    """Tests for LocalPlanBackend."""

    def test_create_plan(self, temp_project):
        """Create plan through backend."""
        backend = get_backend("plan")
        plan = backend.create("v1-release", title="Version 1")

        assert plan["name"] == "v1-release"
        assert plan["description"] == "Version 1"  # Plan Objects uses "description"

    def test_switch_plan(self, temp_project):
        """Switch plan through backend."""
        backend = get_backend("plan")
        backend.create("my-plan")

        switched = backend.switch("my-plan")
        assert switched["name"] == "my-plan"

        current = backend.get_current()
        assert current["name"] == "my-plan"


class TestLocalVisionBackend:
    """Tests for LocalVisionBackend."""

    def test_set_and_get_vision(self, temp_project):
        """Set and get vision through backend."""
        backend = get_backend("vision")
        backend.set("Project vision content")

        vision = backend.get()
        assert vision == "Project vision content"

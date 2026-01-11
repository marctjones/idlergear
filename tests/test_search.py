"""Tests for cross-type search functionality."""

from idlergear.explorations import create_exploration
from idlergear.notes import create_note
from idlergear.plans import create_plan
from idlergear.reference import add_reference
from idlergear.search import search_all
from idlergear.tasks import create_task


class TestSearchAll:
    """Tests for search_all function."""

    def test_search_empty(self, temp_project):
        """Search with no items returns empty list."""
        results = search_all("test")
        assert results == []

    def test_search_tasks_by_title(self, temp_project):
        """Search finds tasks by title."""
        create_task("Fix authentication bug")
        create_task("Add user dashboard")

        results = search_all("auth")
        assert len(results) == 1
        assert results[0]["type"] == "task"
        assert results[0]["title"] == "Fix authentication bug"

    def test_search_tasks_by_body(self, temp_project):
        """Search finds tasks by body content."""
        create_task("Task 1", body="Contains unique keyword foobar123")
        create_task("Task 2", body="Different content")

        results = search_all("foobar123")
        assert len(results) == 1
        assert results[0]["title"] == "Task 1"

    def test_search_notes(self, temp_project):
        """Search finds notes by content."""
        create_note("Remember to update the API")
        create_note("Different note")

        results = search_all("API")
        assert len(results) == 1
        assert results[0]["type"] == "note"

    def test_search_explorations(self, temp_project):
        """Search finds explorations by title and body."""
        create_exploration("Database optimization", body="Exploring query performance")
        create_exploration("Other topic")

        results = search_all("optimization")
        assert len(results) == 1
        assert results[0]["type"] == "explore"

    def test_search_references(self, temp_project):
        """Search finds references by title and body."""
        add_reference("API Documentation", body="REST endpoints guide")
        add_reference("Other doc")

        results = search_all("REST")
        assert len(results) == 1
        assert results[0]["type"] == "reference"

    def test_search_plans(self, temp_project):
        """Search finds plans by name, title, and body."""
        create_plan("v2-release", title="Version 2 Release", body="Major refactoring")
        create_plan("other-plan")

        results = search_all("refactoring")
        assert len(results) == 1
        assert results[0]["type"] == "plan"

    def test_search_across_types(self, temp_project):
        """Search finds items across multiple types."""
        create_task("Update documentation")
        create_note("Document the new feature")
        add_reference("Documentation Guide")

        results = search_all("document")
        assert len(results) == 3
        types = {r["type"] for r in results}
        assert types == {"task", "note", "reference"}

    def test_search_case_insensitive(self, temp_project):
        """Search is case insensitive."""
        create_task("UPPERCASE Task")
        create_note("lowercase note")

        upper_results = search_all("UPPERCASE")
        lower_results = search_all("lowercase")

        assert len(upper_results) == 1
        assert len(lower_results) == 1

    def test_search_filter_by_type(self, temp_project):
        """Search can filter by specific types."""
        create_task("Common keyword")
        create_note("Common keyword")
        add_reference("Common keyword")

        results = search_all("common", types=["task"])
        assert len(results) == 1
        assert results[0]["type"] == "task"

        results = search_all("common", types=["task", "note"])
        assert len(results) == 2

    def test_search_multiple_types_filter(self, temp_project):
        """Search can filter by multiple types."""
        create_task("Searchable item")
        create_note("Searchable item")
        create_exploration("Searchable item")

        results = search_all("searchable", types=["task", "explore"])
        assert len(results) == 2
        types = {r["type"] for r in results}
        assert types == {"task", "explore"}

    def test_search_results_include_metadata(self, temp_project):
        """Search results include relevant metadata."""
        task = create_task("High priority bug", priority="high", due="2025-01-15")

        results = search_all("priority")
        assert len(results) == 1
        result = results[0]
        assert result["priority"] == "high"
        assert result["due"] == "2025-01-15"

    def test_search_no_results(self, temp_project):
        """Search returns empty list when nothing matches."""
        create_task("Something completely different")

        results = search_all("nonexistent12345")
        assert results == []

    def test_search_preview_context(self, temp_project):
        """Search results include preview with context."""
        create_task(
            "Task title",
            body="This is a longer body with the keyword uniqueterm here in the middle",
        )

        results = search_all("uniqueterm")
        assert len(results) == 1
        assert "uniqueterm" in results[0]["preview"]

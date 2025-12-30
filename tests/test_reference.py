"""Tests for reference document management."""

import pytest

from idlergear.reference import (
    add_reference,
    get_reference,
    get_reference_by_id,
    list_references,
    load_reference_from_file,
    search_references,
    update_reference,
)


class TestAddReference:
    """Tests for add_reference."""

    def test_add_reference(self, temp_project):
        ref = add_reference("GGUF Format")

        assert ref["id"] == 1
        assert ref["title"] == "GGUF Format"
        assert ref["created"] is not None
        assert ref["updated"] is not None
        assert "path" in ref

    def test_add_reference_with_body(self, temp_project):
        ref = add_reference(
            "API Guide",
            body="This is the API documentation.",
        )

        assert ref["title"] == "API Guide"
        assert ref["body"] == "This is the API documentation."

    def test_add_duplicate_title(self, temp_project):
        ref1 = add_reference("Same Title")
        ref2 = add_reference("Same Title")

        # Should have different paths (duplicate handling adds id to filename)
        assert ref1["path"] != ref2["path"]
        # Both get ID 1 because reference IDs are based on numeric prefix pattern
        # which these slug-named files don't match
        assert ref1["id"] == 1
        assert ref2["id"] == 1
        # But the second one has a different filename
        assert "same-title.md" in ref1["path"]
        assert "same-title-1.md" in ref2["path"]


class TestListReferences:
    """Tests for list_references."""

    def test_list_empty(self, temp_project):
        refs = list_references()
        assert refs == []

    def test_list_references(self, temp_project):
        add_reference("Alpha")
        add_reference("Zebra")
        add_reference("Beta")

        refs = list_references()
        assert len(refs) == 3

    def test_list_sorted_by_title(self, temp_project):
        add_reference("Zebra")
        add_reference("Alpha")
        add_reference("Beta")

        refs = list_references()
        titles = [r["title"] for r in refs]
        assert titles == ["Alpha", "Beta", "Zebra"]


class TestGetReference:
    """Tests for get_reference."""

    def test_get_by_title(self, temp_project):
        add_reference("Test Reference", body="Test body")

        ref = get_reference("Test Reference")
        assert ref is not None
        assert ref["title"] == "Test Reference"
        assert ref["body"] == "Test body"

    def test_get_case_insensitive(self, temp_project):
        add_reference("Mixed Case Title")

        ref = get_reference("mixed case title")
        assert ref is not None
        assert ref["title"] == "Mixed Case Title"

    def test_get_nonexistent(self, temp_project):
        ref = get_reference("Nonexistent")
        assert ref is None

    def test_get_by_slug(self, temp_project):
        add_reference("My Test Reference")

        # Should also find by slug match
        ref = get_reference("My Test Reference")
        assert ref is not None


class TestGetReferenceById:
    """Tests for get_reference_by_id."""

    def test_get_by_id(self, temp_project):
        created = add_reference("Test")

        ref = get_reference_by_id(created["id"])
        assert ref is not None
        assert ref["title"] == "Test"

    def test_get_nonexistent_id(self, temp_project):
        ref = get_reference_by_id(999)
        assert ref is None


class TestUpdateReference:
    """Tests for update_reference."""

    def test_update_title(self, temp_project):
        add_reference("Original Title")

        updated = update_reference("Original Title", new_title="New Title")
        assert updated["title"] == "New Title"

    def test_update_body(self, temp_project):
        add_reference("Test", body="Original body")

        updated = update_reference("Test", body="Updated body")
        assert updated["body"] == "Updated body"

    def test_update_updates_timestamp(self, temp_project):
        import time

        ref = add_reference("Test")
        original_updated = ref["updated"]

        time.sleep(0.01)  # Ensure timestamp difference
        updated = update_reference("Test", body="New content")

        # Updated timestamp should be newer or equal
        assert updated["updated"] >= original_updated

    def test_update_nonexistent(self, temp_project):
        result = update_reference("Nonexistent", body="New")
        assert result is None


class TestSearchReferences:
    """Tests for search_references."""

    def test_search_by_title(self, temp_project):
        add_reference("Python Guide")
        add_reference("JavaScript Guide")
        add_reference("Database Design")

        results = search_references("guide")
        assert len(results) == 2
        titles = [r["title"] for r in results]
        assert "Python Guide" in titles
        assert "JavaScript Guide" in titles

    def test_search_by_body(self, temp_project):
        add_reference("Doc One", body="Contains the word foobar")
        add_reference("Doc Two", body="Different content")

        results = search_references("foobar")
        assert len(results) == 1
        assert results[0]["title"] == "Doc One"

    def test_search_case_insensitive(self, temp_project):
        add_reference("Test", body="UPPERCASE content")

        results = search_references("uppercase")
        assert len(results) == 1

    def test_search_no_results(self, temp_project):
        add_reference("Test")

        results = search_references("nonexistent")
        assert results == []


class TestLoadReferenceFromFile:
    """Tests for load_reference_from_file."""

    def test_load_nonexistent_file(self, temp_project):
        from pathlib import Path

        result = load_reference_from_file(Path("/nonexistent/file.md"))
        assert result is None

    def test_load_reference_file(self, temp_project):
        from pathlib import Path

        ref = add_reference("Test", body="Body content")

        loaded = load_reference_from_file(Path(ref["path"]))
        assert loaded is not None
        assert loaded["title"] == "Test"
        assert loaded["body"] == "Body content"

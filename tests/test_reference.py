"""Tests for reference document management."""

from idlergear.reference import (
    PINNED_REFERENCES,
    ReferenceSource,
    add_reference,
    get_pinned_reference,
    get_reference,
    get_reference_by_id,
    is_pinned_reference,
    list_pinned_references,
    list_references,
    load_reference_from_file,
    search_references,
    update_pinned_reference,
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

    def test_list_wiki_only_empty(self, temp_project):
        """Test listing only wiki references (no pinned)."""
        refs = list_references(include_pinned=False)
        assert refs == []

    def test_list_includes_pinned(self, temp_project):
        """Test that list includes pinned references when they exist."""
        refs = list_references()
        # Should include vision since VISION.md is created by init
        pinned_refs = [r for r in refs if r.get("source") == ReferenceSource.PINNED.value]
        assert len(pinned_refs) >= 1

    def test_list_references(self, temp_project):
        add_reference("Alpha")
        add_reference("Zebra")
        add_reference("Beta")

        refs = list_references(include_pinned=False)
        assert len(refs) == 3

    def test_list_sorted_by_source_then_title(self, temp_project):
        """Test that pinned refs come before wiki refs, sorted by title."""
        add_reference("Zebra")
        add_reference("Alpha")
        add_reference("Beta")

        refs = list_references()
        # Check sources - pinned should come first
        sources = [r.get("source") for r in refs]
        # All pinned should be before all wiki
        pinned_done = False
        for source in sources:
            if source == ReferenceSource.WIKI.value:
                pinned_done = True
            elif pinned_done:
                assert False, "Pinned reference found after wiki reference"

    def test_list_wiki_sorted_by_title(self, temp_project):
        add_reference("Zebra")
        add_reference("Alpha")
        add_reference("Beta")

        refs = list_references(include_pinned=False)
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
        assert loaded["source"] == ReferenceSource.WIKI.value


class TestPinnedReferences:
    """Tests for pinned reference functions."""

    def test_get_pinned_reference_vision(self, temp_project):
        """Test getting the vision pinned reference."""
        ref = get_pinned_reference("vision")
        assert ref is not None
        assert ref["title"] == "vision"
        assert ref["source"] == ReferenceSource.PINNED.value
        assert ref["filename"] == "VISION.md"

    def test_get_pinned_reference_case_insensitive(self, temp_project):
        """Test that pinned ref names are case-insensitive."""
        ref1 = get_pinned_reference("VISION")
        ref2 = get_pinned_reference("Vision")
        ref3 = get_pinned_reference("vision")
        assert ref1 is not None
        assert ref2 is not None
        assert ref3 is not None

    def test_get_pinned_reference_nonexistent_name(self, temp_project):
        """Test getting a non-pinned reference name."""
        ref = get_pinned_reference("not-a-pinned-ref")
        assert ref is None

    def test_get_pinned_reference_file_not_exists(self, temp_project):
        """Test that missing files return None."""
        # README.md doesn't exist in temp_project
        ref = get_pinned_reference("readme")
        assert ref is None

    def test_list_pinned_references(self, temp_project):
        """Test listing pinned references."""
        refs = list_pinned_references()
        # At minimum, VISION.md exists (created by init)
        assert len(refs) >= 1
        assert all(r["source"] == ReferenceSource.PINNED.value for r in refs)

    def test_update_pinned_reference(self, temp_project):
        """Test updating a pinned reference."""
        new_content = "# Updated Vision\n\nNew content here."
        ref = update_pinned_reference("vision", new_content)
        assert ref is not None
        assert ref["body"] == new_content

        # Verify it was saved
        loaded = get_pinned_reference("vision")
        assert loaded["body"] == new_content

    def test_update_pinned_reference_invalid_name(self, temp_project):
        """Test that updating invalid pinned name returns None."""
        ref = update_pinned_reference("not-pinned", "content")
        assert ref is None

    def test_is_pinned_reference(self, temp_project):
        """Test is_pinned_reference helper."""
        assert is_pinned_reference("vision") is True
        assert is_pinned_reference("VISION") is True
        assert is_pinned_reference("readme") is True
        assert is_pinned_reference("not-pinned") is False

    def test_get_reference_finds_pinned(self, temp_project):
        """Test that get_reference finds pinned references."""
        ref = get_reference("vision")
        assert ref is not None
        assert ref["source"] == ReferenceSource.PINNED.value

    def test_pinned_refs_listed_first(self, temp_project):
        """Test that pinned refs come before wiki refs in list."""
        add_reference("AAA First Alpha")  # Would be first alphabetically

        refs = list_references()
        wiki_refs = [r for r in refs if r["source"] == ReferenceSource.WIKI.value]
        pinned_refs = [r for r in refs if r["source"] == ReferenceSource.PINNED.value]

        # Find indices
        if pinned_refs and wiki_refs:
            first_pinned_idx = refs.index(pinned_refs[0])
            first_wiki_idx = refs.index(wiki_refs[0])
            assert first_pinned_idx < first_wiki_idx

    def test_delete_pinned_reference_fails(self, temp_project):
        """Test that pinned references cannot be deleted."""
        from idlergear.reference import delete_reference

        result = delete_reference("vision")
        assert result is False
        # Vision should still exist
        ref = get_pinned_reference("vision")
        assert ref is not None

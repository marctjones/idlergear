"""Tests for note management."""

import pytest
from pathlib import Path

from idlergear.notes import (
    create_note,
    delete_note,
    get_note,
    get_notes_dir,
    list_notes,
    load_note_from_file,
    promote_note,
)
from idlergear.tasks import get_task


class TestGetNotesDir:
    """Tests for get_notes_dir."""

    def test_get_notes_dir(self, temp_project):
        notes_dir = get_notes_dir()
        assert notes_dir is not None
        assert notes_dir == temp_project / ".idlergear" / "notes"

    def test_get_notes_dir_with_path(self, temp_project):
        notes_dir = get_notes_dir(temp_project)
        assert notes_dir == temp_project / ".idlergear" / "notes"


class TestCreateNote:
    """Tests for create_note."""

    def test_create_note(self, temp_project):
        """Test creating a note."""
        note = create_note("This is a quick note")

        assert note["id"] == 1
        assert note["content"] == "This is a quick note"
        assert note["created"] is not None

    def test_create_note_strips_whitespace(self, temp_project):
        """Test that note content is stripped."""
        note = create_note("  Note with whitespace  ")
        assert note["content"] == "Note with whitespace"

    def test_create_multiple_notes(self, temp_project):
        """Test creating multiple notes with incrementing IDs."""
        note1 = create_note("First")
        note2 = create_note("Second")
        note3 = create_note("Third")

        assert note1["id"] == 1
        assert note2["id"] == 2
        assert note3["id"] == 3


class TestListNotes:
    """Tests for list_notes."""

    def test_list_empty(self, temp_project):
        """Test listing notes when empty."""
        notes = list_notes()
        assert notes == []

    def test_list_notes(self, temp_project):
        """Test listing notes."""
        create_note("Note 1")
        create_note("Note 2")

        notes = list_notes()
        assert len(notes) == 2
        assert notes[0]["content"] == "Note 1"
        assert notes[1]["content"] == "Note 2"

    def test_list_notes_sorted(self, temp_project):
        """Test that notes are sorted by ID."""
        create_note("First")
        create_note("Second")
        create_note("Third")

        notes = list_notes()
        ids = [n["id"] for n in notes]
        assert ids == [1, 2, 3]


class TestGetNote:
    """Tests for get_note."""

    def test_get_note(self, temp_project):
        """Test getting a note by ID."""
        created = create_note("My note content")

        note = get_note(created["id"])
        assert note is not None
        assert note["content"] == "My note content"

    def test_get_nonexistent_note(self, temp_project):
        """Test getting a note that doesn't exist."""
        note = get_note(999)
        assert note is None


class TestDeleteNote:
    """Tests for delete_note."""

    def test_delete_note(self, temp_project):
        """Test deleting a note."""
        note = create_note("Note to delete")

        result = delete_note(note["id"])
        assert result is True

        # Verify it's gone
        assert get_note(note["id"]) is None

    def test_delete_nonexistent_note(self, temp_project):
        """Test deleting a note that doesn't exist."""
        result = delete_note(999)
        assert result is False


class TestLoadNoteFromFile:
    """Tests for load_note_from_file."""

    def test_load_nonexistent_file(self, temp_project):
        """Test loading from a nonexistent file."""
        result = load_note_from_file(Path("/nonexistent/file.md"))
        assert result is None

    def test_load_note_file(self, temp_project):
        """Test loading an existing note file."""
        note = create_note("Test content")
        loaded = load_note_from_file(Path(note["path"]))

        assert loaded is not None
        assert loaded["id"] == note["id"]
        assert loaded["content"] == "Test content"


class TestPromoteNote:
    """Tests for promote_note."""

    def test_promote_note_to_task(self, temp_project):
        """Test promoting a note to a task."""
        note = create_note("Add authentication\nThis should be the body")

        result = promote_note(note["id"], "task")

        assert result is not None
        assert result["title"] == "Add authentication"
        assert result["body"] == "This should be the body"

        # Original note should be deleted
        assert get_note(note["id"]) is None

        # Task should exist
        task = get_task(result["id"])
        assert task is not None
        assert task["title"] == "Add authentication"

    def test_promote_note_to_explore(self, temp_project):
        """Test promoting a note to an exploration."""
        from idlergear.explorations import get_exploration

        note = create_note("Research topic\nMore details here")
        result = promote_note(note["id"], "explore")

        assert result is not None
        assert result["title"] == "Research topic"
        assert result["body"] == "More details here"

        # Original note should be deleted
        assert get_note(note["id"]) is None

        # Exploration should exist
        explore = get_exploration(result["id"])
        assert explore is not None

    def test_promote_note_to_reference(self, temp_project):
        """Test promoting a note to a reference."""
        from idlergear.reference import get_reference

        note = create_note("API Documentation\nReference content")
        result = promote_note(note["id"], "reference")

        assert result is not None
        assert result["title"] == "API Documentation"
        assert result["body"] == "Reference content"

        # Original note should be deleted
        assert get_note(note["id"]) is None

    def test_promote_single_line_note(self, temp_project):
        """Test promoting a note with only one line."""
        note = create_note("Just a title")
        result = promote_note(note["id"], "task")

        assert result is not None
        assert result["title"] == "Just a title"
        # Body should be None for single line notes
        assert result.get("body") is None

    def test_promote_nonexistent_note(self, temp_project):
        """Test promoting a note that doesn't exist."""
        result = promote_note(999, "task")
        assert result is None

    def test_promote_invalid_type(self, temp_project):
        """Test promoting to an invalid type."""
        note = create_note("Test note")

        with pytest.raises(ValueError, match="Unknown promotion target"):
            promote_note(note["id"], "invalid_type")

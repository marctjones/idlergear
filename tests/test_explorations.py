"""Tests for exploration management."""

import pytest

from idlergear.explorations import (
    close_exploration,
    create_exploration,
    get_exploration,
    list_explorations,
    load_exploration_from_file,
    update_exploration,
)


class TestCreateExploration:
    """Tests for create_exploration."""

    def test_create_exploration(self, temp_project):
        exp = create_exploration("Should we support Windows?")

        assert exp["id"] == 1
        assert exp["title"] == "Should we support Windows?"
        assert exp["state"] == "open"
        assert exp["created"] is not None
        assert "path" in exp

    def test_create_exploration_with_body(self, temp_project):
        exp = create_exploration(
            "Windows Support",
            body="Exploring whether to add Windows support.",
        )

        assert exp["title"] == "Windows Support"
        assert exp["body"] == "Exploring whether to add Windows support."

    def test_create_multiple_explorations(self, temp_project):
        exp1 = create_exploration("First exploration")
        exp2 = create_exploration("Second exploration")

        assert exp1["id"] == 1
        assert exp2["id"] == 2


class TestListExplorations:
    """Tests for list_explorations."""

    def test_list_empty(self, temp_project):
        exps = list_explorations()
        assert exps == []

    def test_list_open_explorations(self, temp_project):
        create_exploration("Open one")
        create_exploration("Open two")

        exps = list_explorations(state="open")
        assert len(exps) == 2

    def test_list_closed_explorations(self, temp_project):
        exp = create_exploration("To close")
        close_exploration(exp["id"])

        open_exps = list_explorations(state="open")
        closed_exps = list_explorations(state="closed")

        assert len(open_exps) == 0
        assert len(closed_exps) == 1
        assert closed_exps[0]["title"] == "To close"

    def test_list_all_explorations(self, temp_project):
        create_exploration("Open")
        exp2 = create_exploration("Closed")
        close_exploration(exp2["id"])

        all_exps = list_explorations(state="all")
        assert len(all_exps) == 2

    def test_list_sorted_by_id(self, temp_project):
        create_exploration("First")
        create_exploration("Second")
        create_exploration("Third")

        exps = list_explorations()
        assert exps[0]["id"] < exps[1]["id"] < exps[2]["id"]


class TestGetExploration:
    """Tests for get_exploration."""

    def test_get_existing_exploration(self, temp_project):
        created = create_exploration("Test", body="Test body")

        exp = get_exploration(created["id"])
        assert exp is not None
        assert exp["title"] == "Test"
        assert exp["body"] == "Test body"

    def test_get_nonexistent_exploration(self, temp_project):
        exp = get_exploration(999)
        assert exp is None


class TestUpdateExploration:
    """Tests for update_exploration."""

    def test_update_title(self, temp_project):
        exp = create_exploration("Original")

        updated = update_exploration(exp["id"], title="Updated")
        assert updated["title"] == "Updated"

    def test_update_body(self, temp_project):
        exp = create_exploration("Test", body="Original body")

        updated = update_exploration(exp["id"], body="Updated body")
        assert updated["body"] == "Updated body"

    def test_update_state(self, temp_project):
        exp = create_exploration("Test")

        updated = update_exploration(exp["id"], state="closed")
        assert updated["state"] == "closed"

    def test_update_nonexistent(self, temp_project):
        result = update_exploration(999, title="New")
        assert result is None


class TestCloseExploration:
    """Tests for close_exploration."""

    def test_close_exploration(self, temp_project):
        exp = create_exploration("Test")

        closed = close_exploration(exp["id"])
        assert closed["state"] == "closed"

    def test_close_nonexistent(self, temp_project):
        result = close_exploration(999)
        assert result is None


class TestLoadExplorationFromFile:
    """Tests for load_exploration_from_file."""

    def test_load_nonexistent_file(self, temp_project):
        from pathlib import Path

        result = load_exploration_from_file(Path("/nonexistent/file.md"))
        assert result is None

    def test_load_exploration_file(self, temp_project):
        from pathlib import Path

        exp = create_exploration("Test", body="Body content")

        loaded = load_exploration_from_file(Path(exp["path"]))
        assert loaded is not None
        assert loaded["title"] == "Test"
        assert loaded["body"] == "Body content"

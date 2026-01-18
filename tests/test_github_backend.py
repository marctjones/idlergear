"""Tests for GitHub backend.

These tests mock the gh CLI to test the backend logic without
requiring actual GitHub access.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from idlergear.backends.github import (
    GitHubBackendError,
    GitHubDiscussionsNoteBackend,
    GitHubExploreBackend,
    GitHubTaskBackend,
    _map_issue_to_task,
    _run_gh_command,
)


class TestRunGhCommand:
    """Tests for _run_gh_command function."""

    def test_successful_command(self) -> None:
        """Test running a successful gh command."""
        with patch("idlergear.backends.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"number": 1}',
                stderr="",
            )

            result = _run_gh_command(["issue", "list"])
            assert result == '{"number": 1}'
            mock_run.assert_called_once()

    def test_command_not_found(self) -> None:
        """Test error when gh is not installed."""
        with patch("idlergear.backends.github.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            with pytest.raises(GitHubBackendError) as exc_info:
                _run_gh_command(["issue", "list"])

            assert "not found" in str(exc_info.value)

    def test_not_authenticated(self) -> None:
        """Test error when gh is not authenticated."""
        with patch("idlergear.backends.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="not authenticated",
            )

            with pytest.raises(GitHubBackendError) as exc_info:
                _run_gh_command(["issue", "list"])

            assert "not authenticated" in str(exc_info.value).lower()

    def test_not_git_repository(self) -> None:
        """Test error when not in a git repository."""
        with patch("idlergear.backends.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="not a git repository",
            )

            with pytest.raises(GitHubBackendError) as exc_info:
                _run_gh_command(["issue", "list"])

            assert "git repository" in str(exc_info.value).lower()

    def test_command_timeout(self) -> None:
        """Test command timeout."""
        import subprocess

        with patch("idlergear.backends.github.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("gh", 30)

            with pytest.raises(GitHubBackendError) as exc_info:
                _run_gh_command(["issue", "list"])

            assert "timed out" in str(exc_info.value)


class TestMapIssueToTask:
    """Tests for _map_issue_to_task function."""

    def test_basic_mapping(self) -> None:
        """Test basic field mapping."""
        issue = {
            "number": 42,
            "title": "Test Issue",
            "body": "Description",
            "state": "OPEN",
            "labels": [],
            "assignees": [],
        }

        result = _map_issue_to_task(issue)

        assert result["id"] == 42
        assert result["title"] == "Test Issue"
        assert result["body"] == "Description"
        assert result["state"] == "open"
        assert result["labels"] == []
        assert result["assignees"] == []
        assert result["priority"] is None

    def test_labels_as_objects(self) -> None:
        """Test labels when they come as objects."""
        issue = {
            "number": 1,
            "title": "Test",
            "body": "",
            "state": "open",
            "labels": [{"name": "bug"}, {"name": "help wanted"}],
            "assignees": [],
        }

        result = _map_issue_to_task(issue)
        assert result["labels"] == ["bug", "help wanted"]

    def test_labels_as_strings(self) -> None:
        """Test labels when they come as strings."""
        issue = {
            "number": 1,
            "title": "Test",
            "body": "",
            "state": "open",
            "labels": ["bug", "feature"],
            "assignees": [],
        }

        result = _map_issue_to_task(issue)
        assert result["labels"] == ["bug", "feature"]

    def test_priority_extraction(self) -> None:
        """Test priority extraction from labels."""
        issue = {
            "number": 1,
            "title": "Test",
            "body": "",
            "state": "open",
            "labels": [{"name": "bug"}, {"name": "priority:high"}],
            "assignees": [],
        }

        result = _map_issue_to_task(issue)
        assert result["priority"] == "high"
        # Priority label should not be in regular labels
        assert "priority:high" not in result["labels"]
        assert result["labels"] == ["bug"]

    def test_assignees_as_objects(self) -> None:
        """Test assignees when they come as objects."""
        issue = {
            "number": 1,
            "title": "Test",
            "body": "",
            "state": "open",
            "labels": [],
            "assignees": [{"login": "user1"}, {"login": "user2"}],
        }

        result = _map_issue_to_task(issue)
        assert result["assignees"] == ["user1", "user2"]


class TestGitHubTaskBackend:
    """Tests for GitHubTaskBackend."""

    def test_create_task(self) -> None:
        """Test creating a task."""
        backend = GitHubTaskBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            # First call returns the URL from gh issue create
            # Second call returns JSON from gh issue view
            mock_run.side_effect = [
                "https://github.com/owner/repo/issues/1",
                json.dumps(
                    {
                        "number": 1,
                        "title": "Test Task",
                        "body": "Description",
                        "state": "OPEN",
                        "labels": [],
                        "assignees": [],
                    }
                ),
            ]

            result = backend.create("Test Task", body="Description")

            assert result["id"] == 1
            assert result["title"] == "Test Task"
            assert mock_run.call_count == 2
            # First call was the create
            args = mock_run.call_args_list[0][0][0]
            assert "issue" in args
            assert "create" in args
            assert "Test Task" in args

    def test_create_task_with_labels(self) -> None:
        """Test creating a task with labels."""
        backend = GitHubTaskBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.side_effect = [
                "https://github.com/owner/repo/issues/1",
                json.dumps(
                    {
                        "number": 1,
                        "title": "Test",
                        "body": "",
                        "state": "OPEN",
                        "labels": [{"name": "bug"}],
                        "assignees": [],
                    }
                ),
            ]

            backend.create("Test", labels=["bug"])

            # First call was the create
            args = mock_run.call_args_list[0][0][0]
            assert "--label" in args
            assert "bug" in args

    def test_create_task_with_priority(self) -> None:
        """Test creating a task with priority."""
        backend = GitHubTaskBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.side_effect = [
                "https://github.com/owner/repo/issues/1",
                json.dumps(
                    {
                        "number": 1,
                        "title": "Test",
                        "body": "",
                        "state": "OPEN",
                        "labels": [{"name": "priority:high"}],
                        "assignees": [],
                    }
                ),
            ]

            backend.create("Test", priority="high")

            # First call was the create
            args = mock_run.call_args_list[0][0][0]
            assert "--label" in args
            assert "priority:high" in args

    def test_list_tasks(self) -> None:
        """Test listing tasks."""
        backend = GitHubTaskBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.return_value = json.dumps(
                [
                    {
                        "number": 1,
                        "title": "Task 1",
                        "body": "",
                        "state": "OPEN",
                        "labels": [],
                        "assignees": [],
                    },
                    {
                        "number": 2,
                        "title": "Task 2",
                        "body": "",
                        "state": "OPEN",
                        "labels": [],
                        "assignees": [],
                    },
                ]
            )

            result = backend.list()

            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[1]["id"] == 2

    def test_list_tasks_closed(self) -> None:
        """Test listing closed tasks."""
        backend = GitHubTaskBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.return_value = "[]"

            backend.list(state="closed")

            args = mock_run.call_args[0][0]
            assert "--state" in args
            state_idx = args.index("--state")
            assert args[state_idx + 1] == "closed"

    def test_get_task(self) -> None:
        """Test getting a task."""
        backend = GitHubTaskBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.return_value = json.dumps(
                {
                    "number": 42,
                    "title": "Test",
                    "body": "Body",
                    "state": "OPEN",
                    "labels": [],
                    "assignees": [],
                }
            )

            result = backend.get(42)

            assert result["id"] == 42
            args = mock_run.call_args[0][0]
            assert "42" in args

    def test_get_task_not_found(self) -> None:
        """Test getting a non-existent task."""
        backend = GitHubTaskBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.side_effect = GitHubBackendError("not found")

            result = backend.get(999)
            assert result is None

    def test_close_task(self) -> None:
        """Test closing a task."""
        backend = GitHubTaskBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.return_value = json.dumps(
                {
                    "number": 1,
                    "title": "Test",
                    "body": "",
                    "state": "CLOSED",
                    "labels": [],
                    "assignees": [],
                }
            )

            result = backend.close(1)

            assert result["state"] == "closed"
            # First call should be close, second should be get
            calls = mock_run.call_args_list
            assert "close" in calls[0][0][0]

    def test_reopen_task(self) -> None:
        """Test reopening a task."""
        backend = GitHubTaskBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.return_value = json.dumps(
                {
                    "number": 1,
                    "title": "Test",
                    "body": "",
                    "state": "OPEN",
                    "labels": [],
                    "assignees": [],
                }
            )

            result = backend.reopen(1)

            assert result["state"] == "open"
            calls = mock_run.call_args_list
            assert "reopen" in calls[0][0][0]


class TestGitHubExploreBackend:
    """Tests for GitHubExploreBackend."""

    def test_create_exploration(self) -> None:
        """Test creating an exploration."""
        backend = GitHubExploreBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            # Call sequence: label list, label create (optional), issue create, issue view
            mock_run.side_effect = [
                json.dumps([]),  # label list (empty, so label will be created)
                "",  # label create succeeds (or fails silently)
                "https://github.com/owner/repo/issues/1",  # issue create
                json.dumps(
                    {
                        "number": 1,
                        "title": "Exploration",
                        "body": "",
                        "state": "OPEN",
                        "labels": [{"name": "exploration"}],
                    }
                ),  # issue view
            ]

            result = backend.create("Exploration")

            assert result["id"] == 1
            # Check that exploration label is added (third call was the create)
            args = mock_run.call_args_list[2][0][0]
            assert "--label" in args
            assert "exploration" in args

    def test_list_explorations(self) -> None:
        """Test listing explorations."""
        backend = GitHubExploreBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.return_value = json.dumps(
                [
                    {
                        "number": 1,
                        "title": "Explore 1",
                        "body": "",
                        "state": "OPEN",
                        "labels": [],
                    },
                ]
            )

            result = backend.list()

            # Check that exploration label filter is used
            args = mock_run.call_args[0][0]
            assert "--label" in args
            label_idx = args.index("--label")
            assert args[label_idx + 1] == "exploration"


class TestGitHubDiscussionsNoteBackend:
    """Tests for GitHubDiscussionsNoteBackend."""

    def test_discussions_not_enabled(self) -> None:
        """Test error when discussions not enabled."""
        backend = GitHubDiscussionsNoteBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.return_value = "false"

            with pytest.raises(GitHubBackendError) as exc_info:
                backend.create("Test note")

            assert "Discussions not enabled" in str(exc_info.value)

    def test_list_when_discussions_disabled(self) -> None:
        """Test list returns empty when discussions disabled."""
        backend = GitHubDiscussionsNoteBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.return_value = "false"

            result = backend.list()
            assert result == []

    def test_get_when_discussions_disabled(self) -> None:
        """Test get returns None when discussions disabled."""
        backend = GitHubDiscussionsNoteBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.return_value = "false"

            result = backend.get(1)
            assert result is None

    def test_create_note(self) -> None:
        """Test creating a note as a discussion."""
        backend = GitHubDiscussionsNoteBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.side_effect = [
                "true",  # discussions enabled check
                "R_repo123",  # get repo ID
                json.dumps([{"id": "DIC_cat123", "name": "Ideas"}]),  # get categories
                json.dumps(
                    {
                        "data": {
                            "createDiscussion": {
                                "discussion": {
                                    "id": "D_disc123",
                                    "number": 1,
                                    "title": "Test note",
                                    "body": "",
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "updatedAt": "2024-01-01T00:00:00Z",
                                    "url": "https://github.com/owner/repo/discussions/1",
                                }
                            }
                        }
                    }
                ),
            ]

            result = backend.create("Test note")

            assert result["id"] == 1
            assert "Test note" in result["content"]

    def test_create_note_with_tags(self) -> None:
        """Test creating a note with tags."""
        backend = GitHubDiscussionsNoteBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            # Call sequence: discussions check, label list, label create, repo ID, categories, create discussion
            mock_run.side_effect = [
                "true",  # discussions enabled check
                json.dumps([]),  # label list (empty, so tag label will be created)
                "",  # label create for tag:explore
                "R_repo123",  # get repo ID
                json.dumps([{"id": "DIC_cat123", "name": "Ideas"}]),  # get categories
                json.dumps(
                    {
                        "data": {
                            "createDiscussion": {
                                "discussion": {
                                    "id": "D_disc123",
                                    "number": 1,
                                    "title": "Research idea",
                                    "body": "Some details\n\n---\n_Tags: explore_",
                                    "createdAt": "2024-01-01T00:00:00Z",
                                    "updatedAt": "2024-01-01T00:00:00Z",
                                    "url": "https://github.com/owner/repo/discussions/1",
                                }
                            }
                        }
                    }
                ),
            ]

            result = backend.create("Research idea\nSome details", tags=["explore"])

            assert result["id"] == 1
            assert "explore" in result["tags"]

    def test_list_notes(self) -> None:
        """Test listing notes from discussions."""
        backend = GitHubDiscussionsNoteBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.side_effect = [
                "true",  # discussions enabled check
                json.dumps([{"id": "DIC_cat123", "name": "Ideas"}]),  # get categories
                json.dumps(
                    [
                        {
                            "id": "D_disc1",
                            "number": 1,
                            "title": "Note 1",
                            "body": "",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "updatedAt": "2024-01-01T00:00:00Z",
                            "url": "https://github.com/owner/repo/discussions/1",
                        },
                        {
                            "id": "D_disc2",
                            "number": 2,
                            "title": "Note 2",
                            "body": "",
                            "createdAt": "2024-01-02T00:00:00Z",
                            "updatedAt": "2024-01-02T00:00:00Z",
                            "url": "https://github.com/owner/repo/discussions/2",
                        },
                    ]
                ),
            ]

            result = backend.list()

            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[1]["id"] == 2

    def test_list_notes_filtered_by_tag(self) -> None:
        """Test filtering notes by tag."""
        backend = GitHubDiscussionsNoteBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.side_effect = [
                "true",  # discussions enabled check
                json.dumps([{"id": "DIC_cat123", "name": "Ideas"}]),  # get categories
                json.dumps(
                    [
                        {
                            "id": "D_disc1",
                            "number": 1,
                            "title": "Tagged note",
                            "body": "Content\n\n---\n_Tags: explore_",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "updatedAt": "2024-01-01T00:00:00Z",
                            "url": "https://github.com/owner/repo/discussions/1",
                        },
                        {
                            "id": "D_disc2",
                            "number": 2,
                            "title": "Untagged note",
                            "body": "",
                            "createdAt": "2024-01-02T00:00:00Z",
                            "updatedAt": "2024-01-02T00:00:00Z",
                            "url": "https://github.com/owner/repo/discussions/2",
                        },
                    ]
                ),
            ]

            result = backend.list(tag="explore")

            assert len(result) == 1
            assert result[0]["id"] == 1

    def test_get_note(self) -> None:
        """Test getting a note by ID."""
        backend = GitHubDiscussionsNoteBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.side_effect = [
                "true",  # discussions enabled check
                json.dumps(
                    {
                        "id": "D_disc123",
                        "number": 42,
                        "title": "Test note",
                        "body": "Body content",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-01T00:00:00Z",
                        "url": "https://github.com/owner/repo/discussions/42",
                        "closed": False,
                    }
                ),
            ]

            result = backend.get(42)

            assert result["id"] == 42
            assert "Test note" in result["content"]
            assert result["closed"] is False

    def test_delete_note_closes_discussion(self) -> None:
        """Test that delete closes the discussion."""
        backend = GitHubDiscussionsNoteBackend()

        with patch("idlergear.backends.github._run_gh_command") as mock_run:
            mock_run.side_effect = [
                "true",  # discussions enabled check
                json.dumps(
                    {
                        "id": "D_disc123",
                        "number": 1,
                        "title": "Test",
                        "body": "",
                        "createdAt": "",
                        "updatedAt": "",
                        "url": "",
                        "closed": False,
                    }
                ),
                json.dumps(
                    {
                        "data": {
                            "closeDiscussion": {
                                "discussion": {"id": "D_disc123", "closed": True}
                            }
                        }
                    }
                ),
            ]

            result = backend.delete(1)

            assert result is True
            # Verify close mutation was called
            last_call_args = mock_run.call_args_list[-1][0][0]
            assert "closeDiscussion" in str(last_call_args)

    def test_map_to_note_extracts_tags(self) -> None:
        """Test tag extraction from body."""
        backend = GitHubDiscussionsNoteBackend()

        discussion = {
            "number": 1,
            "id": "D_abc",
            "title": "Note with tags",
            "body": "Content here\n\n---\n_Tags: explore, idea_",
            "createdAt": "",
            "updatedAt": "",
            "url": "",
        }

        result = backend._map_to_note(discussion)

        assert result["tags"] == ["explore", "idea"]
        # Tags line should be removed from content
        assert "---" not in result["content"]
        assert "_Tags:" not in result["content"]

    def test_map_to_note_without_tags(self) -> None:
        """Test mapping when no tags present."""
        backend = GitHubDiscussionsNoteBackend()

        discussion = {
            "number": 1,
            "id": "D_abc",
            "title": "Simple note",
            "body": "Just content",
            "createdAt": "",
            "updatedAt": "",
            "url": "",
        }

        result = backend._map_to_note(discussion)

        assert result["tags"] == []
        assert "Simple note" in result["content"]
        assert "Just content" in result["content"]

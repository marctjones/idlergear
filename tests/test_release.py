"""Tests for release management."""

import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from idlergear.release import (
    Release,
    check_gh_installed,
    check_gh_auth,
    list_releases,
    get_release,
    create_release,
    delete_release,
    generate_notes_from_tasks,
    run_version_command,
)


class TestRelease:
    """Tests for Release dataclass."""

    def test_create_release(self):
        """Create a Release object."""
        now = datetime.now()
        release = Release(
            tag="v1.0.0",
            name="Version 1.0.0",
            published_at=now,
            is_draft=False,
            is_prerelease=False,
            body="Release notes here",
            url="https://github.com/user/repo/releases/v1.0.0",
        )
        assert release.tag == "v1.0.0"
        assert release.name == "Version 1.0.0"
        assert release.published_at == now

    def test_to_dict(self):
        """Release converts to dict."""
        release = Release(
            tag="v1.0.0",
            name="v1.0.0",
            published_at=datetime(2024, 1, 15, 10, 30),
            is_draft=True,
            is_prerelease=False,
            body="Notes",
            url="https://example.com",
        )
        data = release.to_dict()
        assert data["tag"] == "v1.0.0"
        assert data["is_draft"] is True
        assert "2024-01-15" in data["published_at"]


class TestGhCli:
    """Tests for GitHub CLI checks."""

    @patch("subprocess.run")
    def test_check_gh_installed_success(self, mock_run):
        """Detect gh when installed."""
        mock_run.return_value = MagicMock(returncode=0)
        assert check_gh_installed() is True

    @patch("subprocess.run")
    def test_check_gh_installed_failure(self, mock_run):
        """Detect missing gh."""
        mock_run.side_effect = FileNotFoundError()
        assert check_gh_installed() is False

    @patch("subprocess.run")
    def test_check_gh_auth_success(self, mock_run):
        """Detect authenticated gh."""
        mock_run.return_value = MagicMock(returncode=0)
        assert check_gh_auth() is True

    @patch("subprocess.run")
    def test_check_gh_auth_failure(self, mock_run):
        """Detect unauthenticated gh."""
        mock_run.return_value = MagicMock(returncode=1)
        assert check_gh_auth() is False


class TestListReleases:
    """Tests for listing releases."""

    @patch("subprocess.run")
    def test_list_releases(self, mock_run):
        """List releases parses JSON output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "tagName": "v1.0.0",
                        "name": "Version 1.0.0",
                        "publishedAt": "2024-01-15T10:30:00Z",
                        "isDraft": False,
                        "isPrerelease": False,
                    },
                    {
                        "tagName": "v0.9.0",
                        "name": None,
                        "publishedAt": None,
                        "isDraft": True,
                        "isPrerelease": False,
                    },
                ]
            ),
        )

        releases = list_releases(limit=10)
        assert len(releases) == 2
        assert releases[0].tag == "v1.0.0"
        assert releases[0].name == "Version 1.0.0"
        assert releases[1].tag == "v0.9.0"
        assert releases[1].is_draft is True

    @patch("subprocess.run")
    def test_list_releases_error(self, mock_run):
        """List releases handles errors."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Not found",
        )

        with pytest.raises(RuntimeError, match="Failed to list releases"):
            list_releases()


class TestGetRelease:
    """Tests for getting a specific release."""

    @patch("subprocess.run")
    def test_get_release_found(self, mock_run):
        """Get release returns Release object."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
                    "tagName": "v1.0.0",
                    "name": "Version 1.0.0",
                    "publishedAt": "2024-01-15T10:30:00Z",
                    "isDraft": False,
                    "isPrerelease": False,
                    "body": "Notes",
                    "url": "https://example.com",
                }
            ),
        )

        release = get_release("v1.0.0")
        assert release is not None
        assert release.tag == "v1.0.0"

    @patch("subprocess.run")
    def test_get_release_not_found(self, mock_run):
        """Get release returns None when not found."""
        mock_run.return_value = MagicMock(returncode=1)

        release = get_release("v999.0.0")
        assert release is None


class TestCreateRelease:
    """Tests for creating releases."""

    @patch("subprocess.run")
    def test_create_release_simple(self, mock_run):
        """Create release with minimal args."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://github.com/user/repo/releases/v1.0.0\n",
        )

        success, message, url = create_release("v1.0.0")

        assert success is True
        assert "v1.0.0" in message
        assert url is not None

    @patch("subprocess.run")
    def test_create_release_with_options(self, mock_run):
        """Create release with all options."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="https://example.com\n",
        )

        success, message, url = create_release(
            tag="v1.0.0",
            title="Release 1.0.0",
            notes="What's new",
            draft=True,
            prerelease=True,
            target="main",
        )

        assert success is True
        # Verify correct args were passed
        call_args = mock_run.call_args[0][0]
        assert "v1.0.0" in call_args
        assert "--draft" in call_args
        assert "--prerelease" in call_args

    @patch("subprocess.run")
    def test_create_release_failure(self, mock_run):
        """Create release handles failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Tag already exists",
        )

        success, message, url = create_release("v1.0.0")

        assert success is False
        assert "Failed" in message
        assert url is None


class TestDeleteRelease:
    """Tests for deleting releases."""

    @patch("subprocess.run")
    def test_delete_release_success(self, mock_run):
        """Delete release succeeds."""
        mock_run.return_value = MagicMock(returncode=0)

        success, message = delete_release("v1.0.0", yes=True)

        assert success is True
        assert "v1.0.0" in message

    @patch("subprocess.run")
    def test_delete_release_failure(self, mock_run):
        """Delete release handles failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Not found",
        )

        success, message = delete_release("v999.0.0", yes=True)

        assert success is False
        assert "Failed" in message


class TestGenerateNotes:
    """Tests for generating release notes from tasks."""

    @patch("idlergear.tasks.list_tasks")
    @patch("idlergear.config.find_idlergear_root")
    def test_no_project(self, mock_root, mock_list_tasks):
        """Generate notes without project returns message."""
        mock_root.return_value = None

        notes = generate_notes_from_tasks()
        assert "No IdlerGear project" in notes
        mock_list_tasks.assert_not_called()


class TestVersionCommand:
    """Tests for version bump command."""

    @patch("idlergear.config.find_idlergear_root")
    def test_no_project(self, mock_root):
        """Version command fails without project."""
        mock_root.return_value = None

        success, message = run_version_command()

        assert success is False
        assert "Not in an IdlerGear project" in message

    @patch("idlergear.config.get_config_value")
    @patch("idlergear.config.find_idlergear_root")
    def test_no_command_configured(self, mock_root, mock_config):
        """Version command fails without config."""
        mock_root.return_value = "/path/to/project"
        mock_config.return_value = None

        success, message = run_version_command()

        assert success is False
        assert "No version_command configured" in message

    @patch("subprocess.run")
    @patch("idlergear.config.get_config_value")
    @patch("idlergear.config.find_idlergear_root")
    def test_version_command_success(self, mock_root, mock_config, mock_run):
        """Version command runs successfully."""
        mock_root.return_value = "/path/to/project"
        mock_config.return_value = "bumpversion patch"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Bumped version 0.1.0 -> 0.1.1",
        )

        success, message = run_version_command()

        assert success is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    @patch("idlergear.config.get_config_value")
    @patch("idlergear.config.find_idlergear_root")
    def test_version_command_failure(self, mock_root, mock_config, mock_run):
        """Version command handles failure."""
        mock_root.return_value = "/path/to/project"
        mock_config.return_value = "bumpversion patch"
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: Version file not found",
        )

        success, message = run_version_command()

        assert success is False
        assert "failed" in message.lower()

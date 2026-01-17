"""Tests for github_detect module - GitHub feature detection."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from idlergear.github_detect import (
    GitHubFeatures,
    detect_github_features,
    format_features_summary,
    get_github_owner,
    get_recommended_backends,
)


class TestGitHubFeatures:
    """Tests for GitHubFeatures dataclass."""

    def test_default_values(self):
        """Test default values."""
        features = GitHubFeatures()
        assert features.is_github_repo is False
        assert features.has_issues is False
        assert features.has_discussions is False
        assert features.has_wiki is False
        assert features.has_projects is False
        assert features.repo_name is None
        assert features.repo_url is None
        assert features.error is None

    def test_with_all_features(self):
        """Test with all features enabled."""
        features = GitHubFeatures(
            is_github_repo=True,
            has_issues=True,
            has_discussions=True,
            has_wiki=True,
            has_projects=True,
            repo_name="my-repo",
            repo_url="https://github.com/owner/my-repo",
        )
        assert features.is_github_repo is True
        assert features.has_issues is True
        assert features.repo_name == "my-repo"


class TestDetectGitHubFeatures:
    """Tests for detect_github_features function."""

    def test_gh_not_installed(self):
        """Test when gh CLI is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("gh not found")
            features = detect_github_features()
            assert features.error == "GitHub CLI (gh) not installed"
            assert features.is_github_repo is False

    def test_gh_timeout(self):
        """Test when gh CLI times out."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("gh", 5)
            features = detect_github_features()
            assert features.error == "GitHub CLI timed out"
            assert features.is_github_repo is False

    def test_not_a_git_repo(self):
        """Test when not in a git repository."""
        with patch("subprocess.run") as mock_run:
            # First call: gh --version succeeds
            # Second call: gh repo view fails
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=1, stderr="not a git repository"),  # gh repo view
            ]
            features = detect_github_features()
            assert features.error == "Not a git repository"
            assert features.is_github_repo is False

    def test_no_github_remote(self):
        """Test when no GitHub remote is found."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=1, stderr="could not determine base repository"),
            ]
            features = detect_github_features()
            assert features.error == "No GitHub remote found"
            assert features.is_github_repo is False

    def test_no_github_explicit(self):
        """Test when 'no github' is in error message."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=1, stderr="no github.com remote"),
            ]
            features = detect_github_features()
            assert features.error == "No GitHub remote found"

    def test_not_authenticated(self):
        """Test when not authenticated with GitHub."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=1, stderr="not logged in to any GitHub hosts"),
            ]
            features = detect_github_features()
            assert "Not authenticated" in features.error
            assert features.is_github_repo is False

    def test_authentication_error(self):
        """Test authentication error."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=1, stderr="authentication required"),
            ]
            features = detect_github_features()
            assert "Not authenticated" in features.error

    def test_unknown_error(self):
        """Test unknown error."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=1, stderr="some random error"),
            ]
            features = detect_github_features()
            assert features.error == "some random error"

    def test_unknown_error_empty_stderr(self):
        """Test unknown error with empty stderr."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=1, stderr=""),
            ]
            features = detect_github_features()
            assert features.error == "Unknown error"

    def test_success_all_features(self):
        """Test successful detection with all features."""
        repo_data = {
            "name": "my-project",
            "url": "https://github.com/owner/my-project",
            "hasIssuesEnabled": True,
            "hasWikiEnabled": True,
            "hasDiscussionsEnabled": True,
            "hasProjectsEnabled": True,
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=0, stdout=json.dumps(repo_data)),  # gh repo view
            ]
            features = detect_github_features()
            assert features.is_github_repo is True
            assert features.repo_name == "my-project"
            assert features.repo_url == "https://github.com/owner/my-project"
            assert features.has_issues is True
            assert features.has_wiki is True
            assert features.has_discussions is True
            assert features.has_projects is True
            assert features.error is None

    def test_success_some_features(self):
        """Test successful detection with some features disabled."""
        repo_data = {
            "name": "minimal-repo",
            "url": "https://github.com/owner/minimal-repo",
            "hasIssuesEnabled": True,
            "hasWikiEnabled": False,
            "hasDiscussionsEnabled": False,
            "hasProjectsEnabled": False,
        }
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=0, stdout=json.dumps(repo_data)),  # gh repo view
            ]
            features = detect_github_features()
            assert features.is_github_repo is True
            assert features.has_issues is True
            assert features.has_wiki is False
            assert features.has_discussions is False
            assert features.has_projects is False

    def test_success_missing_fields(self):
        """Test successful detection with missing optional fields."""
        repo_data = {"name": "repo"}
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=0, stdout=json.dumps(repo_data)),  # gh repo view
            ]
            features = detect_github_features()
            assert features.is_github_repo is True
            assert features.repo_name == "repo"
            assert features.has_issues is False  # Default when not present

    def test_api_timeout(self):
        """Test timeout during API call."""
        with patch("subprocess.run") as mock_run:
            # First call succeeds, second times out
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                subprocess.TimeoutExpired("gh", 10),  # gh repo view timeout
            ]
            features = detect_github_features()
            assert features.error == "GitHub API timed out"

    def test_invalid_json_response(self):
        """Test invalid JSON response."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=0, stdout="not valid json"),  # gh repo view
            ]
            features = detect_github_features()
            assert features.error == "Invalid response from GitHub"

    def test_generic_exception(self):
        """Test handling generic exception."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                RuntimeError("Unexpected error"),  # gh repo view
            ]
            features = detect_github_features()
            assert "Unexpected error" in features.error

    def test_with_project_path(self, tmp_path):
        """Test detection with custom project path."""
        repo_data = {"name": "test-repo"}
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # gh --version
                MagicMock(returncode=0, stdout=json.dumps(repo_data)),  # gh repo view
            ]
            features = detect_github_features(project_path=tmp_path)
            # Check that cwd was passed
            call_args = mock_run.call_args_list[1]
            assert call_args.kwargs.get("cwd") == tmp_path


class TestGetRecommendedBackends:
    """Tests for get_recommended_backends function."""

    def test_not_github_repo(self):
        """Test recommendations for non-GitHub repo."""
        features = GitHubFeatures(is_github_repo=False)
        recommendations = get_recommended_backends(features)
        assert recommendations == {}

    def test_github_with_issues(self):
        """Test recommendations when issues are enabled."""
        features = GitHubFeatures(is_github_repo=True, has_issues=True)
        recommendations = get_recommended_backends(features)
        assert recommendations["task"] == "github"
        assert recommendations["explore"] == "github"

    def test_github_without_issues(self):
        """Test recommendations when issues are disabled."""
        features = GitHubFeatures(is_github_repo=True, has_issues=False)
        recommendations = get_recommended_backends(features)
        assert "task" not in recommendations

    def test_github_with_error(self):
        """Test recommendations when there's an error."""
        features = GitHubFeatures(is_github_repo=False, error="Some error")
        recommendations = get_recommended_backends(features)
        assert recommendations == {}


class TestGetGitHubOwner:
    """Tests for get_github_owner function."""

    def test_owner_success(self):
        """Test successful owner retrieval."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="myorg\n")
            owner = get_github_owner()
            assert owner == "myorg"

    def test_owner_empty(self):
        """Test empty owner result."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            owner = get_github_owner()
            assert owner is None

    def test_owner_command_failed(self):
        """Test when command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            owner = get_github_owner()
            assert owner is None

    def test_owner_exception(self):
        """Test handling exception."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("error")
            owner = get_github_owner()
            assert owner is None

    def test_owner_with_project_path(self, tmp_path):
        """Test owner retrieval with custom path."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="user\n")
            owner = get_github_owner(project_path=tmp_path)
            assert owner == "user"
            # Check cwd was passed
            assert mock_run.call_args.kwargs.get("cwd") == tmp_path


class TestFormatFeaturesSummary:
    """Tests for format_features_summary function."""

    def test_with_error(self):
        """Test formatting when there's an error."""
        features = GitHubFeatures(error="Not authenticated")
        result = format_features_summary(features)
        assert "GitHub detection: Not authenticated" in result

    def test_not_github_repo(self):
        """Test formatting for non-GitHub repo."""
        features = GitHubFeatures(is_github_repo=False)
        result = format_features_summary(features)
        assert result == "Not a GitHub repository"

    def test_github_with_all_features(self):
        """Test formatting with all features enabled."""
        features = GitHubFeatures(
            is_github_repo=True,
            repo_name="my-project",
            has_issues=True,
            has_discussions=True,
            has_wiki=True,
            has_projects=True,
        )
        result = format_features_summary(features)
        assert "GitHub repository: my-project" in result
        assert "Issues" in result
        assert "Discussions" in result
        assert "Wiki" in result
        assert "Projects" in result

    def test_github_with_some_features(self):
        """Test formatting with some features enabled."""
        features = GitHubFeatures(
            is_github_repo=True,
            repo_name="minimal-repo",
            has_issues=True,
            has_discussions=False,
            has_wiki=False,
            has_projects=False,
        )
        result = format_features_summary(features)
        assert "GitHub repository: minimal-repo" in result
        assert "Issues" in result
        assert "Discussions" not in result
        assert "Wiki" not in result
        assert "Projects" not in result

    def test_github_no_features(self):
        """Test formatting with no features enabled."""
        features = GitHubFeatures(
            is_github_repo=True,
            repo_name="empty-repo",
            has_issues=False,
            has_discussions=False,
            has_wiki=False,
            has_projects=False,
        )
        result = format_features_summary(features)
        assert "GitHub repository: empty-repo" in result
        assert "No GitHub features enabled" in result

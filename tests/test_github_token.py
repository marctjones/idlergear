import pytest
import os
from unittest.mock import patch, MagicMock
from src.main import get_github_token


class TestGitHubToken:
    """Tests for GitHub token retrieval functionality."""

    def test_get_token_from_env_file(self, monkeypatch):
        """Test that token is retrieved from .env file first."""
        monkeypatch.setenv("GITHUB_TOKEN", "test_token_from_env")
        token = get_github_token()
        assert token == "test_token_from_env"

    @patch("subprocess.run")
    def test_get_token_from_gh_cli(self, mock_run, monkeypatch):
        """Test that token falls back to gh CLI when .env not available."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        
        mock_result = MagicMock()
        mock_result.stdout = "test_token_from_gh\n"
        mock_run.return_value = mock_result
        
        token = get_github_token()
        assert token == "test_token_from_gh"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_get_token_returns_none_when_unavailable(self, mock_run, monkeypatch):
        """Test that None is returned when no token source is available."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mock_run.side_effect = FileNotFoundError()
        
        token = get_github_token()
        assert token is None

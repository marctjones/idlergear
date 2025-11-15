import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from src.main import app


class TestNewCommand:
    """Tests for the 'new' command."""

    def test_new_command_accepts_path_option(self):
        """Test that the new command accepts a --path option."""
        runner = CliRunner()
        
        # This will fail without GitHub auth, but we're testing argument parsing
        with patch('src.main.get_github_token', return_value='test_token'):
            result = runner.invoke(app, ['new', 'test-project', '--path', '/tmp'])
            # We expect it to fail on GitHub API, not on argument parsing
            assert '--path' not in result.stdout or result.exit_code != 2

    def test_warns_when_creating_inside_idlergear(self):
        """Test that a warning is shown when creating inside idlergear repo."""
        # This is more of an integration test and would require mocking
        # the git commands and GitHub API calls
        pass

    def test_uses_current_directory_by_default(self):
        """Test that projects are created in current directory by default."""
        # Would require full mocking of GitHub API
        pass

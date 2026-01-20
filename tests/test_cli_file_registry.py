"""Tests for file registry CLI commands."""

import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from idlergear.cli import app

runner = CliRunner()


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            os.chdir(project_path)

            # Create .idlergear directory
            (project_path / ".idlergear").mkdir()

            yield project_path
    finally:
        os.chdir(old_cwd)


def test_file_register(temp_project):
    """Test registering a file."""
    result = runner.invoke(app, ["file", "register", "test.csv", "--status", "current"])
    assert result.exit_code == 0
    assert "Registered test.csv as current" in result.stdout


def test_file_register_with_reason(temp_project):
    """Test registering a file with reason."""
    result = runner.invoke(
        app,
        ["file", "register", "test.csv", "--status", "deprecated", "--reason", "Old schema"],
    )
    assert result.exit_code == 0
    assert "Registered test.csv as deprecated" in result.stdout
    assert "Old schema" in result.stdout


def test_file_register_invalid_status(temp_project):
    """Test registering with invalid status."""
    result = runner.invoke(app, ["file", "register", "test.csv", "--status", "invalid"])
    assert result.exit_code == 1
    assert "Invalid status" in result.stdout


def test_file_deprecate(temp_project):
    """Test deprecating a file."""
    result = runner.invoke(
        app,
        [
            "file",
            "deprecate",
            "old.csv",
            "--reason",
            "Outdated",
            "--successor",
            "new.csv",
        ],
    )
    assert result.exit_code == 0
    assert "Deprecated old.csv" in result.stdout
    assert "Current version: new.csv" in result.stdout
    assert "Outdated" in result.stdout


def test_file_status_registered(temp_project):
    """Test showing status of registered file."""
    # Register file first
    runner.invoke(app, ["file", "register", "test.csv", "--status", "current"])

    # Check status
    result = runner.invoke(app, ["file", "status", "test.csv"])
    assert result.exit_code == 0
    assert "test.csv" in result.stdout
    assert "current" in result.stdout


def test_file_status_not_registered(temp_project):
    """Test showing status of unregistered file."""
    result = runner.invoke(app, ["file", "status", "unknown.csv"])
    assert result.exit_code == 0
    assert "File not registered" in result.stdout


def test_file_list_empty(temp_project):
    """Test listing files when none registered."""
    result = runner.invoke(app, ["file", "list"])
    assert result.exit_code == 0
    assert "No files registered" in result.stdout


def test_file_list(temp_project):
    """Test listing registered files."""
    # Register some files
    runner.invoke(app, ["file", "register", "current.csv", "--status", "current"])
    runner.invoke(
        app,
        ["file", "register", "deprecated.csv", "--status", "deprecated"],
    )

    # List all
    result = runner.invoke(app, ["file", "list"])
    assert result.exit_code == 0
    assert "current.csv" in result.stdout
    assert "deprecated.csv" in result.stdout
    assert "Registered Files (2 total)" in result.stdout


def test_file_list_filtered(temp_project):
    """Test listing files filtered by status."""
    # Register files with different statuses
    runner.invoke(app, ["file", "register", "current.csv", "--status", "current"])
    runner.invoke(
        app,
        ["file", "register", "deprecated.csv", "--status", "deprecated"],
    )

    # List only current
    result = runner.invoke(app, ["file", "list", "--status", "current"])
    assert result.exit_code == 0
    assert "current.csv" in result.stdout
    assert "deprecated.csv" not in result.stdout


def test_file_annotate(temp_project):
    """Test annotating a file."""
    result = runner.invoke(
        app,
        [
            "file",
            "annotate",
            "test.py",
            "--description",
            "Test module",
            "--tag",
            "test",
            "--tag",
            "unit",
            "--component",
            "TestClass",
        ],
    )
    assert result.exit_code == 0
    assert "Annotated test.py" in result.stdout
    assert "Test module" in result.stdout
    assert "test, unit" in result.stdout
    assert "TestClass" in result.stdout


def test_file_annotate_partial(temp_project):
    """Test annotating with only some fields."""
    result = runner.invoke(
        app,
        ["file", "annotate", "test.py", "--description", "Test module"],
    )
    assert result.exit_code == 0
    assert "Annotated test.py" in result.stdout
    assert "Test module" in result.stdout


def test_file_search_empty(temp_project):
    """Test searching when no files match."""
    result = runner.invoke(app, ["file", "search", "--query", "nonexistent"])
    assert result.exit_code == 0
    assert "No files found" in result.stdout


def test_file_search_by_query(temp_project):
    """Test searching files by description query."""
    # Annotate some files
    runner.invoke(
        app,
        ["file", "annotate", "auth.py", "--description", "Authentication module"],
    )
    runner.invoke(
        app,
        ["file", "annotate", "user.py", "--description", "User model"],
    )

    # Search
    result = runner.invoke(app, ["file", "search", "--query", "authentication"])
    assert result.exit_code == 0
    assert "auth.py" in result.stdout
    assert "user.py" not in result.stdout


def test_file_search_by_tags(temp_project):
    """Test searching files by tags."""
    # Annotate files with tags
    runner.invoke(app, ["file", "annotate", "auth.py", "--tag", "api", "--tag", "auth"])
    runner.invoke(app, ["file", "annotate", "user.py", "--tag", "model"])

    # Search by tag
    result = runner.invoke(app, ["file", "search", "--tag", "api"])
    assert result.exit_code == 0
    assert "auth.py" in result.stdout
    assert "user.py" not in result.stdout


def test_file_search_by_components(temp_project):
    """Test searching files by components."""
    # Annotate files
    runner.invoke(
        app,
        ["file", "annotate", "auth.py", "--component", "AuthController"],
    )
    runner.invoke(app, ["file", "annotate", "user.py", "--component", "UserModel"])

    # Search
    result = runner.invoke(app, ["file", "search", "--component", "AuthController"])
    assert result.exit_code == 0
    assert "auth.py" in result.stdout
    assert "user.py" not in result.stdout


def test_file_search_combined(temp_project):
    """Test searching with multiple filters."""
    # Register and annotate
    runner.invoke(app, ["file", "register", "auth.py", "--status", "current"])
    runner.invoke(
        app,
        [
            "file",
            "annotate",
            "auth.py",
            "--description",
            "Authentication API",
            "--tag",
            "api",
        ],
    )

    runner.invoke(app, ["file", "register", "old_auth.py", "--status", "deprecated"])
    runner.invoke(
        app,
        ["file", "annotate", "old_auth.py", "--tag", "api"],
    )

    # Search with filters
    result = runner.invoke(
        app,
        ["file", "search", "--tag", "api", "--status", "current"],
    )
    assert result.exit_code == 0
    assert "auth.py" in result.stdout
    assert "old_auth.py" not in result.stdout


def test_file_unregister(temp_project):
    """Test unregistering a file."""
    # Register first
    runner.invoke(app, ["file", "register", "test.csv"])

    # Unregister
    result = runner.invoke(app, ["file", "unregister", "test.csv"])
    assert result.exit_code == 0
    assert "Unregistered test.csv" in result.stdout

    # Verify it's gone
    result = runner.invoke(app, ["file", "list"])
    assert "test.csv" not in result.stdout


def test_file_unregister_not_registered(temp_project):
    """Test unregistering a file that's not registered."""
    result = runner.invoke(app, ["file", "unregister", "unknown.csv"])
    assert result.exit_code == 1
    assert "File not registered" in result.stdout


def test_file_workflow(temp_project):
    """Test complete file registry workflow."""
    # 1. Register a current file
    result = runner.invoke(app, ["file", "register", "data_v2.csv", "--status", "current"])
    assert result.exit_code == 0

    # 2. Deprecate old version
    result = runner.invoke(
        app,
        [
            "file",
            "deprecate",
            "data.csv",
            "--successor",
            "data_v2.csv",
            "--reason",
            "Old schema",
        ],
    )
    assert result.exit_code == 0

    # 3. Annotate both files
    runner.invoke(
        app,
        [
            "file",
            "annotate",
            "data_v2.csv",
            "--description",
            "Current data file",
            "--tag",
            "data",
        ],
    )
    runner.invoke(
        app,
        [
            "file",
            "annotate",
            "data.csv",
            "--description",
            "Deprecated data file",
            "--tag",
            "data",
        ],
    )

    # 4. List all files
    result = runner.invoke(app, ["file", "list"])
    assert result.exit_code == 0
    assert "data.csv" in result.stdout
    assert "data_v2.csv" in result.stdout

    # 5. Search by tag
    result = runner.invoke(app, ["file", "search", "--tag", "data"])
    assert result.exit_code == 0
    assert "Found 2 files" in result.stdout

    # 6. Check status of deprecated file
    result = runner.invoke(app, ["file", "status", "data.csv"])
    assert result.exit_code == 0
    assert "deprecated" in result.stdout
    assert "data_v2.csv" in result.stdout
    assert "Old schema" in result.stdout

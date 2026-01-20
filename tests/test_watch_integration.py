"""Integration tests for watch with data file version detection."""

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_git_project():
    """Create a temporary git project with IdlerGear initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Initialize git
        subprocess.run(["git", "init"], cwd=project_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=project_path,
            check=True,
            capture_output=True,
        )

        # Create .idlergear directory to mark as IdlerGear project
        idlergear_dir = project_path / ".idlergear"
        idlergear_dir.mkdir()

        yield project_path


def test_watch_detects_stale_data_reference(temp_git_project):
    """Test that watch system detects when Python code references old data files."""
    project_path = temp_git_project

    # Create versioned data files
    (project_path / "data.csv").write_text("col1,col2\n1,2")
    (project_path / "data_old.csv").write_text("col1,col2\n1,2")

    # Create Python script that references old version
    script_content = """
import pandas as pd

def load_data():
    df = pd.read_csv("data_old.csv")
    return df
"""
    (project_path / "analysis.py").write_text(script_content)

    # Commit everything
    subprocess.run(["git", "add", "."], cwd=project_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=project_path, check=True
    )

    # Run watch analysis
    from idlergear.watch import analyze

    result = analyze(project_path)

    # Check that we got a warning about stale data reference
    data_version_suggestions = [
        s for s in result.suggestions if s.category == "data_version"
    ]

    assert len(data_version_suggestions) > 0, "Should detect stale data file reference"

    warning = data_version_suggestions[0]
    assert "analysis.py" in warning.message
    assert warning.severity == "warning"
    assert "stale_file" in warning.context
    assert warning.context["stale_file"] == "data_old.csv"
    assert warning.context["current_file"] == "data.csv"


def test_watch_no_warning_for_current_data_file(temp_git_project):
    """Test that watch doesn't warn when using current version."""
    project_path = temp_git_project

    # Create versioned data files
    (project_path / "data.csv").write_text("col1,col2\n1,2")
    (project_path / "data_old.csv").write_text("col1,col2\n1,2")

    # Create Python script that uses CURRENT version
    script_content = """
import pandas as pd

def load_data():
    df = pd.read_csv("data.csv")  # Using current version
    return df
"""
    (project_path / "analysis.py").write_text(script_content)

    # Commit everything
    subprocess.run(["git", "add", "."], cwd=project_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=project_path, check=True
    )

    # Run watch analysis
    from idlergear.watch import analyze

    result = analyze(project_path)

    # Check that we did NOT get a warning
    data_version_suggestions = [
        s for s in result.suggestions if s.category == "data_version"
    ]

    assert len(data_version_suggestions) == 0, "Should not warn about current version"


def test_watch_detects_multiple_stale_references(temp_git_project):
    """Test detection of multiple stale file references."""
    project_path = temp_git_project

    # Create multiple versioned files
    (project_path / "input.csv").write_text("data")
    (project_path / "input_old.csv").write_text("data")
    (project_path / "config.json").write_text("{}")
    (project_path / "config_v1.json").write_text("{}")

    # Script with multiple stale references
    script_content = """
import pandas as pd
import json

df = pd.read_csv("input_old.csv")

with open("config_v1.json") as f:
    config = json.load(f)
"""
    (project_path / "process.py").write_text(script_content)

    # Commit
    subprocess.run(["git", "add", "."], cwd=project_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=project_path, check=True
    )

    # Run watch
    from idlergear.watch import analyze

    result = analyze(project_path)

    data_version_suggestions = [
        s for s in result.suggestions if s.category == "data_version"
    ]

    assert len(data_version_suggestions) == 2, "Should detect both stale references"

    stale_files = {s.context["stale_file"] for s in data_version_suggestions}
    assert "input_old.csv" in stale_files
    assert "config_v1.json" in stale_files


def test_watch_handles_no_versioned_files(temp_git_project):
    """Test that watch doesn't crash when no versioned files exist."""
    project_path = temp_git_project

    # Create files without version suffixes
    (project_path / "data.csv").write_text("data")
    (project_path / "script.py").write_text('df = pd.read_csv("data.csv")')

    # Commit
    subprocess.run(["git", "add", "."], cwd=project_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=project_path, check=True
    )

    # Run watch - should not crash
    from idlergear.watch import analyze

    result = analyze(project_path)

    # Should have no data version warnings (but shouldn't crash)
    data_version_suggestions = [
        s for s in result.suggestions if s.category == "data_version"
    ]

    assert len(data_version_suggestions) == 0

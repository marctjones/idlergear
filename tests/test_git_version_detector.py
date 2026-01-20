"""Tests for git version detection."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from idlergear.git_version_detector import (
    detect_renames,
    detect_versioned_files,
    get_stale_versions,
    group_versioned_files,
    identify_current_version,
    match_version_pattern,
)


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        yield repo_path


def test_match_version_pattern():
    """Test version pattern matching."""
    # Version number
    result = match_version_pattern("api_v2.py")
    assert result == ("api.py", "_v2", "version_number")

    # Old suffix
    result = match_version_pattern("handler_old.py")
    assert result == ("handler.py", "_old", "old")

    # New suffix
    result = match_version_pattern("service_new.py")
    assert result == ("service.py", "_new", "new")

    # Backup
    result = match_version_pattern("util_backup.py")
    assert result == ("util.py", "_backup", "backup")

    # Bak extension
    result = match_version_pattern("config.py.bak")
    assert result == ("config.py", ".bak", "bak")

    # Timestamp
    result = match_version_pattern("data_20250119.py")
    assert result == ("data.py", "_20250119", "timestamp")

    # No match
    result = match_version_pattern("normal.py")
    assert result is None


def test_group_versioned_files():
    """Test grouping files by base name."""
    files = [
        "api.py",
        "api_v2.py",
        "api_old.py",
        "handler.py",
        "handler_new.py",
        "util.py",
    ]

    groups = group_versioned_files(files)

    assert "api.py" in groups
    assert set(groups["api.py"]) == {"api_v2.py", "api_old.py"}

    assert "handler.py" in groups
    assert groups["handler.py"] == ["handler_new.py"]

    assert "util.py" not in groups  # No versions


def test_identify_current_version_base_file():
    """Test current version identification with base file."""
    versions = ["api.py", "api_old.py", "api_backup.py"]
    current = identify_current_version(versions)
    assert current == "api.py"


def test_identify_current_version_number():
    """Test current version identification with version numbers."""
    versions = ["api_v1.py", "api_v2.py", "api_v3.py"]
    current = identify_current_version(versions)
    assert current == "api_v3.py"


def test_identify_current_version_new_suffix():
    """Test current version identification with _new suffix."""
    versions = ["handler.py", "handler_new.py", "handler_old.py"]
    current = identify_current_version(versions)

    # When "_new" exists, it overrides base
    assert current == "handler_new.py"


def test_detect_renames(temp_git_repo):
    """Test git rename detection."""
    repo_path = temp_git_repo

    # Create initial file
    api_file = repo_path / "api.py"
    api_file.write_text("def get_user(): pass")

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True
    )

    # Rename file
    subprocess.run(["git", "mv", "api.py", "api_old.py"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Rename to api_old.py"], cwd=repo_path, check=True
    )

    # Create new api.py
    api_file.write_text("def get_user_v2(): pass")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "New api.py"], cwd=repo_path, check=True
    )

    # Detect renames
    renames = detect_renames(repo_path)

    assert len(renames) == 1
    assert renames[0] == ("api.py", "api_old.py")


def test_detect_versioned_files(temp_git_repo):
    """Test full versioned file detection."""
    repo_path = temp_git_repo

    # Create versioned files
    (repo_path / "api.py").write_text("# Current API")
    (repo_path / "api_v2.py").write_text("# API v2")
    (repo_path / "api_old.py").write_text("# Old API")
    (repo_path / "handler.py").write_text("# Handler")
    (repo_path / "normal.py").write_text("# Normal file")

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add files"], cwd=repo_path, check=True)

    # Detect versions
    groups = detect_versioned_files(repo_path, include_renames=False)

    assert "api.py" in groups
    assert len(groups["api.py"]) == 3

    # Check current version
    current = [v for v in groups["api.py"] if v.is_current]
    assert len(current) == 1
    assert current[0].path == "api.py"

    # Check stale versions
    stale = [v for v in groups["api.py"] if not v.is_current]
    assert len(stale) == 2
    assert {v.path for v in stale} == {"api_v2.py", "api_old.py"}


def test_get_stale_versions(temp_git_repo):
    """Test getting stale versions."""
    repo_path = temp_git_repo

    # Create files
    (repo_path / "api.py").write_text("# Current")
    (repo_path / "api_old.py").write_text("# Old")
    (repo_path / "handler_v2.py").write_text("# Handler v2")
    (repo_path / "handler_v3.py").write_text("# Handler v3")

    subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "-m", "Add files"], cwd=repo_path, check=True)

    # Detect and get stale
    groups = detect_versioned_files(repo_path, include_renames=False)
    stale = get_stale_versions(groups)

    assert len(stale) >= 2
    stale_paths = {v.path for v in stale}
    assert "api_old.py" in stale_paths
    assert "handler_v2.py" in stale_paths

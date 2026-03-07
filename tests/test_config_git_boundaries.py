"""Test that find_idlergear_root respects git boundaries."""

import tempfile
from pathlib import Path

from idlergear.config import find_idlergear_root


def test_respects_git_boundaries():
    """Test that find_idlergear_root doesn't cross git boundaries.

    This prevents global ~/.idlergear/ from contaminating project-specific data.
    Addresses issue #414 and #415.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create directory structure:
        # /tmp/
        #   parent/.idlergear/  (global-like instance)
        #   parent/project/.git/ (git repo without .idlergear)

        parent = tmpdir / "parent"
        project = parent / "project"
        project.mkdir(parents=True)

        # Create "global" .idlergear in parent
        (parent / ".idlergear").mkdir()

        # Create git repo in project
        (project / ".git").mkdir()

        # From inside project, should NOT find parent's .idlergear
        result = find_idlergear_root(str(project))
        assert result is None, f"Should not find parent .idlergear, got: {result}"


def test_finds_idlergear_within_git_repo():
    """Test that it finds .idlergear within the same git repo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create git repo with .idlergear at root
        project = tmpdir / "project"
        project.mkdir()
        (project / ".git").mkdir()
        (project / ".idlergear").mkdir()

        # Create subdirectory
        subdir = project / "src" / "module"
        subdir.mkdir(parents=True)

        # From subdirectory, should find project root
        result = find_idlergear_root(str(subdir))
        assert result == project, f"Expected {project}, got {result}"


def test_non_git_directory():
    """Test behavior when not in a git repo.

    When not in a git repo, only check current directory to prevent
    accidentally using a parent directory's .idlergear.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create non-git directory structure
        parent = tmpdir / "parent"
        child = parent / "child"
        child.mkdir(parents=True)

        # Put .idlergear in parent
        (parent / ".idlergear").mkdir()

        # From child, should NOT find parent's .idlergear (not in git)
        result = find_idlergear_root(str(child))
        assert result is None, f"Should not find parent .idlergear outside git, got: {result}"


def test_finds_idlergear_in_current_dir_when_not_in_git():
    """Test that .idlergear in current dir is found even outside git."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create directory with .idlergear but no git
        project = tmpdir / "project"
        project.mkdir()
        (project / ".idlergear").mkdir()

        # Should find .idlergear in current directory
        result = find_idlergear_root(str(project))
        assert result == project, f"Expected {project}, got {result}"

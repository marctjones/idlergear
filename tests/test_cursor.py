"""Tests for Cursor AI IDE integration."""

import tempfile
from pathlib import Path

import pytest

from idlergear.cursor import (
    generate_context_rule,
    generate_cursorignore,
    generate_tasks_rule,
    generate_vision_rule,
    install_cursor_rules,
)


def test_generate_vision_rule():
    """Test vision rule generation."""
    content = generate_vision_rule()

    assert "---" in content  # YAML frontmatter
    assert "description:" in content
    assert "globs:" in content
    assert "alwaysApply:" in content
    assert "idlergear vision show" in content
    assert "Project Vision" in content


def test_generate_tasks_rule():
    """Test tasks rule generation."""
    content = generate_tasks_rule()

    assert "---" in content
    assert "description:" in content
    assert "Active Tasks" in content
    assert "idlergear task list" in content
    assert "idlergear task close" in content
    assert "Never write TODO comments" in content


def test_generate_context_rule():
    """Test context rule generation."""
    content = generate_context_rule()

    assert "---" in content
    assert "description:" in content
    assert "IdlerGear Project Context" in content
    assert "idlergear context" in content
    assert "Plugin System" in content
    assert "Forbidden" in content


def test_install_cursor_rules():
    """Test Cursor rules installation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create .idlergear directory to simulate initialized project
        (project_path / ".idlergear").mkdir()

        # Install rules
        results = install_cursor_rules(project_path)

        # Check that all files were created
        assert len(results) == 3
        assert all(action == "created" for action in results.values())

        # Check files exist
        cursor_dir = project_path / ".cursor" / "rules"
        assert cursor_dir.exists()
        assert (cursor_dir / "idlergear-vision.mdc").exists()
        assert (cursor_dir / "idlergear-tasks.mdc").exists()
        assert (cursor_dir / "idlergear-context.mdc").exists()

        # Check content is correct
        vision_content = (cursor_dir / "idlergear-vision.mdc").read_text()
        assert "Project Vision" in vision_content
        assert "idlergear vision show" in vision_content

        # Second installation should report unchanged
        results2 = install_cursor_rules(project_path)
        assert all(action == "unchanged" for action in results2.values())


def test_generate_cursorignore():
    """Test .cursorignore generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create .idlergear directory
        (project_path / ".idlergear").mkdir()

        # Generate .cursorignore
        action = generate_cursorignore(project_path)

        assert action == "created"
        assert (project_path / ".cursorignore").exists()

        # Check content
        content = (project_path / ".cursorignore").read_text()
        assert ".idlergear/" in content
        assert ".claude/hooks/" in content
        assert "__pycache__/" in content
        assert "venv/" in content

        # Second generation should report unchanged
        action2 = generate_cursorignore(project_path)
        assert action2 == "unchanged"


def test_cursorignore_update_existing():
    """Test .cursorignore updates existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create .idlergear directory
        (project_path / ".idlergear").mkdir()

        # Create existing .cursorignore without IdlerGear section
        cursorignore = project_path / ".cursorignore"
        cursorignore.write_text("# Existing content\n*.pyc\n")

        # Generate .cursorignore
        action = generate_cursorignore(project_path)

        assert action == "updated"

        # Check content was appended
        content = cursorignore.read_text()
        assert "# Existing content" in content
        assert ".idlergear/" in content


def test_install_cursor_rules_explicitly_provided_path():
    """Test with explicitly provided project path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create .idlergear directory
        (project_path / ".idlergear").mkdir()

        # Install with explicit path
        results = install_cursor_rules(project_path)

        # Should succeed with explicit path
        assert len(results) == 3
        assert all(action == "created" for action in results.values())

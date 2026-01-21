"""Tests for Aider AI coding assistant integration."""

import tempfile
from pathlib import Path

import pytest

from idlergear.aider import (
    generate_aider_config,
    generate_aiderignore,
    install_aider_config,
)


def test_generate_aider_config():
    """Test Aider configuration generation."""
    content = generate_aider_config()

    # Check YAML structure
    assert "# .aider.conf.yml" in content
    assert "auto-commits:" in content
    assert "dirty-commits:" in content

    # Check context files
    assert "read:" in content
    assert "VISION.md" in content
    assert "AGENTS.md" in content
    assert "CLAUDE.md" in content
    assert "DEVELOPMENT.md" in content
    assert "README.md" in content

    # Check conventions
    assert "conventions:" in content
    assert "IdlerGear Development Conventions" in content
    assert "typer" in content
    assert "pytest" in content

    # Check editor settings
    assert "edit-format: diff" in content
    assert "show-diffs: true" in content

    # Check code quality tools
    assert "lint-cmd: ruff check" in content
    assert "test-cmd: pytest" in content

    # Check git settings
    assert "git: true" in content
    assert "gitignore: true" in content


def test_install_aider_config():
    """Test Aider configuration installation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create .idlergear directory to simulate initialized project
        (project_path / ".idlergear").mkdir()

        # Install configuration
        action = install_aider_config(project_path)

        assert action == "created"
        assert (project_path / ".aider.conf.yml").exists()

        # Check content
        content = (project_path / ".aider.conf.yml").read_text()
        assert "auto-commits:" in content
        assert "VISION.md" in content
        assert "conventions:" in content

        # Second installation should report unchanged
        action2 = install_aider_config(project_path)
        assert action2 == "unchanged"


def test_install_aider_config_update():
    """Test Aider configuration update when content differs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create .idlergear directory
        (project_path / ".idlergear").mkdir()

        # Create existing config with different content
        config_path = project_path / ".aider.conf.yml"
        config_path.write_text("# Old config\nauto-commits: true\n")

        # Install should update
        action = install_aider_config(project_path)
        assert action == "updated"

        # Check content was replaced
        content = config_path.read_text()
        assert "IdlerGear" in content
        assert "conventions:" in content


def test_generate_aiderignore():
    """Test .aiderignore generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create .idlergear directory
        (project_path / ".idlergear").mkdir()

        # Generate .aiderignore
        action = generate_aiderignore(project_path)

        assert action == "created"
        assert (project_path / ".aiderignore").exists()

        # Check content
        content = (project_path / ".aiderignore").read_text()
        assert ".idlergear/" in content
        assert ".claude/hooks/" in content
        assert "__pycache__/" in content
        assert "venv/" in content
        assert ".cursor/" in content
        assert "node_modules/" in content

        # Second generation should report unchanged
        action2 = generate_aiderignore(project_path)
        assert action2 == "unchanged"


def test_aiderignore_update_existing():
    """Test .aiderignore updates existing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create .idlergear directory
        (project_path / ".idlergear").mkdir()

        # Create existing .aiderignore without IdlerGear section
        aiderignore = project_path / ".aiderignore"
        aiderignore.write_text("# Existing content\n*.pyc\n")

        # Generate .aiderignore
        action = generate_aiderignore(project_path)

        assert action == "updated"

        # Check content was appended
        content = aiderignore.read_text()
        assert "# Existing content" in content
        assert ".idlergear/" in content


def test_install_aider_config_explicitly_provided_path():
    """Test with explicitly provided project path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Create .idlergear directory
        (project_path / ".idlergear").mkdir()

        # Install with explicit path
        action = install_aider_config(project_path)

        # Should succeed with explicit path
        assert action == "created"
        assert (project_path / ".aider.conf.yml").exists()


def test_aiderignore_content_completeness():
    """Test .aiderignore includes all necessary patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        (project_path / ".idlergear").mkdir()

        generate_aiderignore(project_path)
        content = (project_path / ".aiderignore").read_text()

        # IdlerGear patterns
        assert ".idlergear/" in content
        assert ".claude/hooks/" in content
        assert ".claude/scripts/" in content

        # Build artifacts
        assert "__pycache__/" in content
        assert "*.egg-info/" in content

        # Virtual environments
        assert "venv/" in content
        assert "env/" in content

        # IDE files
        assert ".vscode/" in content
        assert ".cursor/" in content

        # Test artifacts
        assert ".pytest_cache/" in content
        assert ".coverage" in content


def test_aider_config_conventions_section():
    """Test that conventions section includes key guidelines."""
    content = generate_aider_config()

    # Check key conventions are present
    assert "CLI Commands" in content
    assert "Code Style" in content
    assert "Testing" in content
    assert "MCP Tools" in content
    assert "Knowledge Management" in content

    # Check specific conventions
    assert "No TODO comments" in content
    assert "use idlergear note create" in content
    assert "Document architecture decisions as references" in content

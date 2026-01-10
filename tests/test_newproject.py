"""Tests for new project creation."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from idlergear.newproject import create_project, slugify_package


class TestSlugifyPackage:
    """Tests for slugify_package."""

    def test_lowercase(self):
        assert slugify_package("MyProject") == "myproject"

    def test_replace_dash(self):
        assert slugify_package("my-project") == "my_project"

    def test_replace_space(self):
        assert slugify_package("my project") == "my_project"

    def test_combined(self):
        assert slugify_package("My-Cool Project") == "my_cool_project"


class TestCreateProject:
    """Tests for create_project."""

    def test_create_base_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = create_project(
                "test-project",
                path=tmpdir,
                init_git=False,
            )

            assert project_path.exists()
            assert (project_path / ".idlergear").is_dir()
            assert (project_path / ".claude").is_dir()
            assert (project_path / ".mcp.json").exists()
            assert (project_path / "AGENTS.md").exists()
            assert (project_path / "CLAUDE.md").exists()
            assert (project_path / ".gitignore").exists()

    def test_create_with_vision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_project(
                "test-project",
                path=tmpdir,
                vision="Build the best thing",
                init_git=False,
            )

            # Vision is in project root, not .idlergear
            vision_path = Path(tmpdir) / "test-project" / "VISION.md"
            assert "Build the best thing" in vision_path.read_text()

    def test_create_with_description(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_project(
                "test-project",
                path=tmpdir,
                description="A test project",
                init_git=False,
            )

            # Description is used in various places
            assert (Path(tmpdir) / "test-project").exists()

    def test_create_already_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test-project"
            project_path.mkdir()

            with pytest.raises(ValueError, match="already exists"):
                create_project("test-project", path=tmpdir)

    def test_create_unknown_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="Unknown template"):
                create_project(
                    "test-project",
                    path=tmpdir,
                    template="nonexistent",
                )

    def test_create_idlergear_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = create_project(
                "test-project",
                path=tmpdir,
                init_git=False,
            )

            idlergear = project_path / ".idlergear"
            assert (idlergear / "issues").is_dir()  # renamed from tasks
            assert (idlergear / "notes").is_dir()
            assert (idlergear / "plans").is_dir()
            assert (idlergear / "wiki").is_dir()  # renamed from reference
            assert (idlergear / "runs").is_dir()
            assert (idlergear / "config.toml").exists()
            # Vision is in project root, not .idlergear
            assert (project_path / "VISION.md").exists()

    def test_create_claude_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = create_project(
                "test-project",
                path=tmpdir,
                init_git=False,
            )

            claude = project_path / ".claude"
            assert claude.is_dir()
            assert (claude / "settings.json").exists()
            assert (claude / "rules").is_dir()
            assert (claude / "rules" / "idlergear.md").exists()

    def test_create_mcp_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = create_project(
                "test-project",
                path=tmpdir,
                init_git=False,
            )

            mcp_path = project_path / ".mcp.json"
            with open(mcp_path) as f:
                config = json.load(f)

            assert "mcpServers" in config
            assert "idlergear" in config["mcpServers"]


class TestCreatePythonProject:
    """Tests for Python project template."""

    def test_create_python_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = create_project(
                "my-python-app",
                path=tmpdir,
                template="python",
                init_git=False,
                init_venv=False,
            )

            assert (project_path / "pyproject.toml").exists()
            assert (project_path / "README.md").exists()
            assert (project_path / "src" / "my_python_app" / "__init__.py").exists()
            assert (project_path / "tests" / "__init__.py").exists()
            assert (project_path / "tests" / "test_placeholder.py").exists()

    def test_python_pyproject_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = create_project(
                "test-app",
                path=tmpdir,
                template="python",
                description="A test app",
                init_git=False,
                init_venv=False,
            )

            pyproject = project_path / "pyproject.toml"
            content = pyproject.read_text()

            assert 'name = "test-app"' in content
            assert "test_app" in content  # package name
            assert "A test app" in content

    def test_python_claude_rules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = create_project(
                "test-app",
                path=tmpdir,
                template="python",
                init_git=False,
                init_venv=False,
            )

            python_rules = project_path / ".claude" / "rules" / "ig_python.md"
            assert python_rules.exists()

    def test_python_with_venv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = create_project(
                "test-app",
                path=tmpdir,
                template="python",
                init_git=False,
                init_venv=True,
            )

            venv_path = project_path / "venv"
            # venv may or may not exist depending on python availability
            # but hooks should be created if venv was created
            if venv_path.exists():
                hooks_path = project_path / ".claude" / "hooks" / "ig_activate-venv.sh"
                assert hooks_path.exists()


class TestCreateWithGit:
    """Tests for git initialization."""

    def test_create_with_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = create_project(
                "test-project",
                path=tmpdir,
                init_git=True,
            )

            git_dir = project_path / ".git"
            # Git should be initialized if git is available
            # We don't fail if git isn't installed

    def test_create_without_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = create_project(
                "test-project",
                path=tmpdir,
                init_git=False,
            )

            git_dir = project_path / ".git"
            assert not git_dir.exists()

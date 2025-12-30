"""Tests for project initialization."""

import os
import tempfile
from pathlib import Path

import pytest


class TestInitProject:
    """Tests for init_project."""

    def test_init_project(self, save_cwd):
        from idlergear.init import init_project

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            init_project(".")

            idlergear_path = Path(tmpdir) / ".idlergear"
            assert idlergear_path.exists()
            assert (idlergear_path / "config.toml").exists()
            assert (idlergear_path / "vision.md").exists()
            assert (idlergear_path / "tasks").is_dir()
            assert (idlergear_path / "notes").is_dir()
            assert (idlergear_path / "explorations").is_dir()
            assert (idlergear_path / "plans").is_dir()
            assert (idlergear_path / "reference").is_dir()
            assert (idlergear_path / "runs").is_dir()

    def test_init_already_initialized(self, save_cwd, capsys):
        from idlergear.init import init_project

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # First init
            init_project(".")

            # Second init should show warning
            init_project(".")

            captured = capsys.readouterr()
            assert "already initialized" in captured.out

    def test_init_creates_config_content(self, save_cwd):
        from idlergear.init import init_project

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            init_project(".")

            config_path = Path(tmpdir) / ".idlergear" / "config.toml"
            content = config_path.read_text()

            assert "[project]" in content
            assert "[github]" in content
            assert "[daemon]" in content

    def test_init_creates_vision(self, save_cwd):
        from idlergear.init import init_project

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            init_project(".")

            vision_path = Path(tmpdir) / ".idlergear" / "vision.md"
            content = vision_path.read_text()

            assert "Project Vision" in content

    def test_init_updates_gitignore(self, save_cwd):
        from idlergear.init import init_project

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create existing .gitignore
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("*.pyc\n")

            init_project(".")

            content = gitignore.read_text()
            assert "daemon.sock" in content
            assert "daemon.pid" in content

    def test_init_no_gitignore(self, save_cwd):
        from idlergear.init import init_project

        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            init_project(".")

            # Should not create .gitignore if it doesn't exist
            gitignore = Path(tmpdir) / ".gitignore"
            assert not gitignore.exists()

    def test_init_with_path(self, save_cwd):
        from idlergear.init import init_project

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "myproject"
            subdir.mkdir()

            init_project(str(subdir))

            assert (subdir / ".idlergear").exists()

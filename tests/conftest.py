"""Pytest fixtures for IdlerGear tests."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def save_cwd():
    """Save and restore current working directory."""
    old_cwd = os.getcwd()
    yield
    os.chdir(old_cwd)


@pytest.fixture
def temp_project():
    """Create a temporary project directory with IdlerGear initialized."""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            idlergear_path = project_path / ".idlergear"

            # Create directory structure
            directories = [
                idlergear_path,
                idlergear_path / "tasks",
                idlergear_path / "notes",
                idlergear_path / "explorations",
                idlergear_path / "plans",
                idlergear_path / "reference",
                idlergear_path / "runs",
            ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

            # Create config file
            config_path = idlergear_path / "config.toml"
            config_path.write_text("""\
[project]
name = "test-project"
""")

            # Create empty vision file
            vision_path = idlergear_path / "vision.md"
            vision_path.write_text("# Project Vision\n\n")

            # Change to project directory
            os.chdir(project_path)

            yield project_path
    finally:
        os.chdir(old_cwd)

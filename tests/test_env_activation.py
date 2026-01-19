"""Tests for automatic environment detection and activation."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from idlergear.env import activate_project_env, find_virtualenv


class TestFindVirtualenv:
    """Tests for find_virtualenv function."""

    def test_find_venv_standard(self, tmp_path):
        """Test finding a standard venv directory."""
        # Create a fake venv structure
        venv_dir = tmp_path / "venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").touch()

        result = find_virtualenv(tmp_path)

        assert result is not None
        assert result["type"] == "venv"
        assert result["name"] == "venv"
        assert Path(result["path"]) == venv_dir

    def test_find_venv_dotenv(self, tmp_path):
        """Test finding a .venv directory."""
        # Create a fake .venv structure
        venv_dir = tmp_path / ".venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").touch()

        result = find_virtualenv(tmp_path)

        assert result is not None
        assert result["type"] == "venv"
        assert result["name"] == ".venv"

    def test_find_poetry(self, tmp_path):
        """Test detecting poetry project."""
        (tmp_path / "poetry.lock").touch()

        result = find_virtualenv(tmp_path)

        assert result is not None
        assert result["type"] == "poetry"
        assert "poetry run python" in result["command"]

    def test_find_pipenv(self, tmp_path):
        """Test detecting pipenv project."""
        (tmp_path / "Pipfile").touch()

        result = find_virtualenv(tmp_path)

        assert result is not None
        assert result["type"] == "pipenv"
        assert "pipenv run python" in result["command"]

    def test_no_venv_found(self, tmp_path):
        """Test when no venv is present."""
        result = find_virtualenv(tmp_path)
        assert result is None


class TestActivateProjectEnv:
    """Tests for activate_project_env function."""

    def test_activate_standard_venv(self, tmp_path):
        """Test activating a standard venv."""
        # Create a fake venv structure
        venv_dir = tmp_path / "venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        python_exe = venv_bin / "python"
        python_exe.touch()
        python_exe.chmod(0o755)

        # Save original env
        original_env = os.environ.copy()

        try:
            result = activate_project_env(tmp_path)

            assert result is not None
            assert result["activated"] is True
            assert result["type"] == "venv"
            assert result["method"] == "environment"

            # Check environment variables were set
            assert os.environ.get("VIRTUAL_ENV") == str(venv_dir)
            assert str(venv_bin) in os.environ.get("PATH", "")

            # Verify PYTHONHOME is not set
            assert "PYTHONHOME" not in os.environ

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_activate_poetry(self, tmp_path):
        """Test detecting poetry (no actual activation)."""
        (tmp_path / "poetry.lock").touch()

        result = activate_project_env(tmp_path)

        assert result is not None
        assert result["activated"] is False
        assert result["type"] == "poetry"
        assert result["method"] == "wrapper"
        assert "note" in result

    def test_no_venv_no_activation(self, tmp_path):
        """Test when no venv exists."""
        result = activate_project_env(tmp_path)
        assert result is None


class TestSubprocessActivation:
    """Tests that subprocess calls use the activated environment."""

    @pytest.mark.skipif(
        not Path("/home/marc/Projects/idlergear/venv").exists(),
        reason="IdlerGear venv not present",
    )
    def test_subprocess_uses_venv(self):
        """Test that subprocess calls use venv after activation."""
        # Save original env
        original_env = os.environ.copy()

        try:
            # Activate IdlerGear's venv
            result = activate_project_env(Path("/home/marc/Projects/idlergear"))

            if result and result["activated"]:
                # Run a subprocess to check which Python it uses
                proc_result = subprocess.run(
                    ["python3", "-c", "import sys; print(sys.executable)"],
                    capture_output=True,
                    text=True,
                )

                # Should be using venv python
                assert "idlergear/venv" in proc_result.stdout

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_activation_prepends_to_path(self, tmp_path):
        """Test that venv bin is prepended to PATH."""
        # Create a fake venv
        venv_dir = tmp_path / "venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").touch()

        # Save original PATH
        original_path = os.environ.get("PATH", "")

        try:
            activate_project_env(tmp_path)

            # Check that venv bin is at the start of PATH
            new_path = os.environ.get("PATH", "")
            assert new_path.startswith(str(venv_bin))

        finally:
            # Restore PATH
            os.environ["PATH"] = original_path

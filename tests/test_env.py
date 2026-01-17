"""Tests for environment detection and management."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from idlergear.env import (
    detect_python_env,
    detect_node_env,
    detect_rust_env,
    detect_dotnet_env,
    get_environment_info,
    which_enhanced,
    detect_project_type,
    find_virtualenv,
)


class TestDetectPythonEnv:
    """Tests for detect_python_env."""

    def test_basic_python_info(self):
        """Test that basic Python info is returned."""
        result = detect_python_env()

        assert "version" in result
        assert "executable" in result
        assert "prefix" in result
        assert "base_prefix" in result
        assert "in_virtualenv" in result
        assert result["executable"] == sys.executable

    def test_version_format(self):
        """Test version format is correct."""
        result = detect_python_env()

        expected_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert result["version"] == expected_version

    def test_virtualenv_detection_venv(self):
        """Test venv detection when in a venv."""
        with patch.dict(os.environ, {"VIRTUAL_ENV": "/path/to/venv"}):
            with patch.object(sys, "prefix", "/path/to/venv"):
                with patch.object(sys, "base_prefix", "/usr"):
                    result = detect_python_env()
                    assert result["in_virtualenv"] is True
                    assert result["venv_type"] == "venv"
                    assert result["venv_path"] == "/path/to/venv"

    def test_virtualenv_detection_conda(self):
        """Test conda detection when in conda env."""
        with patch.dict(os.environ, {"CONDA_DEFAULT_ENV": "myenv", "CONDA_PREFIX": "/path/to/conda"}):
            with patch.object(sys, "prefix", "/path/to/conda"):
                with patch.object(sys, "base_prefix", "/usr"):
                    result = detect_python_env()
                    assert result["in_virtualenv"] is True
                    assert result["venv_type"] == "conda"

    def test_virtualenv_detection_poetry(self):
        """Test poetry detection."""
        with patch.dict(os.environ, {"POETRY_ACTIVE": "1"}):
            with patch.object(sys, "prefix", "/path/to/poetry"):
                with patch.object(sys, "base_prefix", "/usr"):
                    result = detect_python_env()
                    assert result["in_virtualenv"] is True
                    assert result["venv_type"] == "poetry"

    def test_no_virtualenv(self):
        """Test when not in a virtualenv."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove venv-related env vars
            env = dict(os.environ)
            env.pop("VIRTUAL_ENV", None)
            env.pop("CONDA_DEFAULT_ENV", None)
            env.pop("POETRY_ACTIVE", None)
            with patch.dict(os.environ, env, clear=True):
                with patch.object(sys, "prefix", "/usr"):
                    with patch.object(sys, "base_prefix", "/usr"):
                        result = detect_python_env()
                        assert result["in_virtualenv"] is False
                        assert result["venv_type"] is None


class TestDetectNodeEnv:
    """Tests for detect_node_env."""

    def test_node_not_available(self):
        """Test when node is not available."""
        with patch("shutil.which", return_value=None):
            result = detect_node_env()
            assert result is None

    def test_node_available(self):
        """Test when node is available."""
        with patch("shutil.which", return_value="/usr/bin/node"):
            with patch("subprocess.run") as mock_run:
                # Mock successful node --version
                mock_run.side_effect = [
                    MagicMock(stdout="v18.0.0\n"),
                    MagicMock(stdout="9.0.0\n"),
                ]
                result = detect_node_env()
                assert result is not None
                assert result["node_version"] == "v18.0.0"
                assert result["npm_version"] == "9.0.0"
                assert result["node_path"] == "/usr/bin/node"

    def test_node_timeout(self):
        """Test when node command times out."""
        with patch("shutil.which", return_value="/usr/bin/node"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("node", 2)
                result = detect_node_env()
                assert result is not None
                assert "error" in result

    def test_node_subprocess_error(self):
        """Test when subprocess raises error."""
        with patch("shutil.which", return_value="/usr/bin/node"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.SubprocessError()
                result = detect_node_env()
                assert result is not None
                assert "error" in result


class TestDetectRustEnv:
    """Tests for detect_rust_env."""

    def test_rust_not_available(self):
        """Test when rust is not available."""
        with patch("shutil.which", return_value=None):
            result = detect_rust_env()
            assert result is None

    def test_rust_available(self):
        """Test when rust is available."""
        with patch("shutil.which", return_value="/usr/bin/cargo"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    MagicMock(stdout="cargo 1.75.0\n"),
                    MagicMock(stdout="rustc 1.75.0\n"),
                ]
                result = detect_rust_env()
                assert result is not None
                assert result["cargo_version"] == "cargo 1.75.0"
                assert result["rustc_version"] == "rustc 1.75.0"
                assert result["cargo_path"] == "/usr/bin/cargo"

    def test_rust_timeout(self):
        """Test when rust command times out."""
        with patch("shutil.which", return_value="/usr/bin/cargo"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("cargo", 2)
                result = detect_rust_env()
                assert result is not None
                assert "error" in result


class TestDetectDotNetEnv:
    """Tests for detect_dotnet_env."""

    def test_dotnet_not_available(self):
        """Test when dotnet is not available."""
        with patch("shutil.which", return_value=None):
            result = detect_dotnet_env()
            assert result is None

    def test_dotnet_available(self):
        """Test when dotnet is available."""
        with patch("shutil.which", return_value="/usr/bin/dotnet"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(stdout="8.0.100\n")
                result = detect_dotnet_env()
                assert result is not None
                assert result["dotnet_version"] == "8.0.100"
                assert result["dotnet_path"] == "/usr/bin/dotnet"

    def test_dotnet_timeout(self):
        """Test when dotnet command times out."""
        with patch("shutil.which", return_value="/usr/bin/dotnet"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("dotnet", 2)
                result = detect_dotnet_env()
                assert result is not None
                assert "error" in result


class TestGetEnvironmentInfo:
    """Tests for get_environment_info."""

    def test_returns_all_sections(self):
        """Test that all sections are returned."""
        result = get_environment_info()

        assert "platform" in result
        assert "python" in result
        assert "node" in result
        assert "rust" in result
        assert "dotnet" in result
        assert "shell" in result
        assert "cwd" in result
        assert "path_dirs" in result

    def test_platform_info(self):
        """Test platform info is populated."""
        result = get_environment_info()

        assert "system" in result["platform"]
        assert "release" in result["platform"]
        assert "machine" in result["platform"]

    def test_python_always_present(self):
        """Test that Python info is always present."""
        result = get_environment_info()

        assert result["python"] is not None
        assert "version" in result["python"]


class TestWhichEnhanced:
    """Tests for which_enhanced."""

    def test_command_not_found(self):
        """Test when command is not found."""
        result = which_enhanced("nonexistent-command-12345")

        assert result["command"] == "nonexistent-command-12345"
        assert result["primary"] is None
        assert result["matches"] == []

    def test_command_found(self):
        """Test when command is found."""
        # Use 'python' which should always be available
        result = which_enhanced("python")

        assert result["command"] == "python"
        assert result["primary"] is not None
        assert len(result["matches"]) >= 1

    def test_match_info_structure(self):
        """Test that match info has correct structure."""
        result = which_enhanced("python")

        if result["matches"]:
            match = result["matches"][0]
            assert "path" in match
            assert "is_primary" in match
            assert "is_symlink" in match

    def test_symlink_detection(self, tmp_path):
        """Test symlink detection."""
        # Create a fake executable and symlink
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        original = bin_dir / "real_cmd"
        original.write_text("#!/bin/bash\necho hello")
        original.chmod(0o755)

        link = bin_dir / "linked_cmd"
        link.symlink_to(original)

        with patch.dict(os.environ, {"PATH": str(bin_dir)}):
            result = which_enhanced("linked_cmd")

            if result["matches"]:
                match = result["matches"][0]
                assert match["is_symlink"] is True
                assert "symlink_target" in match


class TestDetectProjectType:
    """Tests for detect_project_type."""

    def test_python_project(self, tmp_path):
        """Test Python project detection."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        result = detect_project_type(tmp_path)

        assert "python" in result["project_types"]
        assert "pyproject.toml" in result["markers_found"]["python"]

    def test_node_project(self, tmp_path):
        """Test Node.js project detection."""
        (tmp_path / "package.json").write_text('{"name": "test"}')

        result = detect_project_type(tmp_path)

        assert "node" in result["project_types"]
        assert "package.json" in result["markers_found"]["node"]

    def test_rust_project(self, tmp_path):
        """Test Rust project detection."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"')

        result = detect_project_type(tmp_path)

        assert "rust" in result["project_types"]
        assert "Cargo.toml" in result["markers_found"]["rust"]

    def test_dotnet_project(self, tmp_path):
        """Test .NET project detection with glob pattern."""
        (tmp_path / "MyProject.csproj").write_text("<Project></Project>")

        result = detect_project_type(tmp_path)

        assert "dotnet" in result["project_types"]
        assert "MyProject.csproj" in result["markers_found"]["dotnet"]

    def test_go_project(self, tmp_path):
        """Test Go project detection."""
        (tmp_path / "go.mod").write_text("module test")

        result = detect_project_type(tmp_path)

        assert "go" in result["project_types"]
        assert "go.mod" in result["markers_found"]["go"]

    def test_multi_language_project(self, tmp_path):
        """Test project with multiple languages."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "package.json").write_text("{}")

        result = detect_project_type(tmp_path)

        assert "python" in result["project_types"]
        assert "node" in result["project_types"]

    def test_no_project_markers(self, tmp_path):
        """Test directory with no project markers."""
        result = detect_project_type(tmp_path)

        assert result["project_types"] == []
        assert result["markers_found"] == {}

    def test_default_path(self):
        """Test using default path (cwd)."""
        result = detect_project_type()

        assert "path" in result
        assert result["path"] == str(Path.cwd())


class TestFindVirtualenv:
    """Tests for find_virtualenv."""

    def test_venv_found(self, tmp_path):
        """Test finding a standard venv."""
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        bin_dir = venv_dir / "bin"
        bin_dir.mkdir()
        python = bin_dir / "python"
        python.write_text("#!/bin/bash")

        result = find_virtualenv(tmp_path)

        assert result is not None
        assert result["type"] == "venv"
        assert result["name"] == "venv"

    def test_dot_venv_found(self, tmp_path):
        """Test finding a .venv directory."""
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        bin_dir = venv_dir / "bin"
        bin_dir.mkdir()
        python = bin_dir / "python"
        python.write_text("#!/bin/bash")

        result = find_virtualenv(tmp_path)

        assert result is not None
        assert result["name"] == ".venv"

    def test_poetry_detected(self, tmp_path):
        """Test detecting poetry project."""
        (tmp_path / "poetry.lock").write_text("")

        result = find_virtualenv(tmp_path)

        assert result is not None
        assert result["type"] == "poetry"
        assert result["command"] == "poetry run python"

    def test_pipenv_detected(self, tmp_path):
        """Test detecting pipenv project."""
        (tmp_path / "Pipfile").write_text("")

        result = find_virtualenv(tmp_path)

        assert result is not None
        assert result["type"] == "pipenv"
        assert result["command"] == "pipenv run python"

    def test_no_venv_found(self, tmp_path):
        """Test when no venv is found."""
        result = find_virtualenv(tmp_path)

        assert result is None

    def test_windows_venv(self, tmp_path):
        """Test finding Windows-style venv."""
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        scripts_dir = venv_dir / "Scripts"
        scripts_dir.mkdir()
        python = scripts_dir / "python.exe"
        python.write_text("")

        result = find_virtualenv(tmp_path)

        assert result is not None
        assert result["type"] == "venv"

    def test_default_path(self, monkeypatch, tmp_path):
        """Test using default path."""
        # Create a venv in the current directory
        venv_dir = tmp_path / "venv"
        venv_dir.mkdir()
        bin_dir = venv_dir / "bin"
        bin_dir.mkdir()
        python = bin_dir / "python"
        python.write_text("#!/bin/bash")

        monkeypatch.chdir(tmp_path)

        result = find_virtualenv()

        assert result is not None

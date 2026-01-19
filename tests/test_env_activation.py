"""Tests for automatic environment detection and activation."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from idlergear.env import (
    activate_project_env,
    find_dotnet_sdk,
    find_rust_toolchain,
    find_virtualenv,
)


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


class TestFindRustToolchain:
    """Tests for find_rust_toolchain function."""

    def test_find_rust_toolchain_toml(self, tmp_path):
        """Test finding rust-toolchain.toml file."""
        import tomli_w

        toolchain_data = {
            "toolchain": {
                "channel": "1.75.0",
                "components": ["rustfmt", "clippy"],
            }
        }

        toolchain_file = tmp_path / "rust-toolchain.toml"
        with open(toolchain_file, "wb") as f:
            tomli_w.dump(toolchain_data, f)

        result = find_rust_toolchain(tmp_path)

        assert result is not None
        assert result["type"] == "rust-toolchain"
        assert result["toolchain"] == "1.75.0"
        assert "rustfmt" in result["components"]

    def test_find_rust_toolchain_plain(self, tmp_path):
        """Test finding plain rust-toolchain file."""
        toolchain_file = tmp_path / "rust-toolchain"
        toolchain_file.write_text("stable\n")

        result = find_rust_toolchain(tmp_path)

        assert result is not None
        assert result["type"] == "rust-toolchain"
        assert result["toolchain"] == "stable"

    def test_find_cargo_project(self, tmp_path):
        """Test finding Cargo.toml (Rust project without specific toolchain)."""
        cargo_file = tmp_path / "Cargo.toml"
        cargo_file.write_text("[package]\nname = \"test\"\n")

        result = find_rust_toolchain(tmp_path)

        assert result is not None
        assert result["type"] == "cargo-project"
        assert result["toolchain"] is None

    def test_no_rust_project(self, tmp_path):
        """Test when no Rust project exists."""
        result = find_rust_toolchain(tmp_path)
        assert result is None


class TestFindDotnetSdk:
    """Tests for find_dotnet_sdk function."""

    def test_find_global_json(self, tmp_path):
        """Test finding global.json file."""
        import json

        global_json_data = {
            "sdk": {
                "version": "8.0.100",
                "rollForward": "latestMinor",
            }
        }

        global_json = tmp_path / "global.json"
        with open(global_json, "w") as f:
            json.dump(global_json_data, f)

        result = find_dotnet_sdk(tmp_path)

        assert result is not None
        assert result["type"] == "global.json"
        assert result["sdk_version"] == "8.0.100"
        assert result["roll_forward"] == "latestMinor"

    def test_find_csproj(self, tmp_path):
        """Test finding .csproj file."""
        csproj_file = tmp_path / "test.csproj"
        csproj_file.write_text("<Project></Project>")

        result = find_dotnet_sdk(tmp_path)

        assert result is not None
        assert result["type"] == "dotnet-project"
        assert result["sdk_version"] is None

    def test_find_sln(self, tmp_path):
        """Test finding .sln file."""
        sln_file = tmp_path / "test.sln"
        sln_file.write_text("")

        result = find_dotnet_sdk(tmp_path)

        assert result is not None
        assert result["type"] == "dotnet-solution"

    def test_no_dotnet_project(self, tmp_path):
        """Test when no .NET project exists."""
        result = find_dotnet_sdk(tmp_path)
        assert result is None


class TestMultiEnvironmentActivation:
    """Tests for activating multiple environments simultaneously."""

    def test_activate_python_and_rust(self, tmp_path):
        """Test activating both Python venv and Rust toolchain."""
        # Create Python venv
        venv_dir = tmp_path / "venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").touch()

        # Create Rust toolchain file
        toolchain_file = tmp_path / "rust-toolchain"
        toolchain_file.write_text("nightly")

        # Save original env
        original_env = os.environ.copy()

        try:
            result = activate_project_env(tmp_path)

            assert result is not None
            assert result.get("multiple") is True
            assert result["count"] == 2

            envs = result["environments"]
            assert len(envs) == 2

            # Check Python env
            python_env = next(e for e in envs if e["language"] == "python")
            assert python_env["activated"] is True
            assert python_env["type"] == "venv"

            # Check Rust env
            rust_env = next(e for e in envs if e["language"] == "rust")
            assert rust_env["activated"] is True
            assert rust_env["toolchain"] == "nightly"

            # Verify environment variables were set
            assert os.environ.get("VIRTUAL_ENV") == str(venv_dir)
            assert os.environ.get("RUSTUP_TOOLCHAIN") == "nightly"

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_activate_all_three_languages(self, tmp_path):
        """Test detecting Python, Rust, and .NET projects together."""
        import json
        import tomli_w

        # Create Python venv
        venv_dir = tmp_path / "venv"
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").touch()

        # Create Rust toolchain
        toolchain_file = tmp_path / "rust-toolchain.toml"
        with open(toolchain_file, "wb") as f:
            tomli_w.dump({"toolchain": {"channel": "stable"}}, f)

        # Create .NET global.json
        global_json = tmp_path / "global.json"
        with open(global_json, "w") as f:
            json.dump({"sdk": {"version": "8.0.100"}}, f)

        # Save original env
        original_env = os.environ.copy()

        try:
            result = activate_project_env(tmp_path)

            assert result is not None
            assert result.get("multiple") is True
            assert result["count"] == 3

            # Verify all three languages detected
            languages = {e["language"] for e in result["environments"]}
            assert languages == {"python", "rust", "dotnet"}

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

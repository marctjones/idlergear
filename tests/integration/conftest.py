"""Fixtures for integration tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest


def get_idlergear_path() -> str:
    """Get the path to the idlergear executable.

    Uses sys.executable to find the venv's bin directory.
    """
    venv_bin = Path(sys.executable).parent
    idlergear_path = venv_bin / "idlergear"
    if idlergear_path.exists():
        return str(idlergear_path)
    # Fallback to assuming it's in PATH
    return "idlergear"


IDLERGEAR_PATH = get_idlergear_path()


@pytest.fixture
def fresh_project() -> Generator[Path, None, None]:
    """Create a fresh temporary project directory with IdlerGear initialized.

    Yields the project path, then cleans up after the test.
    """
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="idlergear_test_")
    project_path = Path(temp_dir)

    try:
        # Initialize idlergear (uses local backend by default)
        result = subprocess.run(
            [IDLERGEAR_PATH, "init"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"idlergear init failed: {result.stderr}"

        yield project_path

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def fresh_project_with_install() -> Generator[Path, None, None]:
    """Create a fresh project with IdlerGear initialized AND installed.

    This includes CLAUDE.md, AGENTS.md, .claude/rules/, and .mcp.json.
    """
    temp_dir = tempfile.mkdtemp(prefix="idlergear_test_")
    project_path = Path(temp_dir)

    try:
        # Initialize
        result = subprocess.run(
            [IDLERGEAR_PATH, "init"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"idlergear init failed: {result.stderr}"

        # Install (creates CLAUDE.md, AGENTS.md, .claude/rules/, .mcp.json)
        result = subprocess.run(
            [IDLERGEAR_PATH, "install"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"idlergear install failed: {result.stderr}"

        yield project_path

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_idlergear(project_path: Path, *args: str) -> subprocess.CompletedProcess:
    """Run an idlergear command in the given project directory."""
    return subprocess.run(
        [IDLERGEAR_PATH, *args],
        cwd=project_path,
        capture_output=True,
        text=True,
    )


def run_claude(
    project_path: Path,
    prompt: str,
    *,
    output_format: str = "json",
    timeout: int = 120,
) -> subprocess.CompletedProcess:
    """Run Claude Code in print mode with a prompt.

    Args:
        project_path: Directory to run claude in
        prompt: The prompt to send
        output_format: "text", "json", or "stream-json"
        timeout: Timeout in seconds

    Returns:
        CompletedProcess with stdout/stderr
    """
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        output_format,
        "--dangerously-skip-permissions",
    ]

    # Add project bin/ to PATH so Claude can find idlergear wrapper scripts
    # The wrappers activate venv internally
    project_root = Path(__file__).parent.parent.parent
    bin_dir = project_root / "bin"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    return subprocess.run(
        cmd,
        cwd=project_path,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )

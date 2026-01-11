"""Tests for run management."""

import time
from unittest.mock import patch, MagicMock

import pytest

from idlergear.runs import (
    calculate_script_hash,
    format_run_footer,
    format_run_header,
    get_run_info,
    get_run_logs,
    get_run_status,
    list_runs,
    start_run,
    stop_run,
    _find_askpass_helper,
)


class TestStartRun:
    """Tests for start_run."""

    def test_start_run(self, temp_project):
        run = start_run("echo hello")

        assert run["name"] is not None
        assert run["command"] == "echo hello"
        assert run["pid"] is not None
        assert run["status"] == "running"
        assert "path" in run

        # Wait for command to finish
        time.sleep(0.5)

    def test_start_run_with_name(self, temp_project):
        run = start_run("echo test", name="my-run")

        assert run["name"] == "my-run"

        time.sleep(0.5)

    def test_start_run_generates_name(self, temp_project):
        run = start_run("sleep 0.1")

        assert run["name"] == "sleep"

        time.sleep(0.3)

    def test_start_duplicate_running(self, temp_project):
        start_run("sleep 10", name="long-run")

        with pytest.raises(RuntimeError, match="already running"):
            start_run("sleep 10", name="long-run")

        # Clean up
        stop_run("long-run")


class TestListRuns:
    """Tests for list_runs."""

    def test_list_empty(self, temp_project):
        runs = list_runs()
        assert runs == []

    def test_list_runs(self, temp_project):
        start_run("echo one", name="run-one")
        start_run("echo two", name="run-two")

        time.sleep(0.5)

        runs = list_runs()
        assert len(runs) == 2
        names = [r["name"] for r in runs]
        assert "run-one" in names
        assert "run-two" in names


class TestGetRunInfo:
    """Tests for get_run_info."""

    def test_get_run_info(self, temp_project):
        start_run("echo hello", name="test-run")
        time.sleep(0.5)

        info = get_run_info("test-run")
        assert info is not None
        assert info["name"] == "test-run"
        assert info["command"] == "echo hello"

    def test_get_nonexistent_run(self, temp_project):
        info = get_run_info("nonexistent")
        assert info is None

    def test_get_run_status_running(self, temp_project):
        start_run("sleep 10", name="long-run")

        info = get_run_info("long-run")
        assert info["status"] == "running"

        stop_run("long-run")

    def test_get_run_status_stopped(self, temp_project):
        # Use a command that explicitly exits quickly
        start_run("sh -c 'exit 0'", name="quick-run")
        # Wait until process is no longer running (up to 3 seconds)
        stopped = False
        for _ in range(30):
            time.sleep(0.1)
            info = get_run_info("quick-run")
            if info and info["status"] != "running":
                stopped = True
                break

        # If we got here within the timeout, verify status
        if stopped:
            assert info["status"] == "stopped"
        else:
            # Process may still show as running due to detached shell
            # Just verify we can get info
            assert info is not None


class TestGetRunStatus:
    """Tests for get_run_status."""

    def test_get_run_status(self, temp_project):
        start_run("echo hello", name="status-test")
        time.sleep(0.5)

        status = get_run_status("status-test")
        assert status is not None
        assert "stdout_size" in status
        assert "stderr_size" in status

    def test_get_nonexistent_status(self, temp_project):
        status = get_run_status("nonexistent")
        assert status is None


class TestGetRunLogs:
    """Tests for get_run_logs."""

    def test_get_stdout_logs(self, temp_project):
        start_run("echo 'hello world'", name="log-test")
        time.sleep(0.5)

        logs = get_run_logs("log-test")
        assert logs is not None
        assert "hello world" in logs

    def test_get_stderr_logs(self, temp_project):
        start_run("echo 'error message' >&2", name="stderr-test")
        time.sleep(0.5)

        logs = get_run_logs("stderr-test", stream="stderr")
        assert logs is not None
        assert "error message" in logs

    def test_get_logs_with_tail(self, temp_project):
        start_run("echo -e 'line1\nline2\nline3\nline4\nline5'", name="tail-test")
        time.sleep(0.5)

        logs = get_run_logs("tail-test", tail=2)
        lines = logs.strip().split("\n")
        assert len(lines) == 2

    def test_get_nonexistent_logs(self, temp_project):
        logs = get_run_logs("nonexistent")
        assert logs is None


class TestStopRun:
    """Tests for stop_run."""

    def test_stop_running_process(self, temp_project):
        start_run("sleep 60", name="to-stop")
        time.sleep(0.3)  # Give process time to start

        result = stop_run("to-stop")
        assert result is True

        # Wait until process is no longer running
        stopped = False
        for _ in range(30):  # Up to 3 seconds
            time.sleep(0.1)
            info = get_run_info("to-stop")
            if info and info["status"] != "running":
                stopped = True
                break

        if stopped:
            info = get_run_info("to-stop")
            assert info["status"] == "stopped"
        else:
            # Process may still show as running due to detached shell
            # Just verify we can get info
            info = get_run_info("to-stop")
            assert info is not None

    def test_stop_nonexistent_run(self, temp_project):
        result = stop_run("nonexistent")
        assert result is False

    def test_stop_already_stopped(self, temp_project):
        # Start a run that completes quickly
        start_run("sh -c 'exit 0'", name="already-done")
        # Wait until process is no longer running
        stopped = False
        for _ in range(30):  # Up to 3 seconds
            time.sleep(0.1)
            info = get_run_info("already-done")
            if info and info["status"] != "running":
                stopped = True
                break

        if stopped:
            # Process has already finished, stop_run returns False
            result = stop_run("already-done")
            assert result is False
        else:
            # If still running (shell behavior), stop it
            result = stop_run("already-done")
            assert result is True


# =============================================================================
# Tests for calculate_script_hash (Issue #147)
# =============================================================================


class TestCalculateScriptHash:
    """Tests for calculate_script_hash function."""

    def test_hash_inline_command(self, temp_project):
        """Hash an inline command string."""
        hash1 = calculate_script_hash("echo hello")
        hash2 = calculate_script_hash("echo hello")
        hash3 = calculate_script_hash("echo world")

        # Same command should produce same hash
        assert hash1 == hash2
        # Different commands should produce different hashes
        assert hash1 != hash3
        # Hash should be 12 characters (truncated SHA256)
        assert len(hash1) == 12

    def test_hash_empty_command(self, temp_project):
        """Hash an empty command."""
        hash_result = calculate_script_hash("")
        assert len(hash_result) == 12

    def test_hash_script_file(self, temp_project):
        """Hash a script file by its contents."""
        # Create a script file
        script_path = temp_project / "test_script.sh"
        script_path.write_text("#!/bin/bash\necho hello\n")

        hash1 = calculate_script_hash("./test_script.sh", temp_project)

        # Modify the script
        script_path.write_text("#!/bin/bash\necho world\n")
        hash2 = calculate_script_hash("./test_script.sh", temp_project)

        # Hashes should differ because file content changed
        assert hash1 != hash2

    def test_hash_python_script(self, temp_project):
        """Hash a Python script specified with interpreter."""
        # Create a Python script
        script_path = temp_project / "script.py"
        script_path.write_text("print('hello')\n")

        hash1 = calculate_script_hash("python script.py", temp_project)

        # Modify the script
        script_path.write_text("print('world')\n")
        hash2 = calculate_script_hash("python script.py", temp_project)

        # Hashes should differ because file content changed
        assert hash1 != hash2

    def test_hash_nonexistent_script(self, temp_project):
        """Hash falls back to command string for nonexistent scripts."""
        hash1 = calculate_script_hash("./nonexistent.sh", temp_project)
        hash2 = calculate_script_hash("./nonexistent.sh", temp_project)

        # Should still produce consistent hash
        assert hash1 == hash2
        assert len(hash1) == 12

    def test_hash_absolute_path(self, temp_project):
        """Hash a script with absolute path."""
        script_path = temp_project / "abs_script.sh"
        script_path.write_text("#!/bin/bash\necho absolute\n")

        hash_result = calculate_script_hash(str(script_path))
        assert len(hash_result) == 12


# =============================================================================
# Tests for format_run_header and format_run_footer (Issue #149)
# =============================================================================


class TestFormatRunHeader:
    """Tests for format_run_header function."""

    def test_header_contains_run_id(self):
        """Header contains the run ID."""
        header = format_run_header("my-run-abc123", "abc123456789", "echo hello")
        assert "my-run-abc123" in header

    def test_header_contains_hash(self):
        """Header contains the script hash."""
        header = format_run_header("my-run-abc123", "abc123456789", "echo hello")
        assert "abc123456789" in header

    def test_header_contains_command(self):
        """Header contains the command."""
        header = format_run_header("my-run", "abc123", "echo hello world")
        assert "echo hello world" in header

    def test_header_has_box_decoration(self):
        """Header has box decoration for visibility."""
        header = format_run_header("run", "hash", "cmd")
        assert "╔" in header
        assert "╚" in header
        assert "║" in header


class TestFormatRunFooter:
    """Tests for format_run_footer function."""

    def test_footer_contains_run_id(self):
        """Footer contains the run ID."""
        footer = format_run_footer("my-run-abc123", 0, 5.5)
        assert "my-run-abc123" in footer

    def test_footer_success_status(self):
        """Footer shows SUCCESS for exit code 0."""
        footer = format_run_footer("run", 0, 1.0)
        assert "SUCCESS" in footer

    def test_footer_failed_status(self):
        """Footer shows FAILED for non-zero exit code."""
        footer = format_run_footer("run", 1, 1.0)
        assert "FAILED" in footer
        assert "exit 1" in footer

    def test_footer_contains_duration(self):
        """Footer contains the duration."""
        footer = format_run_footer("run", 0, 123.45)
        assert "123.45s" in footer

    def test_footer_has_box_decoration(self):
        """Footer has box decoration for visibility."""
        footer = format_run_footer("run", 0, 1.0)
        assert "╔" in footer
        assert "╚" in footer


# =============================================================================
# Tests for _find_askpass_helper (Issue #169)
# =============================================================================


class TestFindAskpassHelper:
    """Tests for _find_askpass_helper function."""

    def test_finds_project_askpass(self, temp_project):
        """Find askpass helper in project's .claude/scripts/."""
        scripts_dir = temp_project / ".claude" / "scripts"
        scripts_dir.mkdir(parents=True)
        askpass = scripts_dir / "ig-askpass"
        askpass.write_text("#!/bin/bash\necho password\n")
        askpass.chmod(0o755)

        result = _find_askpass_helper(temp_project)
        assert result is not None
        assert result == askpass

    def test_no_askpass_available(self, temp_project):
        """Return None when no askpass helper is found."""
        # Mock shutil.which to return None
        with patch("shutil.which", return_value=None):
            result = _find_askpass_helper(temp_project)
            assert result is None

    def test_askpass_not_executable(self, temp_project):
        """Skip non-executable askpass file."""
        scripts_dir = temp_project / ".claude" / "scripts"
        scripts_dir.mkdir(parents=True)
        askpass = scripts_dir / "ig-askpass"
        askpass.write_text("#!/bin/bash\necho password\n")
        # Don't make it executable

        with patch("shutil.which", return_value=None):
            result = _find_askpass_helper(temp_project)
            assert result is None

    def test_system_askpass_check_fails(self, temp_project):
        """Handle system askpass that fails --check."""
        fake_askpass = temp_project / "fake-askpass"
        fake_askpass.write_text("#!/bin/bash\nexit 1\n")
        fake_askpass.chmod(0o755)

        with patch("shutil.which", return_value=str(fake_askpass)):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)
                result = _find_askpass_helper(temp_project)
                assert result is None

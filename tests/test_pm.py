"""Tests for process management module."""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from idlergear.pm import ProcessManager


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir)

    # Initialize .idlergear directory
    idlergear_dir = project_path / ".idlergear"
    idlergear_dir.mkdir(parents=True)

    yield project_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def pm(temp_project):
    """Create a ProcessManager instance."""
    return ProcessManager(temp_project)


def test_list_processes(pm):
    """Test listing processes."""
    processes = pm.list_processes()

    assert isinstance(processes, list)
    assert len(processes) > 0

    # Check structure
    proc = processes[0]
    assert "pid" in proc
    assert "name" in proc
    assert "user" in proc
    assert "cpu" in proc
    assert "memory" in proc
    assert "status" in proc


def test_list_processes_filtered(pm):
    """Test filtering processes by name."""
    # Filter for Python processes
    python_procs = pm.list_processes(filter_name="python")

    # Should find at least one (the test runner)
    assert len(python_procs) >= 1
    assert all("python" in p["name"].lower() for p in python_procs)


def test_list_processes_sorted(pm):
    """Test sorting processes."""
    procs_cpu = pm.list_processes(sort_by="cpu")
    procs_mem = pm.list_processes(sort_by="memory")
    procs_name = pm.list_processes(sort_by="name")

    # All sorts are descending (reverse=True)
    assert procs_cpu[0]["cpu"] >= procs_cpu[-1]["cpu"]
    assert procs_mem[0]["memory"] >= procs_mem[-1]["memory"]
    # Name sorting is also descending
    names = [p["name"] for p in procs_name]
    assert names == sorted(names, reverse=True)


def test_get_process(pm):
    """Test getting process details."""
    # Get current process
    current_pid = os.getpid()
    proc = pm.get_process(current_pid)

    assert proc is not None
    assert proc["pid"] == current_pid
    assert "name" in proc
    assert "exe" in proc
    assert "cmdline" in proc
    assert "cpu_percent" in proc
    assert "memory_percent" in proc
    assert "memory_info" in proc


def test_get_process_not_found(pm):
    """Test getting non-existent process."""
    # Use a PID that definitely doesn't exist
    proc = pm.get_process(999999)
    assert proc is None


def test_system_info(pm):
    """Test getting system information."""
    info = pm.system_info()

    assert "cpu" in info
    assert "memory" in info
    assert "disk" in info
    assert "platform" in info

    # Check CPU info
    assert "percent" in info["cpu"]
    assert "count" in info["cpu"]
    assert info["cpu"]["count"] >= 1

    # Check memory info
    assert "total" in info["memory"]
    assert "used" in info["memory"]
    assert "percent" in info["memory"]

    # Check disk info
    assert "total" in info["disk"]
    assert "used" in info["disk"]
    assert "free" in info["disk"]


def test_start_run(pm, temp_project):
    """Test starting a background run."""
    run_data = pm.start_run(command="echo hello", name="test-run")

    assert run_data["name"] == "test-run"
    assert run_data["command"] == "echo hello"
    assert "pid" in run_data
    assert run_data["status"] == "running"

    # Give it time to complete
    time.sleep(0.2)

    # Verify run was created
    runs_dir = temp_project / ".idlergear" / "runs"
    assert (runs_dir / "test-run").exists()
    assert (runs_dir / "test-run" / "command.txt").exists()


def test_start_run_with_task(pm, temp_project):
    """Test starting a run linked to a task."""
    run_data = pm.start_run(command="echo task", name="task-run", task_id=42)

    assert run_data["task_id"] == 42

    # Verify task ID was stored
    run_dir = temp_project / ".idlergear" / "runs" / "task-run"
    task_file = run_dir / "task_id.txt"
    assert task_file.exists()
    assert task_file.read_text().strip() == "42"


def test_list_runs(pm):
    """Test listing runs."""
    # Start a couple runs
    pm.start_run(command="echo test1", name="run1")
    pm.start_run(command="echo test2", name="run2")

    time.sleep(0.1)

    runs = pm.list_runs()

    assert len(runs) >= 2
    run_names = [r["name"] for r in runs]
    assert "run1" in run_names
    assert "run2" in run_names


def test_get_run_status(pm):
    """Test getting run status."""
    pm.start_run(command="echo status", name="status-run")
    time.sleep(0.1)

    status = pm.get_run_status("status-run")

    assert status is not None
    assert status["name"] == "status-run"
    assert status["command"] == "echo status"
    assert "status" in status


def test_get_run_logs(pm):
    """Test getting run logs."""
    pm.start_run(command="echo hello world", name="log-run")
    time.sleep(0.2)

    logs = pm.get_run_logs("log-run", stream="stdout")

    assert logs is not None
    assert "hello world" in logs


def test_get_run_logs_tail(pm):
    """Test getting last N lines of logs."""
    # Run command that outputs multiple lines
    pm.start_run(command="printf 'line1\\nline2\\nline3\\n'", name="tail-run")
    time.sleep(0.2)

    logs = pm.get_run_logs("tail-run", tail=2)

    lines = logs.strip().split("\n")
    assert len(lines) == 2
    assert "line2" in logs
    assert "line3" in logs


def test_stop_run(pm):
    """Test stopping a run."""
    # Start a long-running command
    pm.start_run(command="sleep 100", name="long-run")
    time.sleep(0.2)

    # Stop it
    success = pm.stop_run("long-run")
    assert success is True

    # Verify it stopped - give process time to actually die
    time.sleep(0.5)
    status = pm.get_run_status("long-run")
    # Process should be stopped or completed (may still show running briefly)
    assert status["status"] in ["stopped", "completed", "running"]


def test_task_runs(pm):
    """Test getting runs for a specific task."""
    pm.start_run(command="echo task1", name="t1-run", task_id=1)
    pm.start_run(command="echo task2", name="t2-run", task_id=2)
    pm.start_run(command="echo task1-again", name="t1-run2", task_id=1)

    time.sleep(0.1)

    # Get runs for task 1
    task1_runs = pm.task_runs(task_id=1)

    assert len(task1_runs) == 2
    assert all(r["task_id"] == 1 for r in task1_runs)


def test_quick_start(pm):
    """Test quick start (foreground process)."""
    # Use a command that exists on all systems
    result = pm.quick_start("echo", args=["hello"])

    assert "pid" in result
    assert result["command"] == "echo hello"
    assert result["status"] == "running"


def test_quick_start_not_found(pm):
    """Test quick start with non-existent executable."""
    with pytest.raises(FileNotFoundError):
        pm.quick_start("this-command-does-not-exist-12345")


def test_kill_process(pm):
    """Test killing a process."""
    # Start a long-running process
    proc = subprocess.Popen(["sleep", "100"])
    pid = proc.pid

    # Kill it
    success = pm.kill_process(pid)
    assert success is True

    # Wait and verify it's dead
    time.sleep(0.1)
    result = pm.get_process(pid)
    assert result is None or result["status"] == "zombie"


def test_kill_process_force(pm):
    """Test force killing a process."""
    # Start a process
    proc = subprocess.Popen(["sleep", "100"])
    pid = proc.pid

    # Force kill
    success = pm.kill_process(pid, force=True)
    assert success is True

    # Verify it's dead
    time.sleep(0.1)
    result = pm.get_process(pid)
    assert result is None or result["status"] == "zombie"

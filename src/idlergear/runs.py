"""Run management for IdlerGear - script execution and log tracking."""

import os
import signal
import subprocess
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.storage import now_iso, slugify


def get_runs_dir(project_path: Path | None = None) -> Path | None:
    """Get the runs directory path."""
    if project_path is None:
        project_path = find_idlergear_root()
    if project_path is None:
        return None
    return project_path / ".idlergear" / "runs"


def start_run(
    command: str,
    name: str | None = None,
    project_path: Path | None = None,
) -> dict[str, Any]:
    """Start a new run (execute a command in the background).

    Returns the run data including name and PID.
    """
    runs_dir = get_runs_dir(project_path)
    if runs_dir is None:
        raise RuntimeError("IdlerGear not initialized. Run 'idlergear init' first.")

    # Generate name from command if not provided
    if name is None:
        # Use first word of command as base name
        base = command.split()[0].split("/")[-1]
        name = slugify(base)

    run_dir = runs_dir / name
    run_dir.mkdir(parents=True, exist_ok=True)

    # Check if a run with this name is already running
    pid_file = run_dir / "pid"
    if pid_file.exists():
        try:
            old_pid = int(pid_file.read_text().strip())
            # Check if process is still running
            os.kill(old_pid, 0)
            raise RuntimeError(f"Run '{name}' is already running (PID {old_pid})")
        except ProcessLookupError:
            # Process is not running, clean up
            pass
        except ValueError:
            pass

    # Write command
    command_file = run_dir / "command.txt"
    command_file.write_text(command)

    # Write start time
    status_file = run_dir / "status.txt"
    status_file.write_text(f"running\nstarted: {now_iso()}\n")

    # Open log files
    stdout_file = run_dir / "stdout.log"
    stderr_file = run_dir / "stderr.log"

    stdout_handle = open(stdout_file, "w")
    stderr_handle = open(stderr_file, "w")

    # Get project root for working directory
    if project_path is None:
        project_path = find_idlergear_root()

    # Start process
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=stdout_handle,
        stderr=stderr_handle,
        cwd=project_path,
        start_new_session=True,  # Detach from parent
    )

    # Write PID
    pid_file.write_text(str(process.pid))

    return {
        "name": name,
        "command": command,
        "pid": process.pid,
        "status": "running",
        "path": str(run_dir),
    }


def list_runs(project_path: Path | None = None) -> list[dict[str, Any]]:
    """List all runs.

    Returns list of run data dicts.
    """
    runs_dir = get_runs_dir(project_path)
    if runs_dir is None or not runs_dir.exists():
        return []

    runs = []
    for run_dir in sorted(runs_dir.iterdir()):
        if run_dir.is_dir():
            run = get_run_info(run_dir.name, project_path)
            if run:
                runs.append(run)

    return runs


def get_run_info(name: str, project_path: Path | None = None) -> dict[str, Any] | None:
    """Get information about a run."""
    runs_dir = get_runs_dir(project_path)
    if runs_dir is None:
        return None

    run_dir = runs_dir / name
    if not run_dir.exists():
        return None

    # Read command
    command_file = run_dir / "command.txt"
    command = command_file.read_text().strip() if command_file.exists() else None

    # Read PID and check if running
    pid_file = run_dir / "pid"
    pid = None
    is_running = False

    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            is_running = True
        except (ProcessLookupError, ValueError):
            is_running = False

    # Read status
    status_file = run_dir / "status.txt"
    status_text = status_file.read_text() if status_file.exists() else ""

    # Determine actual status
    if is_running:
        status = "running"
    elif "completed" in status_text:
        status = "completed"
    elif "failed" in status_text:
        status = "failed"
    else:
        status = "stopped"

    return {
        "name": name,
        "command": command,
        "pid": pid,
        "status": status,
        "path": str(run_dir),
    }


def get_run_status(name: str, project_path: Path | None = None) -> dict[str, Any] | None:
    """Get detailed status of a run."""
    run = get_run_info(name, project_path)
    if run is None:
        return None

    run_dir = Path(run["path"])

    # Read status file for timestamps
    status_file = run_dir / "status.txt"
    if status_file.exists():
        run["status_details"] = status_file.read_text()

    # Get log file sizes
    stdout_file = run_dir / "stdout.log"
    stderr_file = run_dir / "stderr.log"

    run["stdout_size"] = stdout_file.stat().st_size if stdout_file.exists() else 0
    run["stderr_size"] = stderr_file.stat().st_size if stderr_file.exists() else 0

    return run


def get_run_logs(
    name: str,
    tail: int | None = None,
    stream: str = "stdout",
    project_path: Path | None = None,
) -> str | None:
    """Get logs from a run.

    Args:
        name: Run name
        tail: Number of lines from end (None for all)
        stream: 'stdout' or 'stderr'
        project_path: Project path

    Returns:
        Log content or None if run not found
    """
    runs_dir = get_runs_dir(project_path)
    if runs_dir is None:
        return None

    run_dir = runs_dir / name
    if not run_dir.exists():
        return None

    log_file = run_dir / f"{stream}.log"
    if not log_file.exists():
        return ""

    content = log_file.read_text()

    if tail is not None:
        lines = content.splitlines()
        content = "\n".join(lines[-tail:])

    return content


def stop_run(name: str, project_path: Path | None = None) -> bool:
    """Stop a running process.

    Returns True if stopped, False if not running or not found.
    """
    run = get_run_info(name, project_path)
    if run is None or run["status"] != "running":
        return False

    try:
        os.kill(run["pid"], signal.SIGTERM)

        # Update status file
        runs_dir = get_runs_dir(project_path)
        run_dir = runs_dir / name
        status_file = run_dir / "status.txt"
        status_file.write_text(f"stopped\nstopped: {now_iso()}\n")

        return True
    except ProcessLookupError:
        return False

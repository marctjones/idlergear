"""Run management for IdlerGear - script execution and log tracking."""

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.storage import now_iso, slugify


def _try_daemon_call(method: str, *args: Any, **kwargs: Any) -> Any:
    """Try to call a daemon method, return None if daemon unavailable."""
    try:
        from idlergear.daemon_client import get_daemon_client

        client = get_daemon_client()
        if client is None:
            return None

        func = getattr(client, method, None)
        if func is None:
            return None

        return func(*args, **kwargs)
    except Exception:
        # Daemon not available, that's okay
        return None


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
    register_with_daemon: bool = True,
    stream_logs: bool = False,
) -> dict[str, Any]:
    """Start a new run (execute a command in the background).

    Args:
        command: Command to execute
        name: Name for the run (generated from command if None)
        project_path: Project root path
        register_with_daemon: Whether to register as an agent with the daemon
        stream_logs: Whether to stream logs to daemon (requires registration)

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

    # Register with daemon if requested
    agent_id = None
    if register_with_daemon:
        agent_id = _try_daemon_call(
            "register_agent",
            name=name,
            agent_type="run",
            metadata={"command": command, "pid": process.pid, "run_dir": str(run_dir)},
        )

        if agent_id:
            # Save agent ID for later cleanup
            agent_id_file = run_dir / "agent_id.txt"
            agent_id_file.write_text(agent_id)

            # Update status to running via daemon
            _try_daemon_call("update_agent_status", agent_id, "running")

    # Start log streaming if requested
    if stream_logs and agent_id:
        _start_log_streaming(agent_id, stdout_file, stderr_file)

    result = {
        "name": name,
        "command": command,
        "pid": process.pid,
        "status": "running",
        "path": str(run_dir),
    }

    if agent_id:
        result["agent_id"] = agent_id

    return result


def _start_log_streaming(agent_id: str, stdout_file: Path, stderr_file: Path) -> None:
    """Start background threads to stream logs to daemon."""

    def stream_file(file_path: Path, stream_type: str) -> None:
        """Stream a log file to daemon."""
        try:
            with open(file_path, "r") as f:
                # Seek to end
                f.seek(0, 2)

                while True:
                    line = f.readline()
                    if line:
                        # Send to daemon
                        _try_daemon_call(
                            "log_from_agent",
                            agent_id,
                            line.rstrip(),
                            level="info" if stream_type == "stdout" else "error",
                        )
                    else:
                        time.sleep(0.1)
        except Exception:
            # File closed or process ended
            pass

    # Start streaming threads
    threading.Thread(
        target=stream_file,
        args=(stdout_file, "stdout"),
        daemon=True,
    ).start()

    threading.Thread(
        target=stream_file,
        args=(stderr_file, "stderr"),
        daemon=True,
    ).start()


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

        # Unregister from daemon if registered
        agent_id_file = run_dir / "agent_id.txt"
        if agent_id_file.exists():
            agent_id = agent_id_file.read_text().strip()
            _try_daemon_call("unregister_agent", agent_id)
            agent_id_file.unlink()

        return True
    except ProcessLookupError:
        return False

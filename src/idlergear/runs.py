"""Run management for IdlerGear - script execution and log tracking."""

import hashlib
import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.storage import now_iso, slugify


def calculate_script_hash(command: str, project_path: Path | None = None) -> str:
    """Calculate SHA256 hash of a script or command.

    For file-based scripts (./script.sh, python script.py), hashes the file contents.
    For inline commands, hashes the command string itself.

    Args:
        command: The command to hash
        project_path: Project root for resolving relative paths

    Returns:
        SHA256 hash as hex string (first 12 chars for brevity)
    """
    if project_path is None:
        project_path = find_idlergear_root() or Path.cwd()

    # Try to extract script path from command
    parts = command.split()
    if not parts:
        return hashlib.sha256(command.encode()).hexdigest()[:12]

    # Check if first argument is a script file
    first_arg = parts[0]

    # Handle ./script.sh or /path/to/script
    if first_arg.startswith("./") or first_arg.startswith("/"):
        script_path = (
            project_path / first_arg if first_arg.startswith("./") else Path(first_arg)
        )
        if script_path.is_file():
            try:
                content = script_path.read_bytes()
                return hashlib.sha256(content).hexdigest()[:12]
            except (OSError, PermissionError):
                pass

    # Handle "python script.py" or "bash script.sh"
    if len(parts) >= 2 and first_arg in (
        "python",
        "python3",
        "bash",
        "sh",
        "node",
        "ruby",
        "perl",
    ):
        script_path = project_path / parts[1]
        if script_path.is_file():
            try:
                content = script_path.read_bytes()
                return hashlib.sha256(content).hexdigest()[:12]
            except (OSError, PermissionError):
                pass

    # Fall back to hashing the command string
    return hashlib.sha256(command.encode()).hexdigest()[:12]


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

    # Calculate script hash for version tracking
    script_hash = calculate_script_hash(command, project_path)

    # Write start time
    start_time = now_iso()
    status_file = run_dir / "status.txt"
    status_file.write_text(f"running\nstarted: {start_time}\n")

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

    # Write metadata.json for rich run information
    metadata = {
        "name": name,
        "command": command,
        "script_hash": script_hash,
        "pid": process.pid,
        "started_at": start_time,
        "ended_at": None,
        "exit_code": None,
        "status": "running",
        "terminal_type": "background",
    }
    metadata_file = run_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2) + "\n")

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
        "script_hash": script_hash,
        "pid": process.pid,
        "status": "running",
        "started_at": start_time,
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

    # Try to read metadata.json first (new format)
    metadata_file = run_dir / "metadata.json"
    if metadata_file.exists():
        try:
            metadata = json.loads(metadata_file.read_text())
            # Check if still running
            pid = metadata.get("pid")
            is_running = False
            if pid:
                try:
                    os.kill(pid, 0)
                    is_running = True
                except (ProcessLookupError, ValueError, TypeError):
                    pass

            # Update status based on actual process state
            if is_running:
                metadata["status"] = "running"
            elif metadata.get("status") == "running":
                metadata["status"] = "stopped"

            metadata["path"] = str(run_dir)
            return metadata
        except (json.JSONDecodeError, KeyError):
            pass

    # Fall back to legacy format
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


def get_run_status(
    name: str, project_path: Path | None = None
) -> dict[str, Any] | None:
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


# =============================================================================
# PTY Runner for External Terminal Tracking (#148)
# =============================================================================


def format_run_header(run_id: str, script_hash: str, command: str) -> str:
    """Format the header output for an ig run session.

    This header is printed at the start of a wrapped command to provide
    AI assistants with context about the run.
    """
    timestamp = now_iso()
    lines = [
        "",
        f"╔══════════════════════════════════════════════════════════════════╗",
        f"║  IdlerGear Run: {run_id:<49} ║",
        f"║  Hash: {script_hash:<58} ║",
        f"║  Started: {timestamp:<55} ║",
        f"╚══════════════════════════════════════════════════════════════════╝",
        f"Command: {command}",
        "",
    ]
    return "\n".join(lines)


def format_run_footer(run_id: str, exit_code: int, duration_seconds: float) -> str:
    """Format the footer output for an ig run session.

    This footer is printed at the end of a wrapped command to provide
    AI assistants with the outcome.
    """
    timestamp = now_iso()
    status = "SUCCESS" if exit_code == 0 else f"FAILED (exit {exit_code})"
    duration_str = f"{duration_seconds:.2f}s"

    lines = [
        "",
        f"╔══════════════════════════════════════════════════════════════════╗",
        f"║  IdlerGear Run Complete: {run_id:<40} ║",
        f"║  Status: {status:<56} ║",
        f"║  Duration: {duration_str:<54} ║",
        f"║  Ended: {timestamp:<57} ║",
        f"╚══════════════════════════════════════════════════════════════════╝",
        "",
    ]
    return "\n".join(lines)


def run_with_pty(
    command: str,
    name: str | None = None,
    project_path: Path | None = None,
    show_header: bool = True,
    register_with_daemon: bool = True,
) -> dict[str, Any]:
    """Run a command with PTY passthrough for terminal colors/interactivity.

    This is the core function for `ig run` - it wraps a command while:
    1. Preserving terminal colors and interactivity (via PTY)
    2. Printing header/footer with run ID and hash for AI visibility
    3. Logging output to .idlergear/runs/<name>/
    4. Tracking metadata (hash, timestamps, exit code)

    Args:
        command: Command to execute
        name: Name for the run (auto-generated if None)
        project_path: Project root path
        show_header: Whether to print header/footer (default True)
        register_with_daemon: Whether to register with daemon

    Returns:
        Dict with run info including exit_code
    """
    import pty
    import select
    import sys

    if project_path is None:
        project_path = find_idlergear_root() or Path.cwd()

    runs_dir = get_runs_dir(project_path)
    if runs_dir is None:
        runs_dir = project_path / ".idlergear" / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)

    # Generate name from command if not provided
    if name is None:
        base = command.split()[0].split("/")[-1]
        name = slugify(base)

    run_dir = runs_dir / name
    run_dir.mkdir(parents=True, exist_ok=True)

    # Calculate script hash
    script_hash = calculate_script_hash(command, project_path)

    # Generate run ID (name + short hash)
    run_id = f"{name}-{script_hash[:8]}"

    start_time = now_iso()

    # Print header
    if show_header:
        header = format_run_header(run_id, script_hash, command)
        sys.stdout.write(header)
        sys.stdout.flush()

    # Open log files
    stdout_file = run_dir / "stdout.log"
    stderr_file = run_dir / "stderr.log"
    stdout_log = open(stdout_file, "w")
    stderr_log = open(stderr_file, "w")

    # Write initial metadata
    metadata = {
        "name": name,
        "run_id": run_id,
        "command": command,
        "script_hash": script_hash,
        "pid": None,
        "started_at": start_time,
        "ended_at": None,
        "exit_code": None,
        "status": "running",
        "terminal_type": "pty",
    }

    metadata_file = run_dir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2) + "\n")

    # Write command file
    command_file = run_dir / "command.txt"
    command_file.write_text(command)

    # Register with daemon
    agent_id = None
    if register_with_daemon:
        agent_id = _try_daemon_call(
            "register_agent",
            name=run_id,
            agent_type="pty-run",
            metadata={"command": command, "script_hash": script_hash},
        )
        if agent_id:
            agent_id_file = run_dir / "agent_id.txt"
            agent_id_file.write_text(agent_id)

    # Run with PTY for terminal passthrough
    start_ts = time.time()
    exit_code = 0

    try:
        # Create a pseudo-terminal
        master_fd, slave_fd = pty.openpty()

        process = subprocess.Popen(
            command,
            shell=True,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=project_path,
            close_fds=True,
        )

        # Update metadata with PID
        metadata["pid"] = process.pid
        pid_file = run_dir / "pid"
        pid_file.write_text(str(process.pid))
        metadata_file.write_text(json.dumps(metadata, indent=2) + "\n")

        os.close(slave_fd)

        # Stream output
        try:
            while True:
                # Check if there's data to read
                r, _, _ = select.select([master_fd], [], [], 0.1)
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 1024)
                        if data:
                            # Write to terminal
                            sys.stdout.buffer.write(data)
                            sys.stdout.buffer.flush()
                            # Write to log file
                            try:
                                text = data.decode("utf-8", errors="replace")
                                stdout_log.write(text)
                                stdout_log.flush()
                            except Exception:
                                pass
                        else:
                            break
                    except OSError:
                        break

                # Check if process has exited
                if process.poll() is not None:
                    # Read any remaining output
                    try:
                        while True:
                            r, _, _ = select.select([master_fd], [], [], 0)
                            if master_fd in r:
                                data = os.read(master_fd, 1024)
                                if data:
                                    sys.stdout.buffer.write(data)
                                    sys.stdout.buffer.flush()
                                    try:
                                        text = data.decode("utf-8", errors="replace")
                                        stdout_log.write(text)
                                    except Exception:
                                        pass
                                else:
                                    break
                            else:
                                break
                    except OSError:
                        pass
                    break
        finally:
            os.close(master_fd)

        exit_code = process.returncode

    except Exception as e:
        exit_code = 1
        stderr_log.write(f"Error: {e}\n")
    finally:
        stdout_log.close()
        stderr_log.close()

    end_ts = time.time()
    duration = end_ts - start_ts
    end_time = now_iso()

    # Print footer
    if show_header:
        footer = format_run_footer(run_id, exit_code, duration)
        sys.stdout.write(footer)
        sys.stdout.flush()

    # Update metadata
    metadata["ended_at"] = end_time
    metadata["exit_code"] = exit_code
    metadata["status"] = "completed" if exit_code == 0 else "failed"
    metadata["duration_seconds"] = round(duration, 2)
    metadata_file.write_text(json.dumps(metadata, indent=2) + "\n")

    # Update status file
    status_file = run_dir / "status.txt"
    status = "completed" if exit_code == 0 else "failed"
    status_file.write_text(f"{status}\nstarted: {start_time}\nended: {end_time}\n")

    # Unregister from daemon
    if agent_id:
        _try_daemon_call("unregister_agent", agent_id)
        agent_id_file = run_dir / "agent_id.txt"
        if agent_id_file.exists():
            agent_id_file.unlink()

    return {
        "name": name,
        "run_id": run_id,
        "command": command,
        "script_hash": script_hash,
        "exit_code": exit_code,
        "status": metadata["status"],
        "duration_seconds": round(duration, 2),
        "started_at": start_time,
        "ended_at": end_time,
        "path": str(run_dir),
    }

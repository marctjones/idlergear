"""Daemon lifecycle management - auto-start, health checks, and recovery."""

import asyncio
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from idlergear.daemon.client import DaemonClient, DaemonError, DaemonNotRunning


class DaemonLifecycle:
    """Manages the daemon lifecycle for a project."""

    def __init__(self, idlergear_root: Path):
        self.root = idlergear_root
        self.socket_path = idlergear_root / "daemon.sock"
        self.pid_path = idlergear_root / "daemon.pid"
        self.log_path = idlergear_root / "daemon.log"

    def is_running(self) -> bool:
        """Check if the daemon is running (fast check)."""
        if not self.pid_path.exists():
            return False

        try:
            pid = int(self.pid_path.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            return False

    async def is_healthy(self) -> bool:
        """Check if the daemon is running and responsive."""
        if not self.is_running():
            return False

        client = DaemonClient(self.socket_path)
        try:
            await client.connect()
            await asyncio.wait_for(client.ping(), timeout=5.0)
            return True
        except (DaemonNotRunning, DaemonError, asyncio.TimeoutError):
            return False
        finally:
            await client.disconnect()

    def get_pid(self) -> int | None:
        """Get the daemon PID if running."""
        if not self.pid_path.exists():
            return None

        try:
            pid = int(self.pid_path.read_text().strip())
            os.kill(pid, 0)
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            return None

    def _can_connect_sync(self) -> bool:
        """Synchronously check if we can connect to the socket."""
        if not self.socket_path.exists():
            return False

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(str(self.socket_path))
            sock.close()
            return True
        except (socket.error, OSError):
            return False

    def start(self, wait: bool = True, timeout: float = 10.0) -> int:
        """Start the daemon process.

        Args:
            wait: Wait for daemon to be responsive before returning.
            timeout: Maximum time to wait for daemon to start.

        Returns:
            The daemon PID.

        Raises:
            RuntimeError: If daemon fails to start.
        """
        # Check if already running
        if self.is_running():
            pid = self.get_pid()
            if pid:
                return pid

        # Clean up stale files
        self._cleanup_stale_files()

        # Start the daemon process
        log_file = open(self.log_path, "a")
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "idlergear.daemon",
                str(self.root),
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        if not wait:
            return proc.pid

        # Wait for daemon to be ready (sync check only)
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_running() and self._can_connect_sync():
                return self.get_pid() or proc.pid
            time.sleep(0.1)

        # Check if process died
        if proc.poll() is not None:
            raise RuntimeError(
                f"Daemon process exited with code {proc.returncode}. "
                f"Check {self.log_path} for details."
            )

        raise RuntimeError(f"Daemon failed to start within {timeout}s")

    def stop(self, timeout: float = 10.0) -> bool:
        """Stop the daemon gracefully.

        Returns:
            True if daemon was stopped, False if it wasn't running.
        """
        pid = self.get_pid()
        if pid is None:
            self._cleanup_stale_files()
            return False

        # Send SIGTERM
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            self._cleanup_stale_files()
            return False

        # Wait for process to exit
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except ProcessLookupError:
                self._cleanup_stale_files()
                return True

        # Force kill if still running
        try:
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
        except ProcessLookupError:
            pass

        self._cleanup_stale_files()
        return True

    def restart(self, timeout: float = 10.0) -> int:
        """Restart the daemon.

        Returns:
            The new daemon PID.
        """
        self.stop(timeout=timeout / 2)
        return self.start(wait=True, timeout=timeout / 2)

    def _cleanup_stale_files(self) -> None:
        """Clean up stale socket and PID files."""
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except OSError:
                pass

        if self.pid_path.exists():
            try:
                self.pid_path.unlink()
            except OSError:
                pass

    async def get_status(self) -> dict[str, Any]:
        """Get detailed daemon status."""
        pid = self.get_pid()
        if pid is None:
            return {
                "running": False,
                "pid": None,
                "socket": str(self.socket_path),
            }

        # Try to get status from daemon
        client = DaemonClient(self.socket_path)
        try:
            await client.connect()
            status = await client.status()
            status["healthy"] = True
            return status
        except (DaemonNotRunning, DaemonError):
            return {
                "running": True,
                "healthy": False,
                "pid": pid,
                "socket": str(self.socket_path),
                "error": "Not responding",
            }
        finally:
            await client.disconnect()


def ensure_daemon(idlergear_root: Path) -> DaemonClient:
    """Ensure the daemon is running and return a connected client.

    This is the main entry point for code that needs to use the daemon.
    It will auto-start the daemon if not running.
    """
    lifecycle = DaemonLifecycle(idlergear_root)

    # Start daemon if not running
    if not lifecycle.is_running():
        lifecycle.start(wait=True)

    # Create and return client
    client = DaemonClient(lifecycle.socket_path)
    return client

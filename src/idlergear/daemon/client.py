"""IdlerGear daemon client - Connect to daemon via Unix socket."""

import asyncio
import json
import os
import signal
from pathlib import Path
from typing import Any

from idlergear.daemon.protocol import (
    ErrorCode,
    Notification,
    Request,
    Response,
    parse_message,
)


class DaemonError(Exception):
    """Error from daemon communication."""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"[{code}] {message}")


class DaemonNotRunning(Exception):
    """Daemon is not running."""

    pass


class DaemonClient:
    """Client for communicating with the IdlerGear daemon."""

    def __init__(self, socket_path: Path):
        self.socket_path = socket_path
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[Response]] = {}
        self._receive_task: asyncio.Task | None = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to the daemon."""
        if not self.socket_path.exists():
            raise DaemonNotRunning(f"Daemon socket not found: {self.socket_path}")

        try:
            self._reader, self._writer = await asyncio.open_unix_connection(
                str(self.socket_path)
            )
        except (ConnectionRefusedError, FileNotFoundError):
            raise DaemonNotRunning("Cannot connect to daemon")

        self._connected = True
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def __aenter__(self) -> "DaemonClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def disconnect(self) -> None:
        """Disconnect from the daemon."""
        self._connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

        # Cancel pending requests
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

    async def _send(self, message: str) -> None:
        """Send a message to the daemon."""
        if not self._writer:
            raise DaemonNotRunning("Not connected")

        encoded = message.encode("utf-8")
        length = len(encoded)
        self._writer.write(length.to_bytes(4, "big") + encoded)
        await self._writer.drain()

    async def _recv(self) -> str | None:
        """Receive a message from the daemon."""
        if not self._reader:
            return None

        try:
            length_bytes = await self._reader.readexactly(4)
            length = int.from_bytes(length_bytes, "big")
            data = await self._reader.readexactly(length)
            return data.decode("utf-8")
        except (asyncio.IncompleteReadError, ConnectionError):
            return None

    async def _receive_loop(self) -> None:
        """Background loop to receive messages."""
        while self._connected:
            message = await self._recv()
            if message is None:
                break

            try:
                parsed = parse_message(message)
            except ValueError:
                continue

            if isinstance(parsed, Response) and parsed.id is not None:
                future = self._pending.pop(parsed.id, None)
                if future and not future.done():
                    future.set_result(parsed)
            elif isinstance(parsed, Notification):
                # Handle event notifications
                await self._handle_notification(parsed)

    async def _handle_notification(self, notification: Notification) -> None:
        """Handle incoming notification (events)."""
        # Subclasses can override this
        pass

    async def call(
        self, method: str, params: dict[str, Any] | None = None, timeout: float = 30.0
    ) -> Any:
        """Call a method on the daemon and wait for response."""
        if not self._connected:
            raise DaemonNotRunning("Not connected")

        request_id = self._next_id
        self._next_id += 1

        request = Request(method=method, params=params or {}, id=request_id)

        # Create future for response
        future: asyncio.Future[Response] = asyncio.Future()
        self._pending[request_id] = future

        try:
            await self._send(request.to_json())
            response = await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            raise DaemonError(-1, "Request timed out")

        if response.error:
            raise DaemonError(
                response.error["code"],
                response.error["message"],
                response.error.get("data"),
            )

        return response.result

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        """Send a notification to the daemon (no response expected)."""
        if not self._connected:
            raise DaemonNotRunning("Not connected")

        notification = Notification(method=method, params=params or {})
        await self._send(notification.to_json())

    # Convenience methods
    async def ping(self) -> bool:
        """Check if daemon is responsive."""
        result = await self.call("daemon.ping")
        return result.get("pong", False)

    async def status(self) -> dict[str, Any]:
        """Get daemon status."""
        return await self.call("daemon.status")

    async def shutdown(self) -> None:
        """Request daemon shutdown."""
        try:
            await self.call("daemon.shutdown", timeout=5.0)
        except (DaemonError, asyncio.TimeoutError):
            pass  # Expected - daemon shuts down

    async def subscribe(self, event: str) -> None:
        """Subscribe to an event."""
        await self.call("daemon.subscribe", {"event": event})

    async def unsubscribe(self, event: str) -> None:
        """Unsubscribe from an event."""
        await self.call("daemon.unsubscribe", {"event": event})


def get_daemon_client(idlergear_root: Path) -> DaemonClient:
    """Get a daemon client for the given project root."""
    socket_path = idlergear_root / "daemon.sock"
    return DaemonClient(socket_path)


async def is_daemon_running(idlergear_root: Path) -> bool:
    """Check if the daemon is running."""
    socket_path = idlergear_root / "daemon.sock"
    pid_path = idlergear_root / "daemon.pid"

    # Check if socket exists
    if not socket_path.exists():
        return False

    # Check if PID file exists and process is running
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
        except (ValueError, ProcessLookupError, PermissionError):
            # Stale PID file
            return False
    else:
        return False

    # Try to connect and ping
    client = DaemonClient(socket_path)
    try:
        await client.connect()
        await client.ping()
        return True
    except (DaemonNotRunning, DaemonError):
        return False
    finally:
        await client.disconnect()


def start_daemon_process(idlergear_root: Path) -> int:
    """Start the daemon as a background process. Returns PID."""
    import subprocess
    import sys

    # Fork a new process to run the daemon
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "idlergear.daemon.server",
            str(idlergear_root),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # Detach from terminal
    )

    return proc.pid


def stop_daemon_process(idlergear_root: Path) -> bool:
    """Stop the daemon process. Returns True if stopped."""
    pid_path = idlergear_root / "daemon.pid"

    if not pid_path.exists():
        return False

    try:
        pid = int(pid_path.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False

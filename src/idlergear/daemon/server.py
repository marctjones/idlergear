"""IdlerGear daemon server - Unix socket server with JSON-RPC 2.0."""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any, Callable, Coroutine

from idlergear.daemon.protocol import (
    ErrorCode,
    Notification,
    Request,
    Response,
    parse_message,
)

logger = logging.getLogger(__name__)


class Connection:
    """Represents a client connection to the daemon."""

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        conn_id: int,
    ):
        self.reader = reader
        self.writer = writer
        self.conn_id = conn_id
        self.subscriptions: set[str] = set()
        self._closed = False

    async def send(self, message: str) -> None:
        """Send a message to the client."""
        if self._closed:
            return
        try:
            # Length-prefixed framing: 4-byte length + message
            encoded = message.encode("utf-8")
            length = len(encoded)
            self.writer.write(length.to_bytes(4, "big") + encoded)
            await self.writer.drain()
        except (ConnectionError, BrokenPipeError):
            self._closed = True

    async def recv(self) -> str | None:
        """Receive a message from the client."""
        if self._closed:
            return None
        try:
            # Read 4-byte length prefix
            length_bytes = await self.reader.readexactly(4)
            length = int.from_bytes(length_bytes, "big")
            if length > 10 * 1024 * 1024:  # 10MB limit
                logger.warning(f"Message too large: {length} bytes")
                return None
            data = await self.reader.readexactly(length)
            return data.decode("utf-8")
        except asyncio.IncompleteReadError:
            self._closed = True
            return None
        except (ConnectionError, BrokenPipeError):
            self._closed = True
            return None

    def close(self) -> None:
        """Close the connection."""
        self._closed = True
        self.writer.close()


# Type for method handlers
MethodHandler = Callable[[dict[str, Any], Connection], Coroutine[Any, Any, Any]]


class DaemonServer:
    """Unix socket daemon server with JSON-RPC 2.0 protocol."""

    def __init__(self, socket_path: Path, pid_path: Path):
        self.socket_path = socket_path
        self.pid_path = pid_path
        self._server: asyncio.Server | None = None
        self._connections: dict[int, Connection] = {}
        self._next_conn_id = 1
        self._methods: dict[str, MethodHandler] = {}
        self._running = False

        # Register built-in methods
        self._register_builtin_methods()

    def _register_builtin_methods(self) -> None:
        """Register built-in daemon methods."""
        self.register_method("daemon.ping", self._handle_ping)
        self.register_method("daemon.status", self._handle_status)
        self.register_method("daemon.shutdown", self._handle_shutdown)
        self.register_method("daemon.subscribe", self._handle_subscribe)
        self.register_method("daemon.unsubscribe", self._handle_unsubscribe)

    def register_method(self, name: str, handler: MethodHandler) -> None:
        """Register a method handler."""
        self._methods[name] = handler

    async def _handle_ping(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle ping request."""
        return {"pong": True}

    async def _handle_status(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle status request."""
        return {
            "running": True,
            "pid": os.getpid(),
            "connections": len(self._connections),
            "socket": str(self.socket_path),
        }

    async def _handle_shutdown(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle shutdown request."""
        logger.info("Shutdown requested")
        asyncio.create_task(self._shutdown())
        return {"shutting_down": True}

    async def _handle_subscribe(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle event subscription."""
        event = params.get("event")
        if not event:
            raise ValueError("Missing 'event' parameter")
        conn.subscriptions.add(event)
        return {"subscribed": event}

    async def _handle_unsubscribe(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle event unsubscription."""
        event = params.get("event")
        if not event:
            raise ValueError("Missing 'event' parameter")
        conn.subscriptions.discard(event)
        return {"unsubscribed": event}

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        """Broadcast an event to all subscribed connections."""
        notification = Notification(
            method="event",
            params={"event": event, "data": data},
        )
        message = notification.to_json()

        for conn in list(self._connections.values()):
            if event in conn.subscriptions:
                await conn.send(message)

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a client connection."""
        conn_id = self._next_conn_id
        self._next_conn_id += 1
        conn = Connection(reader, writer, conn_id)
        self._connections[conn_id] = conn

        peer = writer.get_extra_info("peername")
        logger.debug(f"Client connected: {conn_id} from {peer}")

        try:
            while self._running:
                message = await conn.recv()
                if message is None:
                    break

                await self._process_message(message, conn)
        except Exception as e:
            logger.error(f"Error handling client {conn_id}: {e}")
        finally:
            del self._connections[conn_id]
            conn.close()
            logger.debug(f"Client disconnected: {conn_id}")

    async def _process_message(self, message: str, conn: Connection) -> None:
        """Process an incoming message."""
        try:
            parsed = parse_message(message)
        except ValueError as e:
            response = Response.error_response(
                None, ErrorCode.PARSE_ERROR, str(e)
            )
            await conn.send(response.to_json())
            return

        if isinstance(parsed, Response):
            # We don't expect responses from clients
            logger.warning(f"Unexpected response from client: {parsed}")
            return

        if isinstance(parsed, Notification):
            # Fire-and-forget, no response needed
            await self._dispatch_method(parsed.method, parsed.params, conn)
            return

        # It's a Request, needs a response
        request = parsed
        try:
            result = await self._dispatch_method(
                request.method, request.params, conn
            )
            response = Response.success(request.id, result)
        except KeyError:
            response = Response.error_response(
                request.id,
                ErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {request.method}",
            )
        except ValueError as e:
            response = Response.error_response(
                request.id, ErrorCode.INVALID_PARAMS, str(e)
            )
        except Exception as e:
            logger.exception(f"Error in method {request.method}")
            response = Response.error_response(
                request.id, ErrorCode.INTERNAL_ERROR, str(e)
            )

        await conn.send(response.to_json())

    async def _dispatch_method(
        self, method: str, params: dict[str, Any], conn: Connection
    ) -> Any:
        """Dispatch a method call to its handler."""
        if method not in self._methods:
            raise KeyError(f"Method not found: {method}")
        return await self._methods[method](params, conn)

    async def start(self) -> None:
        """Start the daemon server."""
        # Clean up stale socket
        if self.socket_path.exists():
            self.socket_path.unlink()

        # Ensure parent directory exists
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)

        # Create server
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self.socket_path),
        )

        # Set socket permissions (owner only)
        os.chmod(self.socket_path, 0o600)

        # Write PID file
        self.pid_path.write_text(str(os.getpid()))

        self._running = True
        logger.info(f"Daemon started on {self.socket_path}")

    async def serve_forever(self) -> None:
        """Serve until shutdown."""
        if not self._server:
            raise RuntimeError("Server not started")

        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self._shutdown()))

        async with self._server:
            await self._server.serve_forever()

    async def _shutdown(self) -> None:
        """Shutdown the daemon gracefully."""
        logger.info("Shutting down daemon...")
        self._running = False

        # Close all connections
        for conn in list(self._connections.values()):
            conn.close()
        self._connections.clear()

        # Stop server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Clean up files
        if self.socket_path.exists():
            self.socket_path.unlink()
        if self.pid_path.exists():
            self.pid_path.unlink()

        logger.info("Daemon stopped")

    def stop(self) -> None:
        """Stop the daemon (sync wrapper)."""
        if self._running:
            asyncio.create_task(self._shutdown())


def run_daemon(idlergear_root: Path) -> None:
    """Run the daemon process."""
    socket_path = idlergear_root / "daemon.sock"
    pid_path = idlergear_root / "daemon.pid"

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Create and run server
    server = DaemonServer(socket_path, pid_path)

    # Register knowledge management methods
    from idlergear.daemon.handlers import register_handlers
    register_handlers(server)

    async def main():
        await server.start()
        await server.serve_forever()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

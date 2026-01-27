"""IdlerGear daemon server - Unix socket server with JSON-RPC 2.0."""

import asyncio
import logging
import os
import signal
from pathlib import Path
from typing import Any, Callable, Coroutine

from idlergear.daemon.protocol import (
    ErrorCode,
    Notification,
    Response,
    parse_message,
)
from idlergear.daemon.queue import CommandQueue
from idlergear.daemon.agents import AgentRegistry
from idlergear.daemon.locks import LockManager

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

    def __init__(self, socket_path: Path, pid_path: Path, storage_path: Path):
        self.socket_path = socket_path
        self.pid_path = pid_path
        self.storage_path = storage_path
        self._server: asyncio.Server | None = None
        self._connections: dict[int, Connection] = {}
        self._next_conn_id = 1
        self._methods: dict[str, MethodHandler] = {}
        self._running = False

        # Multi-agent coordination components
        self.queue = CommandQueue(storage_path / "queue")
        self.agents = AgentRegistry(storage_path / "agents")
        self.locks = LockManager()

        # Register built-in methods
        self._register_builtin_methods()

    def _register_builtin_methods(self) -> None:
        """Register built-in daemon methods."""
        self.register_method("daemon.ping", self._handle_ping)
        self.register_method("daemon.status", self._handle_status)
        self.register_method("daemon.shutdown", self._handle_shutdown)
        self.register_method("daemon.subscribe", self._handle_subscribe)
        self.register_method("daemon.unsubscribe", self._handle_unsubscribe)

        # Agent registration methods
        self.register_method("agent.register", self._handle_agent_register)
        self.register_method("agent.unregister", self._handle_agent_unregister)
        self.register_method("agent.heartbeat", self._handle_agent_heartbeat)
        self.register_method("agent.update_status", self._handle_agent_update_status)
        self.register_method("agent.update_state", self._handle_agent_update_state)
        self.register_method(
            "agent.append_uncertainty", self._handle_agent_append_uncertainty
        )
        self.register_method("agent.append_search", self._handle_agent_append_search)
        self.register_method("agent.list", self._handle_agent_list)

        # Session monitoring methods
        self.register_method("session.start", self._handle_session_start)
        self.register_method("session.end", self._handle_session_end)
        self.register_method("session.update", self._handle_session_update)
        self.register_method("session.list", self._handle_session_list)
        self.register_method("session.get", self._handle_session_get)

        # Queue methods
        self.register_method("queue.add", self._handle_queue_add)
        self.register_method("queue.get", self._handle_queue_get)
        self.register_method("queue.list", self._handle_queue_list)
        self.register_method("queue.poll", self._handle_queue_poll)
        self.register_method("queue.start", self._handle_queue_start)
        self.register_method("queue.complete", self._handle_queue_complete)
        self.register_method("queue.cancel", self._handle_queue_cancel)

        # Lock methods
        self.register_method("lock.acquire", self._handle_lock_acquire)
        self.register_method("lock.release", self._handle_lock_release)
        self.register_method("lock.is_locked", self._handle_lock_is_locked)
        self.register_method("lock.list", self._handle_lock_list)

        # Message methods
        self.register_method("message.broadcast", self._handle_message_broadcast)

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

    # Agent registration handlers
    async def _handle_agent_register(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle agent registration."""
        agent_id = params.get("agent_id")
        agent_type = params.get("agent_type")
        if not agent_id or not agent_type:
            raise ValueError("Missing agent_id or agent_type")

        session = await self.agents.register(
            agent_id=agent_id,
            agent_type=agent_type,
            connection_id=conn.conn_id,
            capabilities=params.get("capabilities"),
            metadata=params.get("metadata"),
        )

        await self.broadcast("agent.registered", session.to_dict())
        return session.to_dict()

    async def _handle_agent_unregister(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle agent unregistration."""
        agent_id = params.get("agent_id")
        if not agent_id:
            raise ValueError("Missing agent_id")

        # Release all locks held by this agent
        await self.locks.release_all(agent_id)

        success = await self.agents.unregister(agent_id)
        if success:
            await self.broadcast("agent.unregistered", {"agent_id": agent_id})

        return {"success": success}

    async def _handle_agent_heartbeat(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle agent heartbeat."""
        agent_id = params.get("agent_id")
        if not agent_id:
            raise ValueError("Missing agent_id")

        success = await self.agents.heartbeat(agent_id)
        return {"success": success}

    async def _handle_agent_update_status(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle agent status update."""
        agent_id = params.get("agent_id")
        status = params.get("status")
        if not agent_id or not status:
            raise ValueError("Missing agent_id or status")

        success = await self.agents.update_status(
            agent_id, status, params.get("current_task")
        )
        if success:
            await self.broadcast(
                "agent.status_changed",
                {
                    "agent_id": agent_id,
                    "status": status,
                    "current_task": params.get("current_task"),
                },
            )

        return {"success": success}

    async def _handle_agent_list(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle agent list request."""
        agents = await self.agents.list(
            agent_type=params.get("agent_type"), status=params.get("status")
        )
        return {"agents": [a.to_dict() for a in agents]}

    async def _handle_agent_update_state(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle AI state update for observability.

        Updates agent's AI state (current activity, planned steps, uncertainties, etc.)
        and broadcasts changes to subscribers for real-time monitoring.
        """
        agent_id = params.get("agent_id")
        ai_state = params.get("ai_state")

        if not agent_id:
            raise ValueError("Missing agent_id")
        if not ai_state or not isinstance(ai_state, dict):
            raise ValueError("Missing or invalid ai_state (must be dict)")

        # Update agent's AI state in registry
        merge = params.get("merge", True)
        success = await self.agents.update_ai_state(agent_id, ai_state, merge=merge)

        if success:
            # Broadcast specific event types based on what was updated
            if "current_activity" in ai_state:
                await self.broadcast(
                    "ai.activity_changed",
                    {
                        "agent_id": agent_id,
                        "activity": ai_state["current_activity"],
                    },
                )

            if "planned_steps" in ai_state:
                await self.broadcast(
                    "ai.plan_updated",
                    {
                        "agent_id": agent_id,
                        "plan": ai_state["planned_steps"],
                    },
                )

            if "uncertainties" in ai_state:
                # Check if there are uncertainties with low confidence
                uncertainties = ai_state["uncertainties"]
                if isinstance(uncertainties, list) and uncertainties:
                    # Get most recent uncertainty
                    latest = uncertainties[-1] if uncertainties else None
                    if latest:
                        await self.broadcast(
                            "ai.uncertainty_detected",
                            {
                                "agent_id": agent_id,
                                "uncertainty": latest,
                            },
                        )

            if "search_history" in ai_state:
                # Check for repeated searches (same query multiple times)
                history = ai_state["search_history"]
                if isinstance(history, list) and len(history) >= 2:
                    latest_search = history[-1]
                    # Count how many times this query appeared
                    query = latest_search.get("query", "")
                    count = sum(1 for s in history if s.get("query") == query)
                    if count >= 2:
                        await self.broadcast(
                            "ai.search_repeated",
                            {
                                "agent_id": agent_id,
                                "query": query,
                                "count": count,
                                "search": latest_search,
                            },
                        )

        return {"success": success}

    async def _handle_agent_append_uncertainty(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Append an uncertainty report to agent's AI state.

        Used when AI is confused or has low confidence about something.
        """
        agent_id = params.get("agent_id")
        uncertainty = params.get("uncertainty")

        if not agent_id:
            raise ValueError("Missing agent_id")
        if not uncertainty or not isinstance(uncertainty, dict):
            raise ValueError("Missing or invalid uncertainty (must be dict)")

        # Get current agent state
        agent = await self.agents.get(agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}

        # Append to uncertainties list
        uncertainties = agent.ai_state.get("uncertainties", [])
        uncertainties.append(uncertainty)

        # Update state with new list
        success = await self.agents.update_ai_state(
            agent_id, {"uncertainties": uncertainties}, merge=True
        )

        if success:
            # Broadcast uncertainty detected event
            await self.broadcast(
                "ai.uncertainty_detected",
                {
                    "agent_id": agent_id,
                    "uncertainty": uncertainty,
                },
            )

        return {"success": success}

    async def _handle_agent_append_search(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Append a search report to agent's AI state.

        Tracks search activity to detect inefficiency (repeated searches).
        """
        agent_id = params.get("agent_id")
        search = params.get("search")

        if not agent_id:
            raise ValueError("Missing agent_id")
        if not search or not isinstance(search, dict):
            raise ValueError("Missing or invalid search (must be dict)")

        # Get current agent state
        agent = await self.agents.get(agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}

        # Append to search history (keep last 20 searches)
        search_history = agent.ai_state.get("search_history", [])
        search_history.append(search)
        if len(search_history) > 20:
            search_history = search_history[-20:]  # Keep only last 20

        # Update state with new list
        success = await self.agents.update_ai_state(
            agent_id, {"search_history": search_history}, merge=True
        )

        if success:
            # Check for repeated searches
            query = search.get("query", "")
            count = sum(1 for s in search_history if s.get("query") == query)

            if count >= 2:
                # Repeated search detected - broadcast warning
                await self.broadcast(
                    "ai.search_repeated",
                    {
                        "agent_id": agent_id,
                        "query": query,
                        "count": count,
                        "search": search,
                    },
                )

        return {"success": success, "search_count": len(search_history)}

    # Session monitoring handlers
    async def _handle_session_start(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle session start notification."""
        agent_id = params.get("agent_id")
        session_id = params.get("session_id")
        session_name = params.get("session_name")

        if not agent_id or not session_id:
            raise ValueError("Missing agent_id or session_id")

        # Update agent's session information
        success = await self.agents.update_session(
            agent_id=agent_id,
            session_id=session_id,
            session_name=session_name,
            working_files=params.get("working_files"),
            current_task_id=params.get("current_task_id"),
        )

        if success:
            agent = await self.agents.get(agent_id)
            if agent:
                await self.broadcast("session.started", agent.to_dict())

        return {"success": success}

    async def _handle_session_end(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle session end notification."""
        agent_id = params.get("agent_id")
        session_id = params.get("session_id")

        if not agent_id or not session_id:
            raise ValueError("Missing agent_id or session_id")

        # Clear session information
        success = await self.agents.update_session(
            agent_id=agent_id,
            session_id=None,
            session_name=None,
            working_files=[],
            current_task_id=None,
        )

        if success:
            await self.broadcast(
                "session.ended",
                {"agent_id": agent_id, "session_id": session_id},
            )

        return {"success": success}

    async def _handle_session_update(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle session state update."""
        agent_id = params.get("agent_id")
        if not agent_id:
            raise ValueError("Missing agent_id")

        # Update session fields (only those provided)
        success = await self.agents.update_session(
            agent_id=agent_id,
            session_id=params.get("session_id"),
            session_name=params.get("session_name"),
            working_files=params.get("working_files"),
            current_task_id=params.get("current_task_id"),
        )

        if success:
            agent = await self.agents.get(agent_id)
            if agent:
                # Determine what changed and broadcast appropriate event
                event_data = agent.to_dict()

                if params.get("current_task_id") is not None:
                    await self.broadcast("session.task_changed", event_data)
                elif params.get("working_files") is not None:
                    await self.broadcast("session.files_changed", event_data)
                else:
                    await self.broadcast("session.updated", event_data)

        return {"success": success}

    async def _handle_session_list(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle session list request - returns all active sessions."""
        agents = await self.agents.list()

        # Filter to only agents with active sessions
        sessions = [
            {
                "agent_id": a.agent_id,
                "agent_type": a.agent_type,
                "session_id": a.session_id,
                "session_name": a.session_name,
                "working_files": a.working_files,
                "current_task_id": a.current_task_id,
                "status": a.status,
                "last_heartbeat": a.last_heartbeat,
            }
            for a in agents
            if a.session_id is not None
        ]

        return {"sessions": sessions}

    async def _handle_session_get(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle getting session details for a specific agent."""
        agent_id = params.get("agent_id")
        if not agent_id:
            raise ValueError("Missing agent_id")

        agent = await self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        return {
            "agent_id": agent.agent_id,
            "agent_type": agent.agent_type,
            "session_id": agent.session_id,
            "session_name": agent.session_name,
            "working_files": agent.working_files,
            "current_task_id": agent.current_task_id,
            "status": agent.status,
            "last_heartbeat": agent.last_heartbeat,
        }

    # Queue handlers
    async def _handle_queue_add(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle adding command to queue."""
        prompt = params.get("prompt")
        if not prompt:
            raise ValueError("Missing prompt")

        cmd_id = await self.queue.add(
            prompt=prompt,
            priority=params.get("priority", 0),
            tags=params.get("tags"),
            metadata=params.get("metadata"),
        )

        await self.broadcast("queue.added", {"id": cmd_id, "prompt": prompt[:100]})

        return {"id": cmd_id}

    async def _handle_queue_get(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle getting command by ID."""
        cmd_id = params.get("id")
        if not cmd_id:
            raise ValueError("Missing id")

        command = await self.queue.get(cmd_id)
        if not command:
            raise ValueError(f"Command not found: {cmd_id}")

        return command.to_dict()

    async def _handle_queue_list(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle listing queued commands."""
        from idlergear.daemon.queue import CommandStatus

        status = params.get("status")
        if status:
            status = CommandStatus(status)

        commands = await self.queue.list(status=status, agent_id=params.get("agent_id"))

        return {"commands": [c.to_dict() for c in commands]}

    async def _handle_queue_poll(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle polling for next command."""
        agent_id = params.get("agent_id")
        if not agent_id:
            raise ValueError("Missing agent_id")

        command = await self.queue.poll_pending(agent_id)
        if command:
            await self.broadcast(
                "queue.assigned",
                {"id": command.id, "agent_id": agent_id},
            )
            return command.to_dict()

        return {"command": None}

    async def _handle_queue_start(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle marking command as started."""
        cmd_id = params.get("id")
        if not cmd_id:
            raise ValueError("Missing id")

        success = await self.queue.start(cmd_id)
        if success:
            await self.broadcast("queue.started", {"id": cmd_id})

        return {"success": success}

    async def _handle_queue_complete(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle marking command as completed."""
        cmd_id = params.get("id")
        if not cmd_id:
            raise ValueError("Missing id")

        success = await self.queue.complete(
            cmd_id, result=params.get("result", {}), error=params.get("error")
        )

        if success:
            await self.broadcast(
                "queue.completed",
                {
                    "id": cmd_id,
                    "success": params.get("error") is None,
                },
            )

        return {"success": success}

    async def _handle_queue_cancel(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle canceling a command."""
        cmd_id = params.get("id")
        if not cmd_id:
            raise ValueError("Missing id")

        success = await self.queue.cancel(cmd_id)
        if success:
            await self.broadcast("queue.cancelled", {"id": cmd_id})

        return {"success": success}

    # Lock handlers
    async def _handle_lock_acquire(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle lock acquisition."""
        resource = params.get("resource")
        agent_id = params.get("agent_id")
        if not resource or not agent_id:
            raise ValueError("Missing resource or agent_id")

        acquired = await self.locks.acquire(
            resource, agent_id, timeout=params.get("timeout")
        )

        if acquired:
            await self.broadcast(
                "lock.acquired", {"resource": resource, "agent_id": agent_id}
            )

        return {"acquired": acquired}

    async def _handle_lock_release(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle lock release."""
        resource = params.get("resource")
        agent_id = params.get("agent_id")
        if not resource or not agent_id:
            raise ValueError("Missing resource or agent_id")

        released = await self.locks.release(resource, agent_id)

        if released:
            await self.broadcast(
                "lock.released", {"resource": resource, "agent_id": agent_id}
            )

        return {"released": released}

    async def _handle_lock_is_locked(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle lock status check."""
        resource = params.get("resource")
        if not resource:
            raise ValueError("Missing resource")

        is_locked = await self.locks.is_locked(resource)
        lock_info = await self.locks.get_lock(resource)

        return {
            "is_locked": is_locked,
            "lock": lock_info.__dict__ if lock_info else None,
        }

    async def _handle_lock_list(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle listing locks."""
        locks = await self.locks.list_locks(agent_id=params.get("agent_id"))
        return {"locks": [lock.__dict__ for lock in locks]}

    async def _handle_message_broadcast(
        self, params: dict[str, Any], conn: Connection
    ) -> dict[str, Any]:
        """Handle broadcasting a message to all agents."""
        event = params.get("event", "message")
        data = params.get("data", {})
        await self.broadcast(event, data)
        return {
            "broadcasted": True,
            "event": event,
            "connections": len(self._connections),
        }

    def _matches_subscription(self, event: str, subscription: str) -> bool:
        """Check if an event matches a subscription pattern.

        Supports wildcards:
        - "task.*" matches "task.created", "task.closed", etc.
        - "*" matches all events
        - "task.created" matches exactly "task.created"
        """
        if subscription == "*":
            return True
        if subscription == event:
            return True
        if subscription.endswith(".*"):
            prefix = subscription[:-2]
            return event.startswith(prefix + ".")
        return False

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        """Broadcast an event to all subscribed connections.

        Supports wildcard subscriptions like "task.*" or "*".
        """
        notification = Notification(
            method="event",
            params={"event": event, "data": data},
        )
        message = notification.to_json()

        for conn in list(self._connections.values()):
            for subscription in conn.subscriptions:
                if self._matches_subscription(event, subscription):
                    await conn.send(message)
                    break  # Only send once per connection

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
            response = Response.error_response(None, ErrorCode.PARSE_ERROR, str(e))
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
            result = await self._dispatch_method(request.method, request.params, conn)
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
    storage_path = idlergear_root

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Create and run server
    server = DaemonServer(socket_path, pid_path, storage_path)

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

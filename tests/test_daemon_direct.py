"""Direct unit tests for daemon components."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from idlergear.daemon.protocol import (
    Request,
    Response,
    parse_message,
)
from idlergear.daemon.server import Connection, DaemonServer


class TestConnection:
    """Tests for Connection class."""

    @pytest.mark.asyncio
    async def test_send_when_closed(self):
        """Test that send does nothing when connection is closed."""
        reader = AsyncMock()
        writer = MagicMock()
        conn = Connection(reader, writer, 1)
        conn._closed = True

        await conn.send("test")

        # Writer should not be called
        writer.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_recv_when_closed(self):
        """Test that recv returns None when connection is closed."""
        reader = AsyncMock()
        writer = MagicMock()
        conn = Connection(reader, writer, 1)
        conn._closed = True

        result = await conn.recv()

        assert result is None

    def test_close(self):
        """Test closing a connection."""
        reader = AsyncMock()
        writer = MagicMock()
        conn = Connection(reader, writer, 1)

        conn.close()

        assert conn._closed is True
        writer.close.assert_called_once()


class TestDaemonServerMethods:
    """Tests for DaemonServer method registration."""

    def test_register_method(self):
        """Test registering a method handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            pid_path = Path(tmpdir) / "daemon.pid"
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            server = DaemonServer(socket_path, pid_path, storage_path)

            async def test_handler(params, conn):
                return {"test": True}

            server.register_method("test.method", test_handler)

            assert "test.method" in server._methods

    @pytest.mark.asyncio
    async def test_handle_ping(self):
        """Test ping handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            pid_path = Path(tmpdir) / "daemon.pid"
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            server = DaemonServer(socket_path, pid_path, storage_path)

            conn = MagicMock()
            result = await server._handle_ping({}, conn)

            assert result == {"pong": True}

    @pytest.mark.asyncio
    async def test_handle_status(self):
        """Test status handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            pid_path = Path(tmpdir) / "daemon.pid"
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            server = DaemonServer(socket_path, pid_path, storage_path)

            conn = MagicMock()
            result = await server._handle_status({}, conn)

            assert result["running"] is True
            assert "pid" in result
            assert result["connections"] == 0

    @pytest.mark.asyncio
    async def test_handle_subscribe(self):
        """Test subscribe handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            pid_path = Path(tmpdir) / "daemon.pid"
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            server = DaemonServer(socket_path, pid_path, storage_path)

            conn = MagicMock()
            conn.subscriptions = set()

            result = await server._handle_subscribe({"event": "test.event"}, conn)

            assert result["subscribed"] == "test.event"
            assert "test.event" in conn.subscriptions

    @pytest.mark.asyncio
    async def test_handle_subscribe_missing_event(self):
        """Test subscribe handler with missing event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            pid_path = Path(tmpdir) / "daemon.pid"
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            server = DaemonServer(socket_path, pid_path, storage_path)

            conn = MagicMock()

            with pytest.raises(ValueError, match="Missing 'event'"):
                await server._handle_subscribe({}, conn)

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self):
        """Test unsubscribe handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            pid_path = Path(tmpdir) / "daemon.pid"
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            server = DaemonServer(socket_path, pid_path, storage_path)

            conn = MagicMock()
            conn.subscriptions = {"test.event"}

            result = await server._handle_unsubscribe({"event": "test.event"}, conn)

            assert result["unsubscribed"] == "test.event"
            assert "test.event" not in conn.subscriptions

    @pytest.mark.asyncio
    async def test_handle_unsubscribe_missing_event(self):
        """Test unsubscribe handler with missing event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            pid_path = Path(tmpdir) / "daemon.pid"
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            server = DaemonServer(socket_path, pid_path, storage_path)

            conn = MagicMock()

            with pytest.raises(ValueError, match="Missing 'event'"):
                await server._handle_unsubscribe({}, conn)

    @pytest.mark.asyncio
    async def test_dispatch_method(self):
        """Test dispatching a method call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            pid_path = Path(tmpdir) / "daemon.pid"
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            server = DaemonServer(socket_path, pid_path, storage_path)

            async def test_handler(params, conn):
                return {"value": params["x"] * 2}

            server.register_method("test.double", test_handler)
            conn = MagicMock()

            result = await server._dispatch_method("test.double", {"x": 5}, conn)

            assert result == {"value": 10}

    @pytest.mark.asyncio
    async def test_dispatch_method_not_found(self):
        """Test dispatching a method that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            pid_path = Path(tmpdir) / "daemon.pid"
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            server = DaemonServer(socket_path, pid_path, storage_path)

            conn = MagicMock()

            with pytest.raises(KeyError):
                await server._dispatch_method("nonexistent", {}, conn)

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting an event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "daemon.sock"
            pid_path = Path(tmpdir) / "daemon.pid"
            storage_path = Path(tmpdir) / "storage"
            storage_path.mkdir()
            server = DaemonServer(socket_path, pid_path, storage_path)

            # Create mock connections
            conn1 = MagicMock()
            conn1.subscriptions = {"test.event"}
            conn1.send = AsyncMock()

            conn2 = MagicMock()
            conn2.subscriptions = {"other.event"}
            conn2.send = AsyncMock()

            server._connections = {1: conn1, 2: conn2}

            await server.broadcast("test.event", {"data": "test"})

            # Only conn1 should receive the event
            conn1.send.assert_called_once()
            conn2.send.assert_not_called()


class TestHandlersRegistration:
    """Tests for handler registration."""

    def test_register_handlers(self, temp_project):
        """Test that all handlers are registered."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        # Check that all expected methods are registered
        expected_methods = [
            "task.create",
            "task.list",
            "task.get",
            "task.close",
            "task.update",
            "note.create",
            "note.list",
            "note.get",
            "note.delete",
            "note.promote",
            "explore.create",
            "explore.list",
            "explore.get",
            "explore.close",
            "vision.get",
            "vision.set",
            "plan.create",
            "plan.list",
            "plan.get",
            "plan.current",
            "plan.switch",
            "reference.add",
            "reference.list",
            "reference.get",
            "reference.update",
            "reference.search",
            "config.get",
            "config.set",
            "run.start",
            "run.list",
            "run.status",
            "run.logs",
            "run.stop",
        ]

        for method in expected_methods:
            assert method in server._methods, f"Method {method} not registered"


class TestHandlersExecution:
    """Tests for handler execution."""

    @pytest.mark.asyncio
    async def test_task_create_handler(self, temp_project):
        """Test task.create handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["task.create"]
        result = await handler({"title": "Test task"}, conn)

        assert result["title"] == "Test task"
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_task_list_handler(self, temp_project):
        """Test task.list handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.tasks import create_task

        create_task("Task 1")
        create_task("Task 2")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["task.list"]
        result = await handler({"state": "open"}, conn)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_note_create_handler(self, temp_project):
        """Test note.create handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["note.create"]
        result = await handler({"content": "Quick note"}, conn)

        assert result["content"] == "Quick note"
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_explore_create_handler(self, temp_project):
        """Test explore.create handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["explore.create"]
        result = await handler({"title": "Research", "body": "Details"}, conn)

        assert result["title"] == "Research"
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_vision_get_handler(self, temp_project):
        """Test vision.get handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["vision.get"]
        result = await handler({}, conn)

        assert result is not None
        assert "Project Vision" in result

    @pytest.mark.asyncio
    async def test_vision_set_handler(self, temp_project):
        """Test vision.set handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)
        server.broadcast = AsyncMock()

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["vision.set"]
        result = await handler({"content": "New vision"}, conn)

        assert result is True

    @pytest.mark.asyncio
    async def test_plan_create_handler(self, temp_project):
        """Test plan.create handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["plan.create"]
        result = await handler({"name": "my-plan", "title": "My Plan"}, conn)

        assert result["name"] == "my-plan"

    @pytest.mark.asyncio
    async def test_reference_add_handler(self, temp_project):
        """Test reference.add handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["reference.add"]
        result = await handler({"title": "API Guide", "body": "Content"}, conn)

        assert result["title"] == "API Guide"

    @pytest.mark.asyncio
    async def test_config_set_get_handlers(self, temp_project):
        """Test config.set and config.get handlers."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()

        # Set config
        set_handler = server._methods["config.set"]
        result = await set_handler({"key": "test.key", "value": "test-value"}, conn)
        assert result is True

        # Get config
        get_handler = server._methods["config.get"]
        result = await get_handler({"key": "test.key"}, conn)
        assert result == "test-value"

    @pytest.mark.asyncio
    async def test_run_start_handler(self, temp_project):
        """Test run.start handler."""
        import time
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["run.start"]
        result = await handler({"command": "echo hello", "name": "test-run"}, conn)

        assert result["name"] == "test-run"
        assert result["status"] == "running"

        # Wait for command to complete
        time.sleep(0.5)

    @pytest.mark.asyncio
    async def test_task_close_with_broadcast(self, temp_project):
        """Test task.close handler broadcasts event."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.tasks import create_task

        create_task("Test task")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)
        server.broadcast = AsyncMock()

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["task.close"]
        result = await handler({"id": 1}, conn)

        assert result["state"] == "closed"
        server.broadcast.assert_called_once()


class TestProtocolEdgeCases:
    """Tests for protocol edge cases."""

    def test_request_with_null_params(self):
        """Test request with null params."""
        msg = '{"jsonrpc": "2.0", "method": "test", "params": null, "id": 1}'
        parsed = parse_message(msg)

        assert isinstance(parsed, Request)
        assert parsed.params is None

    def test_response_to_json_with_error(self):
        """Test response to_json with error."""
        resp = Response(id=1, error={"code": -32600, "message": "Invalid"})
        data = json.loads(resp.to_json())

        assert "error" in data
        assert data["error"]["code"] == -32600


class TestAllHandlers:
    """Tests for all handler methods."""

    @pytest.mark.asyncio
    async def test_task_get_handler(self, temp_project):
        """Test task.get handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.tasks import create_task

        create_task("Test task")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["task.get"]
        result = await handler({"id": 1}, conn)

        assert result["title"] == "Test task"

    @pytest.mark.asyncio
    async def test_task_update_handler(self, temp_project):
        """Test task.update handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.tasks import create_task

        create_task("Original")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)
        server.broadcast = AsyncMock()

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["task.update"]
        result = await handler({"id": 1, "title": "Updated"}, conn)

        assert result["title"] == "Updated"
        server.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_note_list_handler(self, temp_project):
        """Test note.list handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.notes import create_note

        create_note("Note 1")
        create_note("Note 2")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["note.list"]
        result = await handler({}, conn)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_note_get_handler(self, temp_project):
        """Test note.get handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.notes import create_note

        create_note("Test note")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["note.get"]
        result = await handler({"id": 1}, conn)

        assert result["content"] == "Test note"

    @pytest.mark.asyncio
    async def test_note_delete_handler(self, temp_project):
        """Test note.delete handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.notes import create_note

        create_note("To delete")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)
        server.broadcast = AsyncMock()

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["note.delete"]
        result = await handler({"id": 1}, conn)

        assert result is True
        server.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_note_promote_handler(self, temp_project):
        """Test note.promote handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.notes import create_note

        create_note("Title\nBody")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["note.promote"]
        result = await handler({"id": 1, "to": "task"}, conn)

        assert result["title"] == "Title"

    @pytest.mark.asyncio
    async def test_explore_list_handler(self, temp_project):
        """Test explore.list handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.explorations import create_exploration

        create_exploration("Exp 1")
        create_exploration("Exp 2")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["explore.list"]
        result = await handler({"state": "open"}, conn)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_explore_get_handler(self, temp_project):
        """Test explore.get handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.explorations import create_exploration

        create_exploration("Test exploration")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["explore.get"]
        result = await handler({"id": 1}, conn)

        assert result["title"] == "Test exploration"

    @pytest.mark.asyncio
    async def test_explore_close_handler(self, temp_project):
        """Test explore.close handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.explorations import create_exploration

        create_exploration("To close")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)
        server.broadcast = AsyncMock()

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["explore.close"]
        result = await handler({"id": 1}, conn)

        assert result["state"] == "closed"
        server.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_plan_list_handler(self, temp_project):
        """Test plan.list handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.plans import create_plan

        create_plan("plan-a")
        create_plan("plan-b")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["plan.list"]
        result = await handler({}, conn)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_plan_get_handler(self, temp_project):
        """Test plan.get handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.plans import create_plan

        create_plan("my-plan")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["plan.get"]
        result = await handler({"name": "my-plan"}, conn)

        assert result["name"] == "my-plan"

    @pytest.mark.asyncio
    async def test_plan_current_handler(self, temp_project):
        """Test plan.current handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.plans import create_plan, switch_plan

        create_plan("my-plan")
        switch_plan("my-plan")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["plan.current"]
        result = await handler({}, conn)

        assert result["name"] == "my-plan"

    @pytest.mark.asyncio
    async def test_plan_switch_handler(self, temp_project):
        """Test plan.switch handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.plans import create_plan

        create_plan("my-plan")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)
        server.broadcast = AsyncMock()

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["plan.switch"]
        result = await handler({"name": "my-plan"}, conn)

        assert result["name"] == "my-plan"
        server.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_reference_list_handler(self, temp_project):
        """Test reference.list handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.reference import add_reference

        add_reference("Ref 1")
        add_reference("Ref 2")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["reference.list"]
        result = await handler({}, conn)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_reference_get_handler(self, temp_project):
        """Test reference.get handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.reference import add_reference

        add_reference("API Guide")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["reference.get"]
        result = await handler({"title": "API Guide"}, conn)

        assert result["title"] == "API Guide"

    @pytest.mark.asyncio
    async def test_reference_update_handler(self, temp_project):
        """Test reference.update handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.reference import add_reference

        add_reference("Original", body="Old content")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)
        server.broadcast = AsyncMock()

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["reference.update"]
        result = await handler({"title": "Original", "body": "New content"}, conn)

        assert result["body"] == "New content"
        server.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_reference_search_handler(self, temp_project):
        """Test reference.search handler."""
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.reference import add_reference

        add_reference("Python Guide")
        add_reference("Other Doc")

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["reference.search"]
        result = await handler({"query": "python"}, conn)

        assert len(result) == 1
        assert result[0]["title"] == "Python Guide"

    @pytest.mark.asyncio
    async def test_run_list_handler(self, temp_project):
        """Test run.list handler."""
        import time
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.runs import start_run

        start_run("echo hello", name="run-1")
        time.sleep(0.3)

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["run.list"]
        result = await handler({}, conn)

        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_run_status_handler(self, temp_project):
        """Test run.status handler."""
        import time
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.runs import start_run

        start_run("echo hello", name="status-run")
        time.sleep(0.3)

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["run.status"]
        result = await handler({"name": "status-run"}, conn)

        assert result is not None

    @pytest.mark.asyncio
    async def test_run_logs_handler(self, temp_project):
        """Test run.logs handler."""
        import time
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.runs import start_run

        start_run("echo hello", name="log-run")
        time.sleep(0.5)

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["run.logs"]
        result = await handler({"name": "log-run", "stream": "stdout"}, conn)

        assert "hello" in result

    @pytest.mark.asyncio
    async def test_run_stop_handler(self, temp_project):
        """Test run.stop handler."""
        import time
        from idlergear.daemon.handlers import register_handlers
        from idlergear.daemon.server import DaemonServer
        from idlergear.runs import start_run

        start_run("sleep 60", name="stop-run")
        time.sleep(0.3)

        socket_path = temp_project / ".idlergear" / "daemon.sock"
        pid_path = temp_project / ".idlergear" / "daemon.pid"
        storage_path = temp_project / ".idlergear" / "storage"
        storage_path.mkdir(exist_ok=True)
        server = DaemonServer(socket_path, pid_path, storage_path)

        register_handlers(server)

        conn = MagicMock()
        handler = server._methods["run.stop"]
        result = await handler({"name": "stop-run"}, conn)

        assert result is True

"""Integration tests for file registry daemon integration.

Tests the complete daemon integration including:
- Registry handlers broadcasting events
- Multiple agents receiving broadcasts
- MCP server subscription to registry events

Related to Issue #291.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture
def temp_registry(tmp_path):
    """Create temporary file registry."""
    registry_dir = tmp_path / ".idlergear"
    registry_dir.mkdir()
    registry_file = registry_dir / "file_registry.json"
    registry_file.write_text(json.dumps({"files": {}, "patterns": {}}))
    return registry_file


class TestRegistryDaemonHandlers:
    """Test daemon handlers for file registry operations."""

    @pytest.mark.asyncio
    async def test_file_register_broadcasts_event(self, temp_registry):
        """Test that file_register handler broadcasts events."""
        from idlergear.daemon.server import DaemonServer

        # Create mock server
        server = Mock(spec=DaemonServer)
        server.broadcast = AsyncMock()
        server.storage_path = temp_registry.parent

        # Import and register handlers
        from idlergear.daemon.handlers import register_handlers

        register_handlers(server)

        # Get the file_register handler
        handlers = {
            name: handler
            for name, handler in server.register_method.call_args_list
        }
        file_register = None
        for call in server.register_method.call_args_list:
            if call[0][0] == "file.register":
                file_register = call[0][1]
                break

        assert file_register is not None, "file.register handler not registered"

        # Mock connection
        conn = Mock()

        # Call handler with patch to use temp registry
        with patch(
            "idlergear.file_registry.FileRegistry.__init__",
            lambda self, registry_path=None, lazy_load=True, storage_backend=None: setattr(
                self, "registry_path", temp_registry
            )
            or setattr(self, "files", {})
            or setattr(self, "patterns", {})
            or setattr(self, "_status_cache", {})
            or setattr(self, "_loaded", True)
            or setattr(self, "_patterns_loaded", True)
            or setattr(self, "_last_load_time", None)
            or setattr(self, "_legacy_path", temp_registry)
            or setattr(
                self,
                "_event_callbacks",
                {"file_registered": [], "file_deprecated": []},
            )
            or setattr(self, "storage", __import__('idlergear.file_annotation_storage', fromlist=['FileAnnotationStorage']).FileAnnotationStorage(temp_registry.parent / "file_annotations")),
        ):
            result = await file_register(
                {
                    "path": "test.txt",
                    "status": "current",
                    "reason": "Test file",
                },
                conn,
            )

        # Verify result
        assert result["success"] is True
        assert result["path"] == "test.txt"
        assert result["status"] == "current"

        # Verify broadcast was called
        server.broadcast.assert_called_once()
        call_args = server.broadcast.call_args
        assert call_args[0][0] == "file.registered"
        assert call_args[0][1]["path"] == "test.txt"
        assert call_args[0][1]["status"] == "current"
        assert call_args[0][1]["reason"] == "Test file"

    @pytest.mark.asyncio
    async def test_file_deprecate_broadcasts_event(self, temp_registry):
        """Test that file_deprecate handler broadcasts events."""
        from idlergear.daemon.server import DaemonServer

        # Create mock server
        server = Mock(spec=DaemonServer)
        server.broadcast = AsyncMock()
        server.storage_path = temp_registry.parent

        # Import and register handlers
        from idlergear.daemon.handlers import register_handlers

        register_handlers(server)

        # Get the file_deprecate handler
        file_deprecate = None
        for call in server.register_method.call_args_list:
            if call[0][0] == "file.deprecate":
                file_deprecate = call[0][1]
                break

        assert file_deprecate is not None, "file.deprecate handler not registered"

        # Mock connection
        conn = Mock()

        # Call handler with patch to use temp registry
        with patch(
            "idlergear.file_registry.FileRegistry.__init__",
            lambda self, registry_path=None, lazy_load=True, storage_backend=None: setattr(
                self, "registry_path", temp_registry
            )
            or setattr(self, "files", {})
            or setattr(self, "patterns", {})
            or setattr(self, "_status_cache", {})
            or setattr(self, "_loaded", True)
            or setattr(self, "_patterns_loaded", True)
            or setattr(self, "_last_load_time", None)
            or setattr(self, "_legacy_path", temp_registry)
            or setattr(
                self,
                "_event_callbacks",
                {"file_registered": [], "file_deprecated": []},
            )
            or setattr(self, "storage", __import__('idlergear.file_annotation_storage', fromlist=['FileAnnotationStorage']).FileAnnotationStorage(temp_registry.parent / "file_annotations")),
        ):
            result = await file_deprecate(
                {
                    "path": "old.txt",
                    "successor": "new.txt",
                    "reason": "Updated version",
                },
                conn,
            )

        # Verify result
        assert result["success"] is True
        assert result["path"] == "old.txt"
        assert result["successor"] == "new.txt"

        # Verify broadcast was called
        server.broadcast.assert_called_once()
        call_args = server.broadcast.call_args
        assert call_args[0][0] == "file.deprecated"
        assert call_args[0][1]["path"] == "old.txt"
        assert call_args[0][1]["successor"] == "new.txt"
        assert call_args[0][1]["reason"] == "Updated version"


class TestMultiAgentCoordination:
    """Test multi-agent coordination for file registry updates."""

    @pytest.mark.asyncio
    async def test_daemon_broadcasts_to_multiple_agents(self, tmp_path):
        """Test that daemon broadcasts registry events to all subscribed agents."""
        from idlergear.daemon.protocol import parse_message
        from idlergear.daemon.server import Connection, DaemonServer

        # Create daemon server
        socket_path = tmp_path / "daemon.sock"
        pid_path = tmp_path / "daemon.pid"
        storage_path = tmp_path / ".idlergear"
        storage_path.mkdir()
        server = DaemonServer(socket_path, pid_path, storage_path)

        # Create two mock agent connections
        agent1 = Mock(spec=Connection)
        agent1.subscriptions = {"file.*"}
        agent1.send = AsyncMock()

        agent2 = Mock(spec=Connection)
        agent2.subscriptions = {"file.*"}
        agent2.send = AsyncMock()

        # Add to server connections dictionary
        server._connections = {1: agent1, 2: agent2}

        # Broadcast a file.registered event
        await server.broadcast(
            "file.registered",
            {
                "path": "test.py",
                "status": "current",
                "reason": "New file",
            },
        )

        # Both agents should have received the notification
        assert agent1.send.called
        assert agent2.send.called

        # Verify notification content for agent1
        notification_json = agent1.send.call_args[0][0]
        notification = parse_message(notification_json)
        assert notification.method == "event"
        assert notification.params["event"] == "file.registered"
        assert notification.params["data"]["path"] == "test.py"
        assert notification.params["data"]["status"] == "current"

    @pytest.mark.asyncio
    async def test_wildcard_subscription_matches_registry_events(self, tmp_path):
        """Test that wildcard subscriptions match file registry events."""
        from idlergear.daemon.server import Connection, DaemonServer

        socket_path = tmp_path / "daemon.sock"
        pid_path = tmp_path / "daemon.pid"
        storage_path = tmp_path / ".idlergear"
        storage_path.mkdir()
        server = DaemonServer(socket_path, pid_path, storage_path)

        # Agent subscribed to "file.*"
        agent = Mock(spec=Connection)
        agent.subscriptions = {"file.*"}
        agent.send = AsyncMock()
        server._connections = {1: agent}

        # Test file.registered
        await server.broadcast("file.registered", {"path": "test1.py"})
        assert agent.send.call_count == 1

        # Test file.deprecated
        await server.broadcast("file.deprecated", {"path": "test2.py"})
        assert agent.send.call_count == 2

        # Test unrelated event (should not match)
        await server.broadcast("task.created", {"id": 1})
        # Count should still be 2 (no new send)
        assert agent.send.call_count == 2


class TestMCPServerSubscription:
    """Test MCP server subscription to registry events."""

    @pytest.mark.asyncio
    async def test_mcp_server_subscribes_on_startup(self, tmp_path):
        """Test that MCP server subscribes to file.* events on startup."""
        from unittest.mock import MagicMock

        from idlergear.daemon.client import DaemonClient

        # Mock daemon client
        mock_client = MagicMock(spec=DaemonClient)
        mock_client.connect = AsyncMock()
        mock_client.subscribe = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        # Create a subscription task that we can control
        async def mock_subscribe_task():
            await mock_client.connect()
            await mock_client.subscribe("file.*")
            # Simulate keeping connection alive briefly
            await asyncio.sleep(0.1)

        # Run the subscription logic
        with patch(
            "idlergear.config.find_idlergear_root", return_value=tmp_path
        ), patch(
            "idlergear.daemon.client.get_daemon_client", return_value=mock_client
        ):
            # Import and run subscription function
            from idlergear.mcp_server import _subscribe_to_registry_events

            task = asyncio.create_task(_subscribe_to_registry_events())

            # Give it time to subscribe
            await asyncio.sleep(0.2)

            # Cancel the task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Verify subscription was called
        mock_client.connect.assert_called_once()
        mock_client.subscribe.assert_called_once_with("file.*")

    @pytest.mark.asyncio
    async def test_mcp_server_handles_daemon_not_running(self, tmp_path):
        """Test that MCP server handles daemon not running gracefully."""
        from idlergear.daemon.client import DaemonNotRunning

        # Mock daemon client that raises DaemonNotRunning
        async def mock_connect_fails():
            raise DaemonNotRunning("Daemon not running")

        with patch(
            "idlergear.config.find_idlergear_root", return_value=tmp_path
        ), patch(
            "idlergear.daemon.client.get_daemon_client"
        ) as mock_get_client:
            mock_client = Mock()
            mock_client.connect = mock_connect_fails
            mock_get_client.return_value = mock_client

            # Import and run subscription function
            from idlergear.mcp_server import _subscribe_to_registry_events

            # Should not raise exception
            task = asyncio.create_task(_subscribe_to_registry_events())
            await asyncio.sleep(0.1)

            # Task should have completed without error
            assert task.done() or task.cancelled()


class TestRegistryEventCallbacks:
    """Test FileRegistry event callback system."""

    def test_registry_emits_file_registered_event(self, temp_registry):
        """Test that FileRegistry emits file_registered events."""
        from idlergear.file_registry import FileRegistry, FileStatus

        registry = FileRegistry(registry_path=temp_registry)

        # Register callback
        events_received = []

        def callback(data):
            events_received.append(data)

        registry.on("file_registered", callback)

        # Register a file
        registry.register_file(
            "test.py",
            FileStatus.CURRENT,
            reason="Test file",
        )

        # Verify event was emitted
        assert len(events_received) == 1
        assert events_received[0]["path"] == "test.py"
        assert events_received[0]["status"] == "current"
        assert events_received[0]["reason"] == "Test file"
        assert "timestamp" in events_received[0]

    def test_registry_emits_file_deprecated_event(self, temp_registry):
        """Test that FileRegistry emits file_deprecated events."""
        from idlergear.file_registry import FileRegistry

        registry = FileRegistry(registry_path=temp_registry)

        # Register callback
        events_received = []

        def callback(data):
            events_received.append(data)

        registry.on("file_deprecated", callback)

        # Deprecate a file
        registry.deprecate_file(
            "old.py",
            successor="new.py",
            reason="Updated version",
        )

        # Verify event was emitted
        assert len(events_received) == 1
        assert events_received[0]["path"] == "old.py"
        assert events_received[0]["successor"] == "new.py"
        assert events_received[0]["reason"] == "Updated version"
        assert "timestamp" in events_received[0]

    def test_callback_failure_does_not_break_registry(self, temp_registry):
        """Test that callback failures don't break registry operations."""
        from idlergear.file_registry import FileRegistry, FileStatus

        registry = FileRegistry(registry_path=temp_registry)

        # Register failing callback
        def bad_callback(data):
            raise ValueError("Callback failed")

        registry.on("file_registered", bad_callback)

        # Register a file - should not raise exception
        registry.register_file(
            "test.py",
            FileStatus.CURRENT,
        )

        # Verify file was registered despite callback failure
        assert "test.py" in registry.files

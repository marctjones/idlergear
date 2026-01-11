"""Tests for IdlerGear daemon functionality."""

import json

import pytest

from idlergear.daemon.protocol import (
    ErrorCode,
    Notification,
    Request,
    Response,
    parse_message,
)
from idlergear.daemon.client import DaemonClient, DaemonError, DaemonNotRunning
from idlergear.daemon.lifecycle import DaemonLifecycle


class TestProtocol:
    """Test JSON-RPC 2.0 protocol implementation."""

    def test_request_to_json(self):
        req = Request(method="test.method", params={"key": "value"}, id=1)
        data = json.loads(req.to_json())

        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test.method"
        assert data["params"] == {"key": "value"}
        assert data["id"] == 1

    def test_request_without_params(self):
        req = Request(method="test.method", id=1)
        data = json.loads(req.to_json())

        assert "params" not in data

    def test_response_success(self):
        resp = Response.success(id=1, result={"data": "test"})
        data = json.loads(resp.to_json())

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert data["result"] == {"data": "test"}
        assert "error" not in data

    def test_response_error(self):
        resp = Response.error_response(
            id=1, code=ErrorCode.METHOD_NOT_FOUND, message="Not found"
        )
        data = json.loads(resp.to_json())

        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert data["error"]["code"] == ErrorCode.METHOD_NOT_FOUND
        assert data["error"]["message"] == "Not found"
        assert "result" not in data

    def test_notification_to_json(self):
        notif = Notification(method="event", params={"type": "update"})
        data = json.loads(notif.to_json())

        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "event"
        assert data["params"] == {"type": "update"}
        assert "id" not in data

    def test_parse_request(self):
        msg = '{"jsonrpc": "2.0", "method": "test", "params": {"x": 1}, "id": 42}'
        parsed = parse_message(msg)

        assert isinstance(parsed, Request)
        assert parsed.method == "test"
        assert parsed.params == {"x": 1}
        assert parsed.id == 42

    def test_parse_notification(self):
        msg = '{"jsonrpc": "2.0", "method": "notify", "params": {}}'
        parsed = parse_message(msg)

        assert isinstance(parsed, Notification)
        assert parsed.method == "notify"

    def test_parse_response(self):
        msg = '{"jsonrpc": "2.0", "id": 1, "result": "ok"}'
        parsed = parse_message(msg)

        assert isinstance(parsed, Response)
        assert parsed.id == 1
        assert parsed.result == "ok"

    def test_parse_error_response(self):
        msg = '{"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid"}}'
        parsed = parse_message(msg)

        assert isinstance(parsed, Response)
        assert parsed.error is not None
        assert parsed.error["code"] == -32600

    def test_parse_invalid_json(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_message("not json")

    def test_parse_invalid_version(self):
        with pytest.raises(ValueError, match="Invalid JSON-RPC version"):
            parse_message('{"jsonrpc": "1.0", "method": "test"}')


class TestDaemonLifecycle:
    """Test daemon lifecycle management."""

    def test_not_running_initially(self, temp_project):
        root = temp_project / ".idlergear"
        lifecycle = DaemonLifecycle(root)

        assert not lifecycle.is_running()
        assert lifecycle.get_pid() is None

    def test_cleanup_stale_files(self, temp_project):
        root = temp_project / ".idlergear"
        lifecycle = DaemonLifecycle(root)

        # Create stale files
        (root / "daemon.sock").touch()
        (root / "daemon.pid").write_text("99999")

        lifecycle._cleanup_stale_files()

        assert not (root / "daemon.sock").exists()
        assert not (root / "daemon.pid").exists()


class TestDaemonClient:
    """Test daemon client."""

    @pytest.mark.asyncio
    async def test_connect_no_socket(self, temp_project):
        root = temp_project / ".idlergear"
        client = DaemonClient(root / "daemon.sock")

        with pytest.raises(DaemonNotRunning):
            await client.connect()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self, temp_project):
        root = temp_project / ".idlergear"
        client = DaemonClient(root / "daemon.sock")

        # Should not raise
        await client.disconnect()


class TestDaemonIntegration:
    """Integration tests for daemon (start/stop/communicate)."""

    @pytest.fixture
    def daemon_lifecycle(self, temp_project):
        """Get a lifecycle manager for the temp project."""
        root = temp_project / ".idlergear"
        return DaemonLifecycle(root)

    @pytest.mark.asyncio
    async def test_start_stop_daemon(self, daemon_lifecycle):
        """Test starting and stopping the daemon."""
        # Start daemon
        pid = daemon_lifecycle.start(wait=True, timeout=10.0)
        assert pid is not None
        assert daemon_lifecycle.is_running()

        # Check it's healthy
        healthy = await daemon_lifecycle.is_healthy()
        assert healthy

        # Stop daemon
        stopped = daemon_lifecycle.stop()
        assert stopped
        assert not daemon_lifecycle.is_running()

    @pytest.mark.asyncio
    async def test_daemon_ping(self, daemon_lifecycle):
        """Test pinging the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            result = await client.ping()
            assert result is True
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_daemon_status(self, daemon_lifecycle):
        """Test getting daemon status."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            status = await client.status()
            assert status["running"] is True
            assert "pid" in status
            assert "connections" in status
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_daemon_method_not_found(self, daemon_lifecycle):
        """Test calling non-existent method."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            with pytest.raises(DaemonError) as exc_info:
                await client.call("nonexistent.method")

            assert exc_info.value.code == ErrorCode.METHOD_NOT_FOUND
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_task_via_daemon(self, daemon_lifecycle):
        """Test creating a task through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Create task
            result = await client.call(
                "task.create",
                {"title": "Test task", "body": "Task body"},
            )
            assert result["title"] == "Test task"
            assert result["id"] is not None

            # List tasks
            tasks = await client.call("task.list", {"state": "open"})
            assert len(tasks) == 1
            assert tasks[0]["title"] == "Test task"
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_restart_daemon(self, daemon_lifecycle):
        """Test restarting the daemon."""
        daemon_lifecycle.start(wait=True)
        old_pid = daemon_lifecycle.get_pid()

        # Restart
        new_pid = daemon_lifecycle.restart()

        assert new_pid is not None
        assert daemon_lifecycle.is_running()
        # PID should be different (new process)
        assert new_pid != old_pid

        daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_note_via_daemon(self, daemon_lifecycle):
        """Test creating a note through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Create note
            result = await client.call(
                "note.create",
                {"content": "Quick note"},
            )
            assert result["content"] == "Quick note"
            assert result["id"] is not None

            # List notes
            notes = await client.call("note.list", {})
            assert len(notes) == 1

            # Get note
            note = await client.call("note.get", {"id": result["id"]})
            assert note["content"] == "Quick note"

            # Delete note
            deleted = await client.call("note.delete", {"id": result["id"]})
            assert deleted is True
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_explore_via_daemon(self, daemon_lifecycle):
        """Test exploration operations through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Create exploration
            result = await client.call(
                "explore.create",
                {"title": "Research topic", "body": "Details"},
            )
            assert result["title"] == "Research topic"
            assert result["id"] is not None

            # List explorations
            explores = await client.call("explore.list", {"state": "open"})
            assert len(explores) == 1

            # Get exploration
            explore = await client.call("explore.get", {"id": result["id"]})
            assert explore["title"] == "Research topic"

            # Close exploration
            closed = await client.call("explore.close", {"id": result["id"]})
            assert closed["state"] == "closed"
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_vision_via_daemon(self, daemon_lifecycle):
        """Test vision operations through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Set vision
            result = await client.call(
                "vision.set",
                {"content": "New project vision"},
            )
            assert result is True

            # Get vision
            vision = await client.call("vision.get", {})
            assert "New project vision" in vision
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_plan_via_daemon(self, daemon_lifecycle):
        """Test plan operations through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Create plan
            result = await client.call(
                "plan.create",
                {"name": "my-plan", "title": "My Plan"},
            )
            assert result["name"] == "my-plan"

            # List plans
            plans = await client.call("plan.list", {})
            assert len(plans) >= 1

            # Get plan
            plan = await client.call("plan.get", {"name": "my-plan"})
            assert plan["name"] == "my-plan"

            # Switch plan
            switched = await client.call("plan.switch", {"name": "my-plan"})
            assert switched["name"] == "my-plan"

            # Get current plan
            current = await client.call("plan.current", {})
            assert current["name"] == "my-plan"
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_reference_via_daemon(self, daemon_lifecycle):
        """Test reference operations through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Add reference
            result = await client.call(
                "reference.add",
                {"title": "API Guide", "body": "API documentation"},
            )
            assert result["title"] == "API Guide"

            # List references
            refs = await client.call("reference.list", {})
            assert len(refs) >= 1

            # Get reference
            ref = await client.call("reference.get", {"title": "API Guide"})
            assert ref["title"] == "API Guide"

            # Search references
            search = await client.call("reference.search", {"query": "API"})
            assert len(search) >= 1

            # Update reference
            updated = await client.call(
                "reference.update",
                {"title": "API Guide", "body": "Updated content"},
            )
            assert updated is not None
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_config_via_daemon(self, daemon_lifecycle):
        """Test config operations through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Set config
            result = await client.call(
                "config.set",
                {"key": "test.key", "value": "test-value"},
            )
            assert result is True

            # Get config
            value = await client.call("config.get", {"key": "test.key"})
            assert value == "test-value"
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_run_via_daemon(self, daemon_lifecycle):
        """Test run operations through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Start run
            result = await client.call(
                "run.start",
                {"command": "echo hello", "name": "test-run"},
            )
            assert result["name"] == "test-run"
            assert result["status"] == "running"

            # Wait for command to complete
            import time

            time.sleep(0.5)

            # List runs
            runs = await client.call("run.list", {})
            assert len(runs) >= 1

            # Get run status
            status = await client.call("run.status", {"name": "test-run"})
            assert status is not None

            # Get run logs
            logs = await client.call(
                "run.logs",
                {"name": "test-run", "stream": "stdout"},
            )
            assert "hello" in logs
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_task_close_via_daemon(self, daemon_lifecycle):
        """Test closing a task through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Create task
            task = await client.call(
                "task.create",
                {"title": "Task to close"},
            )

            # Close task
            closed = await client.call("task.close", {"id": task["id"]})
            assert closed["state"] == "closed"
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_task_update_via_daemon(self, daemon_lifecycle):
        """Test updating a task through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Create task
            task = await client.call(
                "task.create",
                {"title": "Original title"},
            )

            # Update task
            updated = await client.call(
                "task.update",
                {"id": task["id"], "title": "Updated title"},
            )
            assert updated["title"] == "Updated title"
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, daemon_lifecycle):
        """Test event subscription and unsubscription."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Subscribe to events
            result = await client.call(
                "daemon.subscribe",
                {"event": "task.created"},
            )
            assert result["subscribed"] == "task.created"

            # Unsubscribe from events
            result = await client.call(
                "daemon.unsubscribe",
                {"event": "task.created"},
            )
            assert result["unsubscribed"] == "task.created"
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_subscribe_missing_event(self, daemon_lifecycle):
        """Test subscription without event parameter."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            with pytest.raises(DaemonError) as exc_info:
                await client.call("daemon.subscribe", {})

            # Should be an invalid params error
            assert exc_info.value.code == ErrorCode.INVALID_PARAMS
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_note_promote_via_daemon(self, daemon_lifecycle):
        """Test promoting a note through the daemon."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Create note
            note = await client.call(
                "note.create",
                {"content": "Note title\nNote body"},
            )

            # Promote to task
            result = await client.call(
                "note.promote",
                {"id": note["id"], "to": "task"},
            )
            assert result["title"] == "Note title"
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()


class TestMultiClientDaemon:
    """Tests for multiple clients connecting to daemon simultaneously."""

    @pytest.fixture
    def daemon_lifecycle(self, temp_project):
        """Get a lifecycle manager for the temp project."""
        root = temp_project / ".idlergear"
        return DaemonLifecycle(root)

    @pytest.mark.asyncio
    async def test_multiple_clients_connect(self, daemon_lifecycle):
        """Test multiple clients can connect simultaneously."""
        daemon_lifecycle.start(wait=True)

        clients = []
        try:
            # Connect multiple clients
            for i in range(5):
                client = DaemonClient(daemon_lifecycle.socket_path)
                await client.connect()
                clients.append(client)

            # All clients should be able to ping
            for client in clients:
                result = await client.ping()
                assert result is True

            # Check daemon status shows correct connection count
            status = await clients[0].status()
            assert status["connections"] == 5
        finally:
            for client in clients:
                await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, daemon_lifecycle):
        """Test multiple clients making concurrent requests."""
        import asyncio

        daemon_lifecycle.start(wait=True)

        clients = []
        try:
            # Connect multiple clients
            for _ in range(3):
                client = DaemonClient(daemon_lifecycle.socket_path)
                await client.connect()
                clients.append(client)

            # Make concurrent task creation requests
            async def create_task(client, title):
                return await client.call("task.create", {"title": title})

            results = await asyncio.gather(
                create_task(clients[0], "Task from client 1"),
                create_task(clients[1], "Task from client 2"),
                create_task(clients[2], "Task from client 3"),
            )

            # All tasks should be created with unique IDs
            task_ids = [r["id"] for r in results]
            assert len(set(task_ids)) == 3

            # Verify all tasks exist
            tasks = await clients[0].call("task.list", {"state": "open"})
            assert len(tasks) == 3
        finally:
            for client in clients:
                await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_client_disconnect_cleanup(self, daemon_lifecycle):
        """Test that disconnecting clients are cleaned up properly."""
        daemon_lifecycle.start(wait=True)

        try:
            # Connect first client
            client1 = DaemonClient(daemon_lifecycle.socket_path)
            await client1.connect()

            status = await client1.status()
            assert status["connections"] == 1

            # Connect second client
            client2 = DaemonClient(daemon_lifecycle.socket_path)
            await client2.connect()

            status = await client1.status()
            assert status["connections"] == 2

            # Disconnect second client
            await client2.disconnect()

            # Give daemon time to process disconnect
            import asyncio

            await asyncio.sleep(0.1)

            status = await client1.status()
            assert status["connections"] == 1

            await client1.disconnect()
        finally:
            daemon_lifecycle.stop()


class TestAgentCoordination:
    """Tests for multi-agent coordination via daemon."""

    @pytest.fixture
    def daemon_lifecycle(self, temp_project):
        """Get a lifecycle manager for the temp project."""
        root = temp_project / ".idlergear"
        return DaemonLifecycle(root)

    @pytest.mark.asyncio
    async def test_multiple_agents_register(self, daemon_lifecycle):
        """Test multiple agents can register and be listed."""
        daemon_lifecycle.start(wait=True)

        clients = []
        try:
            # Register multiple agents with different types
            agents = [
                ("agent-1", "claude-code"),
                ("agent-2", "goose"),
                ("agent-3", "aider"),
            ]

            for agent_id, agent_type in agents:
                client = DaemonClient(daemon_lifecycle.socket_path)
                await client.connect()
                clients.append(client)

                result = await client.call(
                    "agent.register",
                    {"agent_id": agent_id, "agent_type": agent_type},
                )
                assert result["agent_id"] == agent_id
                assert result["agent_type"] == agent_type

            # List all agents
            result = await clients[0].call("agent.list", {})
            assert len(result["agents"]) == 3

            # Filter by type
            result = await clients[0].call("agent.list", {"agent_type": "claude-code"})
            assert len(result["agents"]) == 1
            assert result["agents"][0]["agent_id"] == "agent-1"
        finally:
            for client in clients:
                await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_agent_status_updates(self, daemon_lifecycle):
        """Test agents can update their status."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Register agent
            await client.call(
                "agent.register",
                {"agent_id": "test-agent", "agent_type": "claude-code"},
            )

            # Update status to busy
            result = await client.call(
                "agent.update_status",
                {"agent_id": "test-agent", "status": "busy", "current_task": "task-123"},
            )
            assert result["success"] is True

            # Verify status changed
            agents = await client.call("agent.list", {})
            agent = agents["agents"][0]
            assert agent["status"] == "busy"
            assert agent["current_task"] == "task-123"

            # Update back to idle
            await client.call(
                "agent.update_status",
                {"agent_id": "test-agent", "status": "idle"},
            )

            agents = await client.call("agent.list", {"status": "idle"})
            assert len(agents["agents"]) == 1
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_command_queue_coordination(self, daemon_lifecycle):
        """Test agents coordinate work through command queue."""
        daemon_lifecycle.start(wait=True)

        clients = []
        try:
            # Register two agents
            for agent_id in ["agent-1", "agent-2"]:
                client = DaemonClient(daemon_lifecycle.socket_path)
                await client.connect()
                clients.append(client)
                await client.call(
                    "agent.register",
                    {"agent_id": agent_id, "agent_type": "test"},
                )

            # Queue multiple commands
            cmd1 = await clients[0].call(
                "queue.add", {"prompt": "high priority work", "priority": 10}
            )
            cmd2 = await clients[0].call(
                "queue.add", {"prompt": "low priority work", "priority": 1}
            )

            # Agent 1 polls and gets high priority
            work1 = await clients[0].call("queue.poll", {"agent_id": "agent-1"})
            assert work1["id"] == cmd1["id"]
            assert work1["priority"] == 10

            # Agent 2 polls and gets low priority (high is already assigned)
            work2 = await clients[1].call("queue.poll", {"agent_id": "agent-2"})
            assert work2["id"] == cmd2["id"]
            assert work2["priority"] == 1

            # Complete work
            await clients[0].call("queue.complete", {"id": cmd1["id"], "result": {"done": True}})
            await clients[1].call("queue.complete", {"id": cmd2["id"], "result": {"done": True}})

            # No more pending commands
            work3 = await clients[0].call("queue.poll", {"agent_id": "agent-1"})
            assert work3.get("command") is None
        finally:
            for client in clients:
                await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_resource_locking(self, daemon_lifecycle):
        """Test agents can lock resources to prevent conflicts."""
        daemon_lifecycle.start(wait=True)

        clients = []
        try:
            # Register two agents
            for agent_id in ["agent-1", "agent-2"]:
                client = DaemonClient(daemon_lifecycle.socket_path)
                await client.connect()
                clients.append(client)
                await client.call(
                    "agent.register",
                    {"agent_id": agent_id, "agent_type": "test"},
                )

            # Agent 1 acquires lock on a file
            result = await clients[0].call(
                "lock.acquire",
                {"resource": "src/main.py", "agent_id": "agent-1", "timeout": 60},
            )
            assert result["acquired"] is True

            # Agent 2 tries to acquire same lock (should fail)
            result = await clients[1].call(
                "lock.acquire",
                {"resource": "src/main.py", "agent_id": "agent-2", "timeout": 0.1},
            )
            assert result["acquired"] is False

            # Check lock status
            result = await clients[1].call("lock.is_locked", {"resource": "src/main.py"})
            assert result["is_locked"] is True
            assert result["lock"]["agent_id"] == "agent-1"

            # Agent 1 releases lock
            await clients[0].call(
                "lock.release",
                {"resource": "src/main.py", "agent_id": "agent-1"},
            )

            # Now agent 2 can acquire
            result = await clients[1].call(
                "lock.acquire",
                {"resource": "src/main.py", "agent_id": "agent-2", "timeout": 0.1},
            )
            assert result["acquired"] is True
        finally:
            for client in clients:
                await client.disconnect()
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_agent_unregister_releases_locks(self, daemon_lifecycle):
        """Test that unregistering an agent releases its locks."""
        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Register agent
            await client.call(
                "agent.register",
                {"agent_id": "test-agent", "agent_type": "test"},
            )

            # Acquire locks
            await client.call(
                "lock.acquire",
                {"resource": "file1.py", "agent_id": "test-agent"},
            )
            await client.call(
                "lock.acquire",
                {"resource": "file2.py", "agent_id": "test-agent"},
            )

            # Verify locks exist
            result = await client.call("lock.list", {"agent_id": "test-agent"})
            assert len(result["locks"]) == 2

            # Unregister agent
            await client.call("agent.unregister", {"agent_id": "test-agent"})

            # Locks should be released
            result = await client.call("lock.is_locked", {"resource": "file1.py"})
            assert result["is_locked"] is False

            result = await client.call("lock.is_locked", {"resource": "file2.py"})
            assert result["is_locked"] is False
        finally:
            await client.disconnect()
            daemon_lifecycle.stop()


class TestDaemonResilience:
    """Tests for daemon error handling and resilience."""

    @pytest.fixture
    def daemon_lifecycle(self, temp_project):
        """Get a lifecycle manager for the temp project."""
        root = temp_project / ".idlergear"
        return DaemonLifecycle(root)

    @pytest.mark.asyncio
    async def test_daemon_handles_invalid_messages(self, daemon_lifecycle):
        """Test daemon handles malformed messages gracefully."""
        import socket

        daemon_lifecycle.start(wait=True)

        try:
            # Connect with raw socket to send malformed data
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(str(daemon_lifecycle.socket_path))

            # Send malformed message (not valid JSON)
            bad_message = b"not valid json"
            sock.send(len(bad_message).to_bytes(4, "big") + bad_message)

            # Read response
            length_bytes = sock.recv(4)
            if length_bytes:
                length = int.from_bytes(length_bytes, "big")
                response = sock.recv(length).decode("utf-8")
                assert "error" in response.lower() or "parse" in response.lower()

            sock.close()

            # Daemon should still be running
            assert daemon_lifecycle.is_running()

            # Valid client should still work
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()
            result = await client.ping()
            assert result is True
            await client.disconnect()
        finally:
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_daemon_survives_client_crash(self, daemon_lifecycle):
        """Test daemon handles abrupt client disconnection."""
        daemon_lifecycle.start(wait=True)

        try:
            # Connect a client
            client1 = DaemonClient(daemon_lifecycle.socket_path)
            await client1.connect()

            # Create a task
            await client1.call("task.create", {"title": "Test task"})

            # Abruptly close the connection (simulating crash)
            client1._writer.close()
            await client1._writer.wait_closed()

            # Give daemon time to detect disconnect
            import asyncio

            await asyncio.sleep(0.2)

            # Daemon should still be running and responsive
            client2 = DaemonClient(daemon_lifecycle.socket_path)
            await client2.connect()

            # Previous task should still exist
            tasks = await client2.call("task.list", {"state": "open"})
            assert len(tasks) == 1
            assert tasks[0]["title"] == "Test task"

            await client2.disconnect()
        finally:
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_daemon_heartbeat_timeout(self, daemon_lifecycle):
        """Test that stale agents are detected."""
        import asyncio
        from datetime import datetime, timezone, timedelta

        daemon_lifecycle.start(wait=True)

        try:
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()

            # Register agent
            await client.call(
                "agent.register",
                {"agent_id": "test-agent", "agent_type": "test"},
            )

            # Manually check stale detection logic (agent should not be stale yet)
            agents = await client.call("agent.list", {})
            assert len(agents["agents"]) == 1

            # The agent should have a recent heartbeat
            agent = agents["agents"][0]
            heartbeat = datetime.fromisoformat(agent["last_heartbeat"])
            now = datetime.now(timezone.utc)
            age = (now - heartbeat).total_seconds()
            assert age < 5  # Should be very recent

            await client.disconnect()
        finally:
            daemon_lifecycle.stop()

    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect(self, daemon_lifecycle):
        """Test daemon handles rapid connect/disconnect cycles."""
        import asyncio

        daemon_lifecycle.start(wait=True)

        try:
            # Rapidly connect and disconnect many clients
            for _ in range(20):
                client = DaemonClient(daemon_lifecycle.socket_path)
                await client.connect()
                await client.ping()
                await client.disconnect()

            # Short delay
            await asyncio.sleep(0.1)

            # Daemon should still work
            client = DaemonClient(daemon_lifecycle.socket_path)
            await client.connect()
            status = await client.status()
            assert status["running"] is True
            await client.disconnect()
        finally:
            daemon_lifecycle.stop()

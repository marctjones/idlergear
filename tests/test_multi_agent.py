"""Integration tests for multi-agent coordination via daemon."""

import json
import socket
import tempfile
import time
from pathlib import Path
from threading import Thread

import pytest

from idlergear.daemon.agents import AgentRegistry
from idlergear.daemon.queue import CommandQueue
from idlergear.daemon.server import DaemonServer


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def daemon_server(temp_storage):
    """Create and start a daemon server for testing."""
    socket_path = temp_storage / "daemon.sock"
    pid_path = temp_storage / "daemon.pid"
    storage_path = temp_storage / "storage"
    storage_path.mkdir(exist_ok=True)
    server = DaemonServer(socket_path, pid_path, storage_path)

    # Start server in background thread
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # Wait for server to be ready
    time.sleep(0.1)

    yield server, socket_path

    # Cleanup
    server.shutdown()


def send_rpc_request(socket_path, method, params=None):
    """Send JSON-RPC request to daemon."""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(str(socket_path))

    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1,
    }

    client.sendall(json.dumps(request).encode() + b"\n")
    response_data = client.recv(4096)
    client.close()

    response = json.loads(response_data.decode())
    if "error" in response:
        raise Exception(f"RPC Error: {response['error']}")

    return response.get("result")


class TestMultiAgentCoordination:
    """Test multi-agent coordination features."""

    def test_agent_registration(self, daemon_server):
        """Test agent registration and listing."""
        server, socket_path = daemon_server

        # Register two agents
        agent1 = send_rpc_request(
            socket_path,
            "register_agent",
            {
                "name": "Claude Code",
                "agent_type": "claude-code",
                "metadata": {"session_id": "abc123"},
            },
        )

        agent2 = send_rpc_request(
            socket_path,
            "register_agent",
            {
                "name": "Goose Terminal",
                "agent_type": "goose",
            },
        )

        # Both should have unique IDs
        assert agent1["agent_id"] != agent2["agent_id"]
        assert agent1["status"] == "active"
        assert agent2["status"] == "active"

        # List agents
        agents = send_rpc_request(socket_path, "list_agents")
        assert len(agents) == 2

        agent_names = [a["name"] for a in agents]
        assert "Claude Code" in agent_names
        assert "Goose Terminal" in agent_names

    def test_agent_heartbeat(self, daemon_server):
        """Test agent heartbeat and timeout detection."""
        server, socket_path = daemon_server

        # Register agent
        agent = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Test Agent", "agent_type": "test"},
        )
        agent_id = agent["agent_id"]

        # Send heartbeat
        result = send_rpc_request(
            socket_path,
            "heartbeat",
            {"agent_id": agent_id},
        )
        assert result["status"] == "ok"

        # Agent should still be active
        agents = send_rpc_request(socket_path, "list_agents")
        assert len(agents) == 1
        assert agents[0]["status"] == "active"

    def test_command_queue(self, daemon_server):
        """Test command queueing and retrieval."""
        server, socket_path = daemon_server

        # Register agent
        agent = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Worker Agent", "agent_type": "worker"},
        )
        agent_id = agent["agent_id"]

        # Queue a command
        command_result = send_rpc_request(
            socket_path,
            "queue_command",
            {
                "command": "run tests",
                "priority": 5,
            },
        )
        command_id = command_result["command_id"]

        # Get next command
        next_cmd = send_rpc_request(
            socket_path,
            "get_next_command",
            {"agent_id": agent_id},
        )

        assert next_cmd is not None
        assert next_cmd["command_id"] == command_id
        assert next_cmd["command"] == "run tests"
        assert next_cmd["priority"] == 5
        assert next_cmd["assigned_to"] == agent_id

    def test_command_priority(self, daemon_server):
        """Test that higher priority commands are retrieved first."""
        server, socket_path = daemon_server

        # Register agent
        agent = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Worker", "agent_type": "worker"},
        )
        agent_id = agent["agent_id"]

        # Queue commands with different priorities
        send_rpc_request(
            socket_path,
            "queue_command",
            {"command": "low priority", "priority": 1},
        )

        high_priority = send_rpc_request(
            socket_path,
            "queue_command",
            {"command": "high priority", "priority": 10},
        )

        send_rpc_request(
            socket_path,
            "queue_command",
            {"command": "medium priority", "priority": 5},
        )

        # First command should be high priority
        next_cmd = send_rpc_request(
            socket_path,
            "get_next_command",
            {"agent_id": agent_id},
        )

        assert next_cmd["command"] == "high priority"
        assert next_cmd["command_id"] == high_priority["command_id"]

    def test_command_completion(self, daemon_server):
        """Test marking commands as complete."""
        server, socket_path = daemon_server

        # Register agent
        agent = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Worker", "agent_type": "worker"},
        )
        agent_id = agent["agent_id"]

        # Queue and get command
        cmd = send_rpc_request(
            socket_path,
            "queue_command",
            {"command": "test command"},
        )
        command_id = cmd["command_id"]

        next_cmd = send_rpc_request(
            socket_path,
            "get_next_command",
            {"agent_id": agent_id},
        )

        # Complete command
        result = send_rpc_request(
            socket_path,
            "complete_command",
            {
                "command_id": command_id,
                "result": "Success!",
                "success": True,
            },
        )

        assert result["status"] == "completed"

        # Check command status
        status = send_rpc_request(
            socket_path,
            "get_command_status",
            {"command_id": command_id},
        )

        assert status["status"] == "completed"
        assert status["result"] == "Success!"

    def test_message_broadcasting(self, daemon_server):
        """Test broadcasting messages to all agents."""
        server, socket_path = daemon_server

        # Register two agents
        agent1 = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Agent 1", "agent_type": "test"},
        )

        agent2 = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Agent 2", "agent_type": "test"},
        )

        # Broadcast message
        result = send_rpc_request(
            socket_path,
            "broadcast_message",
            {"message": "Hello all agents!"},
        )

        assert result["sent_to"] == 2

        # Both agents should receive the message via events
        # (In real implementation, agents would subscribe to events)

    def test_write_locking(self, daemon_server):
        """Test write lock acquisition and release."""
        server, socket_path = daemon_server

        # Register two agents
        agent1 = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Agent 1", "agent_type": "test"},
        )
        agent1_id = agent1["agent_id"]

        agent2 = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Agent 2", "agent_type": "test"},
        )
        agent2_id = agent2["agent_id"]

        # Agent 1 acquires lock
        lock1 = send_rpc_request(
            socket_path,
            "acquire_lock",
            {
                "agent_id": agent1_id,
                "resource": "tasks.json",
                "timeout": 5.0,
            },
        )

        assert lock1["acquired"] is True
        lock_id = lock1["lock_id"]

        # Agent 2 tries to acquire same lock - should fail
        lock2 = send_rpc_request(
            socket_path,
            "acquire_lock",
            {
                "agent_id": agent2_id,
                "resource": "tasks.json",
                "timeout": 0.1,
            },
        )

        assert lock2["acquired"] is False

        # Agent 1 releases lock
        release = send_rpc_request(
            socket_path,
            "release_lock",
            {"lock_id": lock_id},
        )

        assert release["released"] is True

        # Now Agent 2 can acquire
        lock3 = send_rpc_request(
            socket_path,
            "acquire_lock",
            {
                "agent_id": agent2_id,
                "resource": "tasks.json",
                "timeout": 1.0,
            },
        )

        assert lock3["acquired"] is True

    def test_agent_status_updates(self, daemon_server):
        """Test updating agent status."""
        server, socket_path = daemon_server

        # Register agent
        agent = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Worker", "agent_type": "worker"},
        )
        agent_id = agent["agent_id"]

        # Update status to busy
        result = send_rpc_request(
            socket_path,
            "update_agent_status",
            {
                "agent_id": agent_id,
                "status": "busy",
                "current_task": "Running tests",
            },
        )

        assert result["status"] == "busy"

        # Verify status
        agents = send_rpc_request(socket_path, "list_agents")
        assert agents[0]["status"] == "busy"
        assert agents[0]["current_task"] == "Running tests"

    def test_multi_agent_workflow(self, daemon_server):
        """Test complete multi-agent workflow."""
        server, socket_path = daemon_server

        # Setup: Register coordinator and two workers
        coordinator = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Coordinator", "agent_type": "coordinator"},
        )

        worker1 = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Worker 1", "agent_type": "worker"},
        )
        worker1_id = worker1["agent_id"]

        worker2 = send_rpc_request(
            socket_path,
            "register_agent",
            {"name": "Worker 2", "agent_type": "worker"},
        )
        worker2_id = worker2["agent_id"]

        # Coordinator queues two commands
        cmd1 = send_rpc_request(
            socket_path,
            "queue_command",
            {"command": "build frontend", "priority": 5},
        )

        cmd2 = send_rpc_request(
            socket_path,
            "queue_command",
            {"command": "build backend", "priority": 5},
        )

        # Workers pick up commands
        task1 = send_rpc_request(
            socket_path,
            "get_next_command",
            {"agent_id": worker1_id},
        )

        task2 = send_rpc_request(
            socket_path,
            "get_next_command",
            {"agent_id": worker2_id},
        )

        # Each worker got a different task
        assert task1["command_id"] != task2["command_id"]
        commands = {task1["command"], task2["command"]}
        assert "build frontend" in commands
        assert "build backend" in commands

        # Workers complete their tasks
        send_rpc_request(
            socket_path,
            "complete_command",
            {
                "command_id": task1["command_id"],
                "result": "Frontend built",
                "success": True,
            },
        )

        send_rpc_request(
            socket_path,
            "complete_command",
            {
                "command_id": task2["command_id"],
                "result": "Backend built",
                "success": True,
            },
        )

        # Check both commands are completed
        status1 = send_rpc_request(
            socket_path,
            "get_command_status",
            {"command_id": task1["command_id"]},
        )

        status2 = send_rpc_request(
            socket_path,
            "get_command_status",
            {"command_id": task2["command_id"]},
        )

        assert status1["status"] == "completed"
        assert status2["status"] == "completed"


class TestAgentRegistry:
    """Test agent registry standalone."""

    def test_register_and_list(self, temp_storage):
        """Test basic registration and listing."""
        registry = AgentRegistry(temp_storage)

        agent_id = registry.register("Test Agent", "test", {})
        assert agent_id is not None

        agents = registry.list_agents()
        assert len(agents) == 1
        assert agents[0]["name"] == "Test Agent"

    def test_heartbeat_updates_timestamp(self, temp_storage):
        """Test heartbeat updates last_seen timestamp."""
        registry = AgentRegistry(temp_storage)

        agent_id = registry.register("Test Agent", "test", {})
        agent = registry.get_agent(agent_id)
        first_seen = agent["last_seen"]

        time.sleep(0.1)
        registry.heartbeat(agent_id)

        agent = registry.get_agent(agent_id)
        assert agent["last_seen"] > first_seen

    def test_cleanup_stale_agents(self, temp_storage):
        """Test cleanup of stale agents."""
        registry = AgentRegistry(temp_storage)

        # Register agent with very short timeout
        agent_id = registry.register("Test Agent", "test", {})

        # Simulate agent being stale
        agent_file = temp_storage / "agents" / f"{agent_id}.json"
        agent_data = json.loads(agent_file.read_text())
        agent_data["last_seen"] = time.time() - 1000  # 1000 seconds ago
        agent_file.write_text(json.dumps(agent_data))

        # Cleanup should remove it
        registry.cleanup_stale_agents(timeout=60)

        agents = registry.list_agents()
        assert len(agents) == 0


class TestCommandQueue:
    """Test command queue standalone."""

    def test_queue_and_get(self, temp_storage):
        """Test queueing and retrieving commands."""
        queue = CommandQueue(temp_storage)

        cmd_id = queue.queue_command("test command", priority=1)
        assert cmd_id is not None

        cmd = queue.get_next_command("agent-123")
        assert cmd is not None
        assert cmd["command"] == "test command"
        assert cmd["assigned_to"] == "agent-123"

    def test_priority_ordering(self, temp_storage):
        """Test commands are returned in priority order."""
        queue = CommandQueue(temp_storage)

        queue.queue_command("low", priority=1)
        high_id = queue.queue_command("high", priority=10)
        queue.queue_command("medium", priority=5)

        cmd = queue.get_next_command("agent-123")
        assert cmd["command"] == "high"
        assert cmd["command_id"] == high_id

    def test_complete_command(self, temp_storage):
        """Test marking command as complete."""
        queue = CommandQueue(temp_storage)

        cmd_id = queue.queue_command("test", priority=1)
        queue.get_next_command("agent-123")
        queue.complete_command(cmd_id, result="Done", success=True)

        status = queue.get_command_status(cmd_id)
        assert status["status"] == "completed"
        assert status["result"] == "Done"

    def test_command_not_reassigned(self, temp_storage):
        """Test completed commands are not reassigned."""
        queue = CommandQueue(temp_storage)

        cmd_id = queue.queue_command("test", priority=1)
        queue.get_next_command("agent-1")
        queue.complete_command(cmd_id, result="Done", success=True)

        # Should not get the completed command
        cmd = queue.get_next_command("agent-2")
        assert cmd is None

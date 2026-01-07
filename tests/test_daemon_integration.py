"""Integration tests for multi-agent daemon coordination."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from idlergear.daemon.agents import AgentRegistry
from idlergear.daemon.locks import LockManager
from idlergear.daemon.queue import CommandQueue, CommandStatus


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def agent_registry(temp_storage):
    """Create agent registry instance."""
    return AgentRegistry(temp_storage)


@pytest.fixture
def command_queue(temp_storage):
    """Create command queue instance."""
    return CommandQueue(temp_storage)


@pytest.fixture
def lock_manager():
    """Create lock manager instance."""
    return LockManager()


@pytest.mark.asyncio
async def test_agent_registration(agent_registry):
    """Test agent registration and retrieval."""
    # Register an agent
    session = await agent_registry.register(
        agent_id="test-agent-1",
        agent_type="claude-code",
        connection_id=1,
        metadata={"test": "data"},
    )

    assert session.agent_id == "test-agent-1"
    assert session.agent_type == "claude-code"
    assert session.status == "active"
    assert session.metadata["test"] == "data"

    # Get agent info
    agent = await agent_registry.get("test-agent-1")
    assert agent is not None
    assert agent.agent_id == "test-agent-1"

    # List agents
    agents = await agent_registry.list()
    assert len(agents) == 1
    assert agents[0].agent_id == "test-agent-1"


@pytest.mark.asyncio
async def test_agent_heartbeat(agent_registry):
    """Test agent heartbeat."""
    await agent_registry.register("test-agent-1", "test", connection_id=1)

    # Send heartbeat
    result = await agent_registry.heartbeat("test-agent-1")
    assert result is True

    agent = await agent_registry.get("test-agent-1")
    assert agent is not None

    # Heartbeat for non-existent agent should fail
    result = await agent_registry.heartbeat("non-existent")
    assert result is False


@pytest.mark.asyncio
async def test_agent_status_update(agent_registry):
    """Test updating agent status."""
    await agent_registry.register("test-agent-1", "test", connection_id=1)

    # Update status
    result = await agent_registry.update_status(
        "test-agent-1", status="busy", current_task="task-123"
    )
    assert result is True

    agent = await agent_registry.get("test-agent-1")
    assert agent.status == "busy"
    assert agent.current_task == "task-123"


@pytest.mark.asyncio
async def test_command_queue_basic(command_queue):
    """Test basic command queueing and retrieval."""
    # Queue a command
    cmd_id = await command_queue.add(
        prompt="test command", priority=5, metadata={"source": "test"}
    )

    assert cmd_id is not None

    # Get command
    cmd = await command_queue.get(cmd_id)
    assert cmd is not None
    assert cmd.prompt == "test command"
    assert cmd.priority == 5
    assert cmd.status.value == "pending"

    # List queued commands
    commands = await command_queue.list(status=CommandStatus.PENDING)
    assert len(commands) == 1
    assert commands[0].id == cmd_id


@pytest.mark.asyncio
async def test_command_priority(command_queue):
    """Test command priority ordering."""
    # Queue commands with different priorities
    low = await command_queue.add("low priority", priority=1)
    high = await command_queue.add("high priority", priority=10)
    medium = await command_queue.add("medium priority", priority=5)

    # Poll should return highest priority
    next_cmd = await command_queue.poll_pending("agent-1")
    assert next_cmd is not None
    assert next_cmd.id == high
    assert next_cmd.priority == 10


@pytest.mark.asyncio
async def test_command_assignment(command_queue):
    """Test command assignment to agents."""
    cmd_id = await command_queue.add("test", priority=5)

    # Poll assigns to agent
    cmd = await command_queue.poll_pending("agent-1")
    assert cmd is not None
    assert cmd.id == cmd_id
    assert cmd.assigned_to == "agent-1"
    assert cmd.status == CommandStatus.ASSIGNED

    # Same command shouldn't be returned again
    next_cmd = await command_queue.poll_pending("agent-2")
    assert next_cmd is None


@pytest.mark.asyncio
async def test_command_completion(command_queue):
    """Test marking commands as complete."""
    cmd_id = await command_queue.add("test")

    # Assign and complete
    await command_queue.poll_pending("agent-1")
    await command_queue.complete(cmd_id, result={"output": "success"})

    # Check status
    cmd = await command_queue.get(cmd_id)
    assert cmd.status == CommandStatus.COMPLETED
    assert cmd.result["output"] == "success"
    assert cmd.completed_at is not None


@pytest.mark.asyncio
async def test_lock_acquisition(lock_manager):
    """Test lock acquisition and release."""
    # Acquire lock
    success = await lock_manager.acquire("test-resource", "agent-1", timeout=5.0)
    assert success is True

    # Try to acquire same lock with different agent (should fail)
    success = await lock_manager.acquire("test-resource", "agent-2", timeout=0.1)
    assert success is False

    # Check lock status
    lock_info = await lock_manager.get_lock("test-resource")
    assert lock_info is not None
    assert lock_info.agent_id == "agent-1"

    # Release lock
    await lock_manager.release("test-resource", "agent-1")

    # Now second agent can acquire
    success = await lock_manager.acquire("test-resource", "agent-2", timeout=0.1)
    assert success is True


@pytest.mark.asyncio
async def test_lock_timeout(lock_manager):
    """Test automatic lock timeout."""
    # Acquire lock with very short timeout
    await lock_manager.acquire("test-resource", "agent-1", timeout=0.2)

    # Wait for timeout
    await asyncio.sleep(0.3)

    # Lock should be expired, second agent can acquire
    success = await lock_manager.acquire("test-resource", "agent-2", timeout=0.1)
    assert success is True


@pytest.mark.asyncio
async def test_multi_agent_coordination(agent_registry, command_queue):
    """Test full multi-agent coordination scenario."""
    # Register multiple agents
    await agent_registry.register("claude-code", "claude-code", connection_id=1)
    await agent_registry.register("goose", "goose", connection_id=2)

    # Queue multiple commands
    cmd1 = await command_queue.add("implement feature", priority=10)
    cmd2 = await command_queue.add("run tests", priority=5)
    cmd3 = await command_queue.add("update docs", priority=3)

    # Agents pick up commands
    work1 = await command_queue.poll_pending("claude-code")
    work2 = await command_queue.poll_pending("goose")

    assert work1 is not None
    assert work2 is not None
    assert work1.id == cmd1  # Highest priority
    assert work2.id == cmd2  # Second highest

    # Update agent statuses
    await agent_registry.update_status("claude-code", "busy")
    await agent_registry.update_status("goose", "busy")

    # Complete work
    await command_queue.complete(cmd1, result={"status": "done"})
    await agent_registry.update_status("claude-code", "idle")

    # Claude Code picks up next work
    work3 = await command_queue.poll_pending("claude-code")
    assert work3 is not None
    assert work3.id == cmd3

    # Verify agent list
    agents = await agent_registry.list()
    assert len(agents) == 2


@pytest.mark.asyncio
async def test_persistence(temp_storage):
    """Test that data persists across restarts."""
    # Create registry and register agent
    registry1 = AgentRegistry(temp_storage)
    await registry1.register("test-agent", "test", connection_id=1)

    # Create new registry instance (simulating restart)
    registry2 = AgentRegistry(temp_storage)

    # Agent should still exist
    agent = await registry2.get("test-agent")
    assert agent is not None
    assert agent.agent_id == "test-agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

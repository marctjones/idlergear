"""MCP tool handlers for daemon-based multi-agent coordination."""

import asyncio
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.daemon.client import DaemonClient, DaemonNotRunning


def _get_daemon_client() -> DaemonClient:
    """Get daemon client for current project."""
    root = find_idlergear_root()
    if not root:
        raise ValueError("IdlerGear not initialized. Run 'idlergear init' first.")

    socket_path = root / ".idlergear" / "daemon.sock"
    return DaemonClient(socket_path)


async def _call_daemon(method: str, params: dict[str, Any]) -> Any:
    """Helper to call daemon method with error handling."""
    client = _get_daemon_client()

    try:
        await client.connect()
        result = await client.call(method, params)
        return result
    except DaemonNotRunning:
        raise ValueError(
            "IdlerGear daemon not running. Start it with: idlergear daemon start"
        )
    finally:
        await client.disconnect()


# Agent handlers
async def handle_agent_register(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle agent registration."""
    return await _call_daemon("agent.register", arguments)


async def handle_agent_heartbeat(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle agent heartbeat."""
    return await _call_daemon("agent.heartbeat", arguments)


async def handle_agent_update_status(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle agent status update."""
    return await _call_daemon("agent.update_status", arguments)


async def handle_agent_list(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle agent list request."""
    return await _call_daemon("agent.list", arguments)


# Queue handlers
async def handle_queue_add(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle adding command to queue."""
    return await _call_daemon("queue.add", arguments)


async def handle_queue_poll(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle polling for next command."""
    return await _call_daemon("queue.poll", arguments)


async def handle_queue_list(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle listing queued commands."""
    return await _call_daemon("queue.list", arguments)


async def handle_queue_get(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle getting command by ID."""
    return await _call_daemon("queue.get", arguments)


async def handle_queue_complete(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle marking command as completed."""
    return await _call_daemon("queue.complete", arguments)


# Lock handlers
async def handle_lock_acquire(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle lock acquisition."""
    return await _call_daemon("lock.acquire", arguments)


async def handle_lock_release(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle lock release."""
    return await _call_daemon("lock.release", arguments)


async def handle_lock_check(arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle lock status check."""
    return await _call_daemon("lock.is_locked", arguments)


# Handler dispatch map
DAEMON_HANDLERS = {
    "idlergear_agent_register": handle_agent_register,
    "idlergear_agent_heartbeat": handle_agent_heartbeat,
    "idlergear_agent_update_status": handle_agent_update_status,
    "idlergear_agent_list": handle_agent_list,
    "idlergear_queue_add": handle_queue_add,
    "idlergear_queue_poll": handle_queue_poll,
    "idlergear_queue_list": handle_queue_list,
    "idlergear_queue_get": handle_queue_get,
    "idlergear_queue_complete": handle_queue_complete,
    "idlergear_lock_acquire": handle_lock_acquire,
    "idlergear_lock_release": handle_lock_release,
    "idlergear_lock_check": handle_lock_check,
}

"""MCP handlers for daemon operations with auto-start support.

These handlers are called from the MCP server and auto-start the daemon
if it's not running. This provides seamless multi-agent coordination.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from idlergear.config import find_idlergear_root
from idlergear.daemon.client import DaemonClient, DaemonError, DaemonNotRunning
from idlergear.daemon.lifecycle import DaemonLifecycle


def _get_idlergear_root() -> Path:
    """Get the .idlergear directory, raising if not initialized."""
    root = find_idlergear_root()
    if not root:
        raise ValueError("IdlerGear not initialized. Run 'idlergear init' first.")
    return root / ".idlergear"


def _ensure_daemon() -> DaemonLifecycle:
    """Ensure daemon is running and return lifecycle manager.

    This is the core auto-start logic. If daemon isn't running, start it.
    """
    idlergear_root = _get_idlergear_root()
    lifecycle = DaemonLifecycle(idlergear_root)

    if not lifecycle.is_running():
        lifecycle.start(wait=True)

    return lifecycle


def _run_async(coro):
    """Run async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're in an async context, create a task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


async def _call_daemon(method: str, params: dict[str, Any]) -> Any:
    """Call daemon method with auto-start and error handling."""
    idlergear_root = _get_idlergear_root()
    lifecycle = DaemonLifecycle(idlergear_root)

    # Auto-start daemon if not running
    if not lifecycle.is_running():
        lifecycle.start(wait=True)

    client = DaemonClient(lifecycle.socket_path)
    try:
        await client.connect()
        result = await client.call(method, params)
        return result
    finally:
        await client.disconnect()


def _write_presence_file(agent_id: str, agent_type: str, metadata: dict[str, Any] | None = None) -> Path:
    """Write agent presence file for visibility.

    Presence files allow `idlergear status` to show connected agents
    even without querying the daemon.
    """
    idlergear_root = _get_idlergear_root()
    agents_dir = idlergear_root / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    presence_file = agents_dir / f"{agent_id}.json"
    presence_data = {
        "agent_id": agent_id,
        "agent_type": agent_type,
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
        "pid": None,  # Could be filled in if we track it
        "metadata": metadata or {},
    }
    presence_file.write_text(json.dumps(presence_data, indent=2))
    return presence_file


def _remove_presence_file(agent_id: str) -> bool:
    """Remove agent presence file on disconnect."""
    idlergear_root = _get_idlergear_root()
    presence_file = idlergear_root / "agents" / f"{agent_id}.json"
    if presence_file.exists():
        presence_file.unlink()
        return True
    return False


def _update_presence_heartbeat(agent_id: str) -> bool:
    """Update last_heartbeat in presence file."""
    idlergear_root = _get_idlergear_root()
    presence_file = idlergear_root / "agents" / f"{agent_id}.json"
    if not presence_file.exists():
        return False

    try:
        data = json.loads(presence_file.read_text())
        data["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
        presence_file.write_text(json.dumps(data, indent=2))
        return True
    except (json.JSONDecodeError, OSError):
        return False


def _list_presence_files() -> list[dict[str, Any]]:
    """List all agent presence files."""
    idlergear_root = _get_idlergear_root()
    agents_dir = idlergear_root / "agents"
    if not agents_dir.exists():
        return []

    agents = []
    for presence_file in agents_dir.glob("*.json"):
        # Skip the daemon's internal registry file
        if presence_file.name == "agents.json":
            continue
        try:
            data = json.loads(presence_file.read_text())
            agents.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    return agents


def _cleanup_stale_presence_files(timeout_seconds: int = 300) -> int:
    """Remove stale presence files (no heartbeat for N seconds)."""
    idlergear_root = _get_idlergear_root()
    agents_dir = idlergear_root / "agents"
    if not agents_dir.exists():
        return 0

    removed = 0
    now = datetime.now(timezone.utc)

    for presence_file in agents_dir.glob("*.json"):
        try:
            data = json.loads(presence_file.read_text())
            last_hb = datetime.fromisoformat(data.get("last_heartbeat", ""))
            age = (now - last_hb).total_seconds()
            if age > timeout_seconds:
                presence_file.unlink()
                removed += 1
        except (json.JSONDecodeError, OSError, ValueError):
            # Remove corrupt files
            try:
                presence_file.unlink()
                removed += 1
            except OSError:
                pass

    return removed


# ============================================================================
# MCP Handler Functions (called from mcp_server.py)
# ============================================================================

def handle_register_agent(arguments: dict[str, Any]) -> dict[str, Any]:
    """Register an AI agent with the daemon.

    This is the main entry point for agent registration:
    1. Auto-starts the daemon if not running
    2. Registers with daemon for coordination
    3. Creates presence file for visibility
    """
    name = arguments.get("name", "Unknown Agent")
    agent_type = arguments.get("agent_type", "unknown")
    metadata = arguments.get("metadata", {})

    # Generate unique agent ID
    agent_id = f"{agent_type}-{uuid.uuid4().hex[:8]}"

    # Ensure daemon is running (auto-start)
    lifecycle = _ensure_daemon()

    # Register with daemon
    async def do_register():
        client = DaemonClient(lifecycle.socket_path)
        try:
            await client.connect()
            result = await client.call("agent.register", {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "name": name,
                "metadata": metadata,
            })
            return result
        except DaemonError as e:
            # If daemon doesn't support agent registration yet, still succeed
            if "Unknown method" in str(e):
                return {"agent_id": agent_id, "registered": True, "note": "Daemon running, agent registered locally"}
            raise
        finally:
            await client.disconnect()

    try:
        result = _run_async(do_register())
    except Exception as e:
        # Even if daemon registration fails, create presence file
        result = {"agent_id": agent_id, "error": str(e)}

    # Create presence file for visibility
    _write_presence_file(agent_id, agent_type, metadata)

    return {
        "agent_id": agent_id,
        "name": name,
        "agent_type": agent_type,
        "daemon_running": lifecycle.is_running(),
        "daemon_pid": lifecycle.get_pid(),
        **result,
    }


def handle_list_agents() -> dict[str, Any]:
    """List all registered agents.

    Returns agents from both daemon (if running) and presence files.
    """
    # First, try to get from daemon
    daemon_agents = []
    daemon_running = False

    try:
        idlergear_root = _get_idlergear_root()
        lifecycle = DaemonLifecycle(idlergear_root)

        if lifecycle.is_running():
            daemon_running = True
            result = _run_async(_call_daemon("agent.list", {}))
            daemon_agents = result.get("agents", [])
    except Exception:
        pass

    # Also get from presence files (fallback/supplement)
    presence_agents = _list_presence_files()

    # Merge: prefer daemon data but include presence-only agents
    daemon_ids = {a.get("agent_id") for a in daemon_agents}

    all_agents = list(daemon_agents)
    for pa in presence_agents:
        if pa.get("agent_id") not in daemon_ids:
            pa["source"] = "presence_file"
            all_agents.append(pa)

    # Cleanup stale presence files while we're here
    stale_removed = _cleanup_stale_presence_files()

    return {
        "agents": all_agents,
        "count": len(all_agents),
        "daemon_running": daemon_running,
        "stale_cleaned": stale_removed,
    }


def handle_queue_command(arguments: dict[str, Any]) -> dict[str, Any]:
    """Queue a command for execution by any available agent."""
    command = arguments.get("command")
    if not command:
        raise ValueError("command is required")

    priority = arguments.get("priority", 1)
    wait_for_result = arguments.get("wait_for_result", False)

    # Ensure daemon is running
    _ensure_daemon()

    result = _run_async(_call_daemon("queue.add", {
        "command": command,
        "priority": priority,
    }))

    if wait_for_result:
        # Poll for completion (with timeout)
        command_id = result.get("id")
        if command_id:
            for _ in range(60):  # 60 second timeout
                import time
                time.sleep(1)
                status = _run_async(_call_daemon("queue.get", {"id": command_id}))
                if status.get("status") == "completed":
                    return status
            result["timeout"] = True

    return result


def handle_send_message(arguments: dict[str, Any]) -> dict[str, Any]:
    """Broadcast a message to all active agents."""
    message = arguments.get("message")
    if not message:
        raise ValueError("message is required")

    # Ensure daemon is running
    _ensure_daemon()

    result = _run_async(_call_daemon("message.broadcast", {
        "event": "message",
        "data": {"message": message, "timestamp": datetime.now(timezone.utc).isoformat()},
    }))

    return {"sent": True, "message": message, **result}


def handle_update_status(arguments: dict[str, Any]) -> dict[str, Any]:
    """Update agent status."""
    agent_id = arguments.get("agent_id")
    status = arguments.get("status")

    if not agent_id:
        raise ValueError("agent_id is required")
    if not status:
        raise ValueError("status is required")

    # Update presence file heartbeat
    _update_presence_heartbeat(agent_id)

    # Update in daemon if running
    try:
        idlergear_root = _get_idlergear_root()
        lifecycle = DaemonLifecycle(idlergear_root)

        if lifecycle.is_running():
            result = _run_async(_call_daemon("agent.update_status", {
                "agent_id": agent_id,
                "status": status,
            }))
            return result
    except Exception as e:
        return {"updated": False, "error": str(e)}

    return {"updated": True, "agent_id": agent_id, "status": status}


def handle_list_queue() -> dict[str, Any]:
    """List queued commands."""
    try:
        idlergear_root = _get_idlergear_root()
        lifecycle = DaemonLifecycle(idlergear_root)

        if not lifecycle.is_running():
            return {"commands": [], "daemon_running": False}

        result = _run_async(_call_daemon("queue.list", {}))
        result["daemon_running"] = True
        return result
    except Exception as e:
        return {"commands": [], "error": str(e)}

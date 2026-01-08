"""Cross-agent messaging system for IdlerGear.

Messages are stored in .idlergear/inbox/<agent_id>/*.json and delivered
at session start via hooks or on-demand via MCP tools.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid


def get_inbox_dir(idlergear_root: Path, agent_id: str) -> Path:
    """Get the inbox directory for an agent."""
    return idlergear_root / "inbox" / agent_id


def send_message(
    idlergear_root: Path,
    to_agent: str,
    message: str,
    from_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a message to another agent's inbox.

    Args:
        idlergear_root: Path to .idlergear directory
        to_agent: Target agent ID
        message: Message content
        from_agent: Sender agent ID (optional)
        metadata: Additional metadata (optional)

    Returns:
        Dict with message_id and status
    """
    inbox_dir = get_inbox_dir(idlergear_root, to_agent)
    inbox_dir.mkdir(parents=True, exist_ok=True)

    message_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).isoformat()

    msg_data = {
        "id": message_id,
        "from": from_agent,
        "to": to_agent,
        "message": message,
        "timestamp": timestamp,
        "read": False,
        "metadata": metadata or {},
    }

    # Use timestamp prefix for ordering
    filename = f"{timestamp.replace(':', '-').replace('+', '_')}_{message_id}.json"
    msg_path = inbox_dir / filename

    with open(msg_path, "w") as f:
        json.dump(msg_data, f, indent=2)

    return {
        "message_id": message_id,
        "sent_to": to_agent,
        "timestamp": timestamp,
        "status": "delivered",
    }


def list_messages(
    idlergear_root: Path,
    agent_id: str,
    unread_only: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """List messages in an agent's inbox.

    Args:
        idlergear_root: Path to .idlergear directory
        agent_id: Agent ID to check inbox for
        unread_only: Only return unread messages
        limit: Maximum number of messages to return

    Returns:
        List of message dicts, newest first
    """
    inbox_dir = get_inbox_dir(idlergear_root, agent_id)

    if not inbox_dir.exists():
        return []

    messages = []
    for msg_file in sorted(inbox_dir.glob("*.json"), reverse=True):
        try:
            with open(msg_file) as f:
                msg = json.load(f)
                msg["_path"] = str(msg_file)

                if unread_only and msg.get("read", False):
                    continue

                messages.append(msg)

                if limit and len(messages) >= limit:
                    break
        except (json.JSONDecodeError, OSError):
            continue

    return messages


def mark_as_read(
    idlergear_root: Path,
    agent_id: str,
    message_ids: list[str] | None = None,
) -> int:
    """Mark messages as read.

    Args:
        idlergear_root: Path to .idlergear directory
        agent_id: Agent ID
        message_ids: Specific message IDs to mark, or None for all

    Returns:
        Number of messages marked as read
    """
    inbox_dir = get_inbox_dir(idlergear_root, agent_id)

    if not inbox_dir.exists():
        return 0

    count = 0
    for msg_file in inbox_dir.glob("*.json"):
        try:
            with open(msg_file) as f:
                msg = json.load(f)

            if message_ids and msg.get("id") not in message_ids:
                continue

            if not msg.get("read", False):
                msg["read"] = True
                msg["read_at"] = datetime.now(timezone.utc).isoformat()

                with open(msg_file, "w") as f:
                    json.dump(msg, f, indent=2)
                count += 1
        except (json.JSONDecodeError, OSError):
            continue

    return count


def clear_inbox(
    idlergear_root: Path,
    agent_id: str,
    read_only: bool = True,
) -> int:
    """Clear messages from inbox.

    Args:
        idlergear_root: Path to .idlergear directory
        agent_id: Agent ID
        read_only: Only clear read messages (default True for safety)

    Returns:
        Number of messages cleared
    """
    inbox_dir = get_inbox_dir(idlergear_root, agent_id)

    if not inbox_dir.exists():
        return 0

    count = 0
    for msg_file in inbox_dir.glob("*.json"):
        try:
            if read_only:
                with open(msg_file) as f:
                    msg = json.load(f)
                if not msg.get("read", False):
                    continue

            msg_file.unlink()
            count += 1
        except (json.JSONDecodeError, OSError):
            continue

    return count


def get_inbox_summary(idlergear_root: Path, agent_id: str) -> dict[str, Any]:
    """Get a summary of an agent's inbox.

    Args:
        idlergear_root: Path to .idlergear directory
        agent_id: Agent ID

    Returns:
        Dict with total, unread, and latest message info
    """
    messages = list_messages(idlergear_root, agent_id)
    unread = [m for m in messages if not m.get("read", False)]

    summary = {
        "total": len(messages),
        "unread": len(unread),
        "latest": None,
    }

    if unread:
        latest = unread[0]
        summary["latest"] = {
            "id": latest.get("id"),
            "from": latest.get("from"),
            "preview": latest.get("message", "")[:100],
            "timestamp": latest.get("timestamp"),
        }

    return summary


def format_messages_for_context(messages: list[dict[str, Any]]) -> str:
    """Format messages for injection into Claude context.

    Args:
        messages: List of message dicts

    Returns:
        Formatted string for additionalContext
    """
    if not messages:
        return ""

    lines = [f"=== PENDING MESSAGES ({len(messages)}) ===", ""]

    for msg in messages:
        from_agent = msg.get("from", "Unknown")
        timestamp = msg.get("timestamp", "")
        content = msg.get("message", "")

        # Parse timestamp for display
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%Y-%m-%d %H:%M UTC")
            except ValueError:
                time_str = timestamp
        else:
            time_str = "Unknown time"

        lines.append(f"From: {from_agent}")
        lines.append(f"Time: {time_str}")
        lines.append(f"Message: {content}")
        lines.append("")

    lines.append("=== END MESSAGES ===")

    return "\n".join(lines)

"""Cross-agent messaging system for IdlerGear.

Messages are stored in .idlergear/inbox/<agent_id>/*.json and delivered
at session start via hooks or on-demand via MCP tools.

Delivery Types:
- context: Inject into recipient's context (they will see and act on it)
- notification: Create task with [message] label (informational)
- deferred: Queue for end-of-session review (batch processing)

Message Types:
- info: Informational, no action needed
- request: Sender wants recipient to do something
- alert: Important notification about system/code state
- question: Sender needs a response
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
import uuid

# Valid delivery types
DELIVERY_TYPES = ("context", "notification", "deferred")
# Valid message types
MESSAGE_TYPES = ("info", "request", "alert", "question")


def get_inbox_dir(idlergear_root: Path, agent_id: str) -> Path:
    """Get the inbox directory for an agent."""
    return idlergear_root / "inbox" / agent_id


def send_message(
    idlergear_root: Path,
    to_agent: str,
    message: str,
    from_agent: str | None = None,
    delivery: Literal["context", "notification", "deferred"] = "notification",
    message_type: Literal["info", "request", "alert", "question"] = "info",
    action_requested: bool = False,
    context: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a message to another agent's inbox.

    Args:
        idlergear_root: Path to .idlergear directory
        to_agent: Target agent ID (or "all" for broadcast)
        message: Message content
        from_agent: Sender agent ID (optional)
        delivery: Delivery type - context/notification/deferred (default: notification)
        message_type: Message type - info/request/alert/question (default: info)
        action_requested: Does sender want recipient to do something?
        context: Related context (task_id, files, etc.)
        metadata: Additional metadata (optional)

    Returns:
        Dict with message_id and status
    """
    # Validate delivery and type
    if delivery not in DELIVERY_TYPES:
        delivery = "notification"
    if message_type not in MESSAGE_TYPES:
        message_type = "info"

    # Handle broadcast to all agents
    if to_agent == "all":
        return _broadcast_message(
            idlergear_root, message, from_agent, delivery, message_type,
            action_requested, context, metadata
        )

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
        "delivery": delivery,
        "type": message_type,
        "action_requested": action_requested,
        "context": context or {},
        "read": False,
        "processed": False,  # Whether routed to task/queue
        "task_id": None,     # If converted to task
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
        "delivery": delivery,
        "type": message_type,
        "status": "delivered",
    }


def _broadcast_message(
    idlergear_root: Path,
    message: str,
    from_agent: str | None,
    delivery: str,
    message_type: str,
    action_requested: bool,
    context: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Broadcast message to all registered agents."""
    agents_file = idlergear_root / "agents" / "agents.json"

    if not agents_file.exists():
        return {"status": "no_agents", "delivered_to": []}

    try:
        with open(agents_file) as f:
            agents = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"status": "error", "delivered_to": []}

    delivered = []
    for agent_id in agents.keys():
        if agent_id != from_agent:  # Don't send to self
            result = send_message(
                idlergear_root, agent_id, message, from_agent,
                delivery=delivery, message_type=message_type,
                action_requested=action_requested, context=context, metadata=metadata
            )
            if result.get("status") == "delivered":
                delivered.append(agent_id)

    return {
        "status": "broadcast",
        "delivered_to": delivered,
        "count": len(delivered),
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


def _get_delivery_type(msg: dict[str, Any]) -> str:
    """Get delivery type from message."""
    delivery = msg.get("delivery")
    if delivery and delivery in DELIVERY_TYPES:
        return delivery
    return "notification"  # Default


def process_inbox(
    idlergear_root: Path,
    agent_id: str,
    create_task_callback: Any = None,
) -> dict[str, Any]:
    """Process inbox messages and route by delivery type.

    - context: Return for immediate injection into context
    - notification: Create task with [message] label
    - deferred: Queue for end-of-session review (just mark as processed)

    Args:
        idlergear_root: Path to .idlergear directory
        agent_id: Agent ID
        create_task_callback: Function(title, body, labels) -> task_id

    Returns:
        Dict with routing results
    """
    messages = list_messages(idlergear_root, agent_id, unread_only=True)

    results = {
        "context": [],        # Messages to inject into context
        "tasks_created": [],  # Messages converted to tasks
        "queued": [],         # Deferred messages
        "errors": [],
    }

    for msg in messages:
        msg_id = msg.get("id")
        delivery = _get_delivery_type(msg)
        msg_path = msg.get("_path")

        try:
            if delivery == "context":
                # Keep for immediate injection
                results["context"].append(msg)
                _mark_message_processed(msg_path, task_id=None)

            elif delivery == "notification":
                # Convert to task
                task_id = None
                if create_task_callback:
                    task_id = _create_task_from_message(msg, create_task_callback)

                if task_id:
                    results["tasks_created"].append({
                        "message_id": msg_id,
                        "task_id": task_id,
                        "from": msg.get("from"),
                    })
                    _mark_message_processed(msg_path, task_id=task_id)
                else:
                    # No callback, treat as context fallback
                    results["context"].append(msg)

            else:  # deferred
                # Just mark as processed, queue for later review
                results["queued"].append({
                    "message_id": msg_id,
                    "from": msg.get("from"),
                    "preview": msg.get("message", "")[:50],
                })
                _mark_message_processed(msg_path, task_id=None)

        except Exception as e:
            results["errors"].append({
                "message_id": msg_id,
                "error": str(e),
            })

    return results


def _mark_message_processed(msg_path: str | Path, task_id: int | None) -> None:
    """Mark a message as processed."""
    if not msg_path:
        return

    path = Path(msg_path)
    if not path.exists():
        return

    try:
        with open(path) as f:
            msg = json.load(f)

        msg["processed"] = True
        msg["processed_at"] = datetime.now(timezone.utc).isoformat()
        msg["read"] = True
        msg["read_at"] = msg["processed_at"]
        if task_id:
            msg["task_id"] = task_id

        with open(path, "w") as f:
            json.dump(msg, f, indent=2)
    except (json.JSONDecodeError, OSError):
        pass


def _create_task_from_message(
    msg: dict[str, Any],
    create_task_callback: Any,
) -> int | None:
    """Create a task from a message.

    Args:
        msg: Message dict
        create_task_callback: Function(title, body, labels) -> task_id

    Returns:
        Task ID if created, None otherwise
    """
    from_agent = msg.get("from", "Unknown")
    message = msg.get("message", "")
    msg_type = msg.get("type", "info")
    timestamp = msg.get("timestamp", "")
    context = msg.get("context", {})

    # Create task title
    preview = message[:60] + "..." if len(message) > 60 else message
    title = f"Message from {from_agent}: {preview}"

    # Create task body
    body_lines = [
        f"**From:** {from_agent}",
        f"**Type:** {msg_type}",
        f"**Received:** {timestamp}",
        "",
        "**Message:**",
        message,
    ]

    if context:
        body_lines.extend(["", "**Context:**"])
        if context.get("task_id"):
            body_lines.append(f"- Related task: #{context['task_id']}")
        if context.get("files"):
            body_lines.append(f"- Files: {', '.join(context['files'])}")

    if msg.get("action_requested"):
        body_lines.extend(["", "**Action Requested:** Yes"])

    body = "\n".join(body_lines)

    # Labels for the task
    labels = ["message", f"from:{from_agent}"]
    if msg_type != "info":
        labels.append(msg_type)
    if msg.get("action_requested"):
        labels.append("action-needed")

    try:
        task_id = create_task_callback(title, body, labels)
        return task_id
    except Exception:
        return None


def get_context_messages(
    idlergear_root: Path,
    agent_id: str,
) -> list[dict[str, Any]]:
    """Get only context-delivery unread messages (for hook injection).

    Args:
        idlergear_root: Path to .idlergear directory
        agent_id: Agent ID

    Returns:
        List of context messages
    """
    messages = list_messages(idlergear_root, agent_id, unread_only=True)
    return [m for m in messages if _get_delivery_type(m) == "context"]


def get_pending_review(
    idlergear_root: Path,
    agent_id: str,
) -> list[dict[str, Any]]:
    """Get messages pending user review (processed but deferred).

    Args:
        idlergear_root: Path to .idlergear directory
        agent_id: Agent ID

    Returns:
        List of deferred processed messages
    """
    messages = list_messages(idlergear_root, agent_id)
    return [
        m for m in messages
        if m.get("processed") and _get_delivery_type(m) == "deferred"
    ]


def format_context_for_injection(messages: list[dict[str, Any]]) -> str:
    """Format context messages for immediate context injection.

    Args:
        messages: List of context message dicts

    Returns:
        Formatted string for additionalContext
    """
    if not messages:
        return ""

    lines = ["📨 MESSAGE(S) FROM OTHER AGENTS:", ""]

    for msg in messages:
        from_agent = msg.get("from", "Unknown")
        content = msg.get("message", "")
        msg_type = msg.get("type", "info")

        lines.append(f"━━━ From: {from_agent} ({msg_type}) ━━━")
        lines.append(content)
        if msg.get("action_requested"):
            lines.append("⚡ ACTION REQUESTED")
        lines.append("")

    lines.append("Consider addressing these messages.")

    return "\n".join(lines)

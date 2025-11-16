"""
Message passing between LLM environments via temporary git branches.

Messages are stored as JSON files in .idlergear/messages/ and committed
to temporary sync branches. When the sync branch is deleted, messages
disappear from git history.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class MessageManager:
    """Manage message passing between LLM environments."""

    MESSAGES_DIR = ".idlergear/messages"

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.messages_dir = self.project_path / self.MESSAGES_DIR

    def _ensure_messages_dir(self):
        """Create messages directory if it doesn't exist."""
        self.messages_dir.mkdir(parents=True, exist_ok=True)

    def send_message(
        self, to: str, body: str, message_type: str = "message", from_env: str = "local"
    ) -> str:
        """
        Create a new message file.

        Args:
            to: Target environment (e.g., "web", "local")
            body: Message content
            message_type: Type of message (message, question, response, etc.)
            from_env: Source environment

        Returns:
            Message ID
        """
        self._ensure_messages_dir()

        message_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()

        message = {
            "id": message_id,
            "from": from_env,
            "to": to,
            "type": message_type,
            "timestamp": timestamp,
            "body": body,
            "status": "sent",
        }

        # Write message file
        message_file = self.messages_dir / f"{message_id}.json"
        with open(message_file, "w") as f:
            json.dump(message, f, indent=2)

        return message_id

    def list_messages(
        self,
        filter_to: Optional[str] = None,
        filter_from: Optional[str] = None,
        unread_only: bool = False,
    ) -> List[Dict]:
        """
        List all messages.

        Args:
            filter_to: Only show messages to this environment
            filter_from: Only show messages from this environment
            unread_only: Only show unread messages

        Returns:
            List of message dicts
        """
        if not self.messages_dir.exists():
            return []

        messages = []

        for message_file in self.messages_dir.glob("*.json"):
            try:
                with open(message_file, "r") as f:
                    message = json.load(f)

                # Apply filters
                if filter_to and message.get("to") != filter_to:
                    continue
                if filter_from and message.get("from") != filter_from:
                    continue
                if unread_only and message.get("status") != "sent":
                    continue

                messages.append(message)
            except Exception:
                continue

        # Sort by timestamp
        messages.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        return messages

    def read_message(self, message_id: str) -> Optional[Dict]:
        """
        Read a specific message and mark as read.

        Args:
            message_id: Message ID

        Returns:
            Message dict or None if not found
        """
        message_file = self.messages_dir / f"{message_id}.json"

        if not message_file.exists():
            return None

        with open(message_file, "r") as f:
            message = json.load(f)

        # Mark as read
        if message.get("status") == "sent":
            message["status"] = "read"
            message["read_at"] = datetime.now().isoformat()

            with open(message_file, "w") as f:
                json.dump(message, f, indent=2)

        return message

    def respond_to_message(
        self, message_id: str, body: str, from_env: str = "local"
    ) -> str:
        """
        Respond to a message.

        Args:
            message_id: ID of message to respond to
            body: Response content
            from_env: Source environment

        Returns:
            Response message ID
        """
        # Read original message
        original = self.read_message(message_id)
        if not original:
            raise ValueError(f"Message {message_id} not found")

        # Create response
        response_id = self.send_message(
            to=original["from"], body=body, message_type="response", from_env=from_env
        )

        # Link response to original
        response_file = self.messages_dir / f"{response_id}.json"
        with open(response_file, "r") as f:
            response = json.load(f)

        response["in_reply_to"] = message_id

        with open(response_file, "w") as f:
            json.dump(response, f, indent=2)

        return response_id

    def format_message_list(self, messages: List[Dict]) -> str:
        """Format message list for display."""
        if not messages:
            return "No messages found."

        lines = []
        lines.append("ID       | From     | To       | Type     | Status   | Preview")
        lines.append("-" * 70)

        for msg in messages:
            msg_id = msg.get("id", "unknown")[:8]
            from_env = msg.get("from", "unknown")[:8]
            to_env = msg.get("to", "unknown")[:8]
            msg_type = msg.get("type", "message")[:8]
            status = msg.get("status", "unknown")[:8]
            body = msg.get("body", "")[:30]

            lines.append(
                f"{msg_id} | {from_env:8} | {to_env:8} | {msg_type:8} | {status:8} | {body}"
            )

        return "\n".join(lines)

    def format_message(self, message: Dict) -> str:
        """Format single message for display."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"Message ID: {message.get('id')}")
        lines.append(f"From: {message.get('from')} → To: {message.get('to')}")
        lines.append(f"Type: {message.get('type')}")
        lines.append(f"Status: {message.get('status')}")
        lines.append(f"Sent: {message.get('timestamp')}")

        if message.get("in_reply_to"):
            lines.append(f"In reply to: {message.get('in_reply_to')}")

        lines.append("=" * 70)
        lines.append("")
        lines.append(message.get("body", ""))
        lines.append("")

        return "\n".join(lines)

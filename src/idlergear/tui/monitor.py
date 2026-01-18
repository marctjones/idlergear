"""File monitor - tail session files and yield new events."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Optional


class SessionTailer:
    """Tails a session file and yields new events as they arrive."""

    def __init__(self, session_file: Path, start_from_end: bool = True):
        """Initialize session tailer.

        Args:
            session_file: Path to session .jsonl file
            start_from_end: If True, only show new events (default: True)
        """
        self.session_file = session_file
        self.position = 0

        if start_from_end and session_file.exists():
            # Seek to end of file
            self.position = session_file.stat().st_size

    def tail(self, callback: Callable[[dict[str, Any]], None], interval: float = 0.5) -> None:
        """Tail the session file and call callback for each new event.

        Args:
            callback: Function to call with each new event
            interval: Polling interval in seconds (default: 0.5)
        """
        while True:
            if not self.session_file.exists():
                time.sleep(interval)
                continue

            try:
                with open(self.session_file, "r") as f:
                    # Seek to last position
                    f.seek(self.position)

                    # Read new lines
                    for line in f:
                        if line.strip():
                            try:
                                event = json.loads(line)
                                callback(event)
                            except json.JSONDecodeError:
                                # Skip invalid JSON lines
                                pass

                    # Update position
                    self.position = f.tell()

            except OSError:
                # File might be locked or inaccessible
                pass

            time.sleep(interval)

    def get_all_events(self) -> list[dict[str, Any]]:
        """Read all events from the session file.

        Returns:
            List of all events in the file
        """
        if not self.session_file.exists():
            return []

        events = []
        try:
            with open(self.session_file, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass

        return events


def parse_event(event: dict[str, Any]) -> dict[str, Any]:
    """Parse a session event into a display-friendly format.

    Args:
        event: Raw event from session file

    Returns:
        Parsed event with type, details, timestamp
    """
    event_type = event.get("type", "unknown")
    timestamp = event.get("timestamp", "")

    result = {
        "type": event_type,
        "timestamp": timestamp,
        "raw": event,
    }

    if event_type == "user":
        # User message
        message = event.get("content", "")
        if isinstance(message, list):
            # Extract text from content blocks
            text_parts = [
                block.get("text", "")
                for block in message
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            message = " ".join(text_parts)

        result["details"] = message[:80]  # Truncate long messages

    elif event_type == "assistant":
        # Assistant response (text only for Phase 1)
        content = event.get("content", "")
        if isinstance(content, list):
            text_parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            content = " ".join(text_parts)

        result["details"] = content[:80] if content else "[tool call]"

    elif event_type == "tool_use":
        # Tool call
        tool_name = event.get("name", "unknown")
        tool_input = event.get("input", {})

        # Extract relevant details from input
        details = tool_name
        if "file_path" in tool_input:
            details = f"{tool_name}: {tool_input['file_path']}"
        elif "path" in tool_input:
            details = f"{tool_name}: {tool_input['path']}"
        elif "command" in tool_input:
            cmd = tool_input["command"]
            if len(cmd) > 40:
                cmd = cmd[:37] + "..."
            details = f"{tool_name}: {cmd}"

        result["details"] = details

    elif event_type == "tool_result":
        # Tool result
        tool_id = event.get("tool_use_id", "")
        is_error = event.get("is_error", False)
        result["details"] = "Error" if is_error else "Success"
        result["error"] = is_error

    else:
        # Unknown event type
        result["details"] = str(event)[:80]

    return result

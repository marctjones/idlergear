"""Command queue system for async execution and multi-agent coordination."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class CommandStatus(Enum):
    """Status of a queued command."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueuedCommand:
    """A command queued for execution by an AI agent."""

    id: str
    prompt: str
    created_at: str
    status: CommandStatus = CommandStatus.PENDING
    assigned_to: Optional[str] = None  # agent_id
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    priority: int = 0  # Higher = more urgent
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueuedCommand":
        """Create from dictionary."""
        data["status"] = CommandStatus(data["status"])
        return cls(**data)


class CommandQueue:
    """Command queue for async execution."""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._queue_file = self.storage_path / "queue.json"
        self._lock = asyncio.Lock()
        self._commands: dict[str, QueuedCommand] = {}
        self._load()

    def _load(self) -> None:
        """Load queue from disk."""
        if self._queue_file.exists():
            try:
                data = json.loads(self._queue_file.read_text())
                self._commands = {
                    cmd_id: QueuedCommand.from_dict(cmd_data)
                    for cmd_id, cmd_data in data.items()
                }
            except (json.JSONDecodeError, KeyError, ValueError):
                # Corrupted file, start fresh
                self._commands = {}

    async def _save(self) -> None:
        """Save queue to disk."""
        data = {cmd_id: cmd.to_dict() for cmd_id, cmd in self._commands.items()}
        self._queue_file.write_text(json.dumps(data, indent=2))

    async def add(
        self,
        prompt: str,
        priority: int = 0,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """Add a command to the queue. Returns command ID."""
        async with self._lock:
            cmd_id = str(uuid.uuid4())
            command = QueuedCommand(
                id=cmd_id,
                prompt=prompt,
                created_at=datetime.now(timezone.utc).isoformat(),
                priority=priority,
                tags=tags or [],
                metadata=metadata or {},
            )
            self._commands[cmd_id] = command
            await self._save()
            return cmd_id

    async def get(self, cmd_id: str) -> Optional[QueuedCommand]:
        """Get a command by ID."""
        return self._commands.get(cmd_id)

    async def list(
        self,
        status: Optional[CommandStatus] = None,
        agent_id: Optional[str] = None,
    ) -> list[QueuedCommand]:
        """List commands, optionally filtered by status or agent."""
        commands = list(self._commands.values())

        if status:
            commands = [c for c in commands if c.status == status]

        if agent_id:
            commands = [c for c in commands if c.assigned_to == agent_id]

        # Sort by priority (descending), then creation time (ascending)
        commands.sort(key=lambda c: (-c.priority, c.created_at))
        return commands

    async def assign(self, cmd_id: str, agent_id: str) -> bool:
        """Assign a command to an agent."""
        async with self._lock:
            command = self._commands.get(cmd_id)
            if not command or command.status != CommandStatus.PENDING:
                return False

            command.status = CommandStatus.ASSIGNED
            command.assigned_to = agent_id
            await self._save()
            return True

    async def start(self, cmd_id: str) -> bool:
        """Mark a command as started."""
        async with self._lock:
            command = self._commands.get(cmd_id)
            if not command or command.status not in (
                CommandStatus.PENDING,
                CommandStatus.ASSIGNED,
            ):
                return False

            command.status = CommandStatus.RUNNING
            command.started_at = datetime.now(timezone.utc).isoformat()
            await self._save()
            return True

    async def complete(
        self, cmd_id: str, result: dict[str, Any], error: Optional[str] = None
    ) -> bool:
        """Mark a command as completed."""
        async with self._lock:
            command = self._commands.get(cmd_id)
            if not command:
                return False

            if error:
                command.status = CommandStatus.FAILED
                command.error = error
            else:
                command.status = CommandStatus.COMPLETED
                command.result = result

            command.completed_at = datetime.now(timezone.utc).isoformat()
            await self._save()
            return True

    async def cancel(self, cmd_id: str) -> bool:
        """Cancel a pending command."""
        async with self._lock:
            command = self._commands.get(cmd_id)
            if not command or command.status in (
                CommandStatus.COMPLETED,
                CommandStatus.FAILED,
                CommandStatus.CANCELLED,
            ):
                return False

            command.status = CommandStatus.CANCELLED
            command.completed_at = datetime.now(timezone.utc).isoformat()
            await self._save()
            return True

    async def poll_pending(self, agent_id: str) -> Optional[QueuedCommand]:
        """Poll for a pending command and assign it to the agent."""
        async with self._lock:
            # Find highest priority pending command
            pending = [
                c for c in self._commands.values() if c.status == CommandStatus.PENDING
            ]
            if not pending:
                return None

            # Sort by priority (descending), then creation time (ascending)
            pending.sort(key=lambda c: (-c.priority, c.created_at))
            command = pending[0]

            # Assign it
            command.status = CommandStatus.ASSIGNED
            command.assigned_to = agent_id
            await self._save()
            return command

    async def cleanup_old(self, days: int = 7) -> int:
        """Remove completed/failed commands older than N days. Returns count removed."""
        async with self._lock:
            cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
            to_remove = []

            for cmd_id, command in self._commands.items():
                if command.status in (
                    CommandStatus.COMPLETED,
                    CommandStatus.FAILED,
                    CommandStatus.CANCELLED,
                ):
                    if command.completed_at:
                        completed_ts = datetime.fromisoformat(
                            command.completed_at
                        ).timestamp()
                        if completed_ts < cutoff:
                            to_remove.append(cmd_id)

            for cmd_id in to_remove:
                del self._commands[cmd_id]

            if to_remove:
                await self._save()

            return len(to_remove)

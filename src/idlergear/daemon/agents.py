"""Agent session registry for multi-agent coordination."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class AgentSession:
    """Represents an active AI agent session."""

    agent_id: str
    agent_type: str  # "claude-code", "goose", "aider", etc.
    connected_at: str
    last_heartbeat: str
    connection_id: int  # Daemon connection ID
    status: str = "active"  # active, idle, busy
    current_task: Optional[str] = None  # Current command ID
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Session tracking fields (for multi-client coordination)
    session_id: Optional[str] = None  # IdlerGear session ID
    session_name: Optional[str] = None  # Human-readable session name
    working_files: list[str] = field(default_factory=list)  # Files being worked on
    current_task_id: Optional[int] = None  # IdlerGear task ID

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentSession":
        """Create from dictionary."""
        return cls(**data)

    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """Check if session is stale (no heartbeat for N seconds)."""
        last_hb = datetime.fromisoformat(self.last_heartbeat)
        age = (datetime.now(timezone.utc) - last_hb).total_seconds()
        return age > timeout_seconds


class AgentRegistry:
    """Registry of active AI agent sessions."""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._registry_file = self.storage_path / "agents.json"
        self._lock = asyncio.Lock()
        self._agents: dict[str, AgentSession] = {}
        self._load()

    def _load(self) -> None:
        """Load registry from disk."""
        if self._registry_file.exists():
            try:
                data = json.loads(self._registry_file.read_text())
                self._agents = {
                    agent_id: AgentSession.from_dict(agent_data)
                    for agent_id, agent_data in data.items()
                }
            except (json.JSONDecodeError, KeyError, ValueError):
                self._agents = {}

    async def _save(self) -> None:
        """Save registry to disk."""
        data = {agent_id: agent.to_dict() for agent_id, agent in self._agents.items()}
        self._registry_file.write_text(json.dumps(data, indent=2))

    async def register(
        self,
        agent_id: str,
        agent_type: str,
        connection_id: int,
        capabilities: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
        session_name: Optional[str] = None,
        working_files: Optional[list[str]] = None,
        current_task_id: Optional[int] = None,
    ) -> AgentSession:
        """Register a new agent session."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            session = AgentSession(
                agent_id=agent_id,
                agent_type=agent_type,
                connected_at=now,
                last_heartbeat=now,
                connection_id=connection_id,
                capabilities=capabilities or [],
                metadata=metadata or {},
                session_id=session_id,
                session_name=session_name,
                working_files=working_files or [],
                current_task_id=current_task_id,
            )
            self._agents[agent_id] = session
            await self._save()
            return session

    async def unregister(self, agent_id: str) -> bool:
        """Unregister an agent session."""
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                await self._save()
                return True
            return False

    async def get(self, agent_id: str) -> Optional[AgentSession]:
        """Get an agent session by ID."""
        return self._agents.get(agent_id)

    async def list(
        self, agent_type: Optional[str] = None, status: Optional[str] = None
    ) -> list[AgentSession]:
        """List all agent sessions, optionally filtered."""
        agents = list(self._agents.values())

        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]

        if status:
            agents = [a for a in agents if a.status == status]

        return agents

    async def heartbeat(self, agent_id: str) -> bool:
        """Update agent's last heartbeat timestamp."""
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False

            agent.last_heartbeat = datetime.now(timezone.utc).isoformat()
            await self._save()
            return True

    async def update_status(
        self,
        agent_id: str,
        status: str,
        current_task: Optional[str] = None,
    ) -> bool:
        """Update agent status and current task."""
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False

            agent.status = status
            agent.current_task = current_task
            agent.last_heartbeat = datetime.now(timezone.utc).isoformat()
            await self._save()
            return True

    async def update_session(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        session_name: Optional[str] = None,
        working_files: Optional[list[str]] = None,
        current_task_id: Optional[int] = None,
    ) -> bool:
        """Update agent's session information."""
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return False

            if session_id is not None:
                agent.session_id = session_id
            if session_name is not None:
                agent.session_name = session_name
            if working_files is not None:
                agent.working_files = working_files
            if current_task_id is not None:
                agent.current_task_id = current_task_id

            agent.last_heartbeat = datetime.now(timezone.utc).isoformat()
            await self._save()
            return True

    async def cleanup_stale(self, timeout_seconds: int = 300) -> int:
        """Remove stale agent sessions. Returns count removed."""
        async with self._lock:
            to_remove = [
                agent_id
                for agent_id, agent in self._agents.items()
                if agent.is_stale(timeout_seconds)
            ]

            for agent_id in to_remove:
                del self._agents[agent_id]

            if to_remove:
                await self._save()

            return len(to_remove)

    async def get_by_connection(self, connection_id: int) -> Optional[AgentSession]:
        """Find agent by connection ID."""
        for agent in self._agents.values():
            if agent.connection_id == connection_id:
                return agent
        return None

    async def get_available_agents(
        self, capability: Optional[str] = None
    ) -> list[AgentSession]:
        """Get list of available (idle/active) agents, optionally filtered by capability."""
        agents = [
            a
            for a in self._agents.values()
            if a.status in ("active", "idle") and not a.is_stale()
        ]

        if capability:
            agents = [a for a in agents if capability in a.capabilities]

        return agents

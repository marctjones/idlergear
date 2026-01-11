"""Write locking system for coordinated multi-agent writes."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Lock:
    """Represents a write lock held by an agent."""

    resource: str  # e.g., "task:42", "vision", "plan:auth-system"
    agent_id: str
    acquired_at: float
    expires_at: float


class LockManager:
    """Manages write locks for multi-agent coordination."""

    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self._locks: dict[str, Lock] = {}
        self._lock = asyncio.Lock()

    async def acquire(
        self,
        resource: str,
        agent_id: str,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Acquire a lock on a resource.

        Args:
            resource: Resource identifier (e.g., "task:42")
            agent_id: Agent requesting the lock
            timeout: Lock timeout in seconds (default: 30s)

        Returns:
            True if lock acquired, False if already locked by another agent
        """
        async with self._lock:
            await self._cleanup_expired()

            # Check if resource is locked
            if resource in self._locks:
                existing = self._locks[resource]
                # Allow same agent to re-acquire
                if existing.agent_id == agent_id:
                    # Refresh expiration
                    lock_timeout = timeout or self.default_timeout
                    existing.expires_at = time.time() + lock_timeout
                    return True
                else:
                    # Locked by another agent
                    return False

            # Acquire new lock
            lock_timeout = timeout or self.default_timeout
            now = time.time()
            lock = Lock(
                resource=resource,
                agent_id=agent_id,
                acquired_at=now,
                expires_at=now + lock_timeout,
            )
            self._locks[resource] = lock
            return True

    async def release(self, resource: str, agent_id: str) -> bool:
        """
        Release a lock on a resource.

        Args:
            resource: Resource identifier
            agent_id: Agent releasing the lock

        Returns:
            True if lock was released, False if not held by this agent
        """
        async with self._lock:
            if resource not in self._locks:
                return False

            lock = self._locks[resource]
            if lock.agent_id != agent_id:
                return False

            del self._locks[resource]
            return True

    async def is_locked(self, resource: str) -> bool:
        """Check if a resource is currently locked."""
        async with self._lock:
            await self._cleanup_expired()
            return resource in self._locks

    async def get_lock(self, resource: str) -> Optional[Lock]:
        """Get lock information for a resource."""
        async with self._lock:
            await self._cleanup_expired()
            return self._locks.get(resource)

    async def release_all(self, agent_id: str) -> int:
        """Release all locks held by an agent. Returns count released."""
        async with self._lock:
            to_release = [
                resource
                for resource, lock in self._locks.items()
                if lock.agent_id == agent_id
            ]

            for resource in to_release:
                del self._locks[resource]

            return len(to_release)

    async def list_locks(self, agent_id: Optional[str] = None) -> list[Lock]:
        """List all active locks, optionally filtered by agent."""
        async with self._lock:
            await self._cleanup_expired()
            locks = list(self._locks.values())

            if agent_id:
                locks = [l for l in locks if l.agent_id == agent_id]

            return locks

    async def _cleanup_expired(self) -> None:
        """Remove expired locks (internal, assumes _lock is held)."""
        now = time.time()
        expired = [
            resource for resource, lock in self._locks.items() if lock.expires_at <= now
        ]

        for resource in expired:
            del self._locks[resource]

    async def force_release(self, resource: str) -> bool:
        """Force release a lock (admin operation). Returns True if lock existed."""
        async with self._lock:
            if resource in self._locks:
                del self._locks[resource]
                return True
            return False

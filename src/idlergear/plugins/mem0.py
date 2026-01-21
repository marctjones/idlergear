"""Mem0 experiential memory plugin.

Provides adaptive memory that learns patterns across IdlerGear sessions:
- Automatic learning from tasks, notes, and decisions
- Pattern recognition and suggestion
- Session-aware context with 90% token savings

Configuration (config.toml):
    [plugins.mem0]
    enabled = true
    api_key = "m0-..."  # Optional, uses MEM0_API_KEY env var
    # Alternative: Local deployment
    # host = "http://localhost:8000"

Example:
    # Enable in config.toml
    [plugins.mem0]
    enabled = true

    # Plugin automatically learns from IdlerGear usage
    # Provides smart suggestions based on patterns
"""

import os
from typing import Any, Dict, List, Optional

from .base import IdlerGearPlugin, PluginCapability


class Mem0Plugin(IdlerGearPlugin):
    """Mem0 experiential memory integration.

    Provides adaptive memory that learns from IdlerGear usage:
    - Automatic pattern learning from tasks and decisions
    - Context-aware suggestions based on history
    - Session memory with 90% token savings
    - Learns team patterns and best practices
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Mem0 plugin.

        Args:
            config: Plugin configuration from config.toml
        """
        super().__init__(config)
        self.client: Optional[Any] = None  # Mem0 client instance
        self._api_key: Optional[str] = None
        self._host: str = "https://api.mem0.ai"
        self._user_id: str = "idlergear"

    def name(self) -> str:
        """Return plugin name."""
        return "mem0"

    def capabilities(self) -> List[PluginCapability]:
        """Return capabilities provided."""
        return [
            PluginCapability.MEMORY_EXPERIENTIAL,
            PluginCapability.MEMORY_HIERARCHICAL,
            PluginCapability.MEMORY_PATTERN_LEARNING,
        ]

    def initialize(self) -> None:
        """Initialize Mem0 client.

        Loads API key from config or environment variables.
        Creates Mem0 client instance for memory operations.

        Raises:
            ImportError: If mem0ai package not installed
            ValueError: If API key not provided
        """
        # Load API key (config takes precedence over env vars)
        self._api_key = self.config.get("api_key", os.getenv("MEM0_API_KEY"))
        self._host = self.config.get("host", self._host)
        self._user_id = self.config.get("user_id", self._user_id)

        # Check API key (only required for cloud)
        if self._host == "https://api.mem0.ai" and not self._api_key:
            raise ValueError(
                "Mem0 API key not found. "
                "Provide api_key in config.toml or set MEM0_API_KEY environment variable. "
                "Get your key at: https://app.mem0.ai"
            )

        # Import mem0ai (optional dependency)
        try:
            from mem0 import Memory
        except ImportError:
            raise ImportError(
                "mem0ai package not installed. " "Install with: pip install mem0ai"
            )

        # Create client
        if self._api_key:
            self.client = Memory(api_key=self._api_key)
        else:
            # Local deployment
            self.client = Memory(host=self._host)

        self.mark_initialized()

    def shutdown(self) -> None:
        """Shutdown Mem0 client.

        Cleans up any pending operations.
        """
        if self.client:
            self.client = None

    def health_check(self) -> bool:
        """Check if Mem0 is accessible.

        Returns:
            True if Mem0 API is reachable
        """
        if not self.client:
            return False

        try:
            # Simple health check - try to get memories
            self.client.get_all(user_id=self._user_id, limit=1)
            return True
        except Exception:
            return False

    def add_memory(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a memory to Mem0.

        Args:
            text: Memory text
            metadata: Optional metadata (type, tags, etc.)

        Returns:
            Memory ID
        """
        if not self.client:
            raise RuntimeError("Plugin not initialized")

        result = self.client.add(
            text, user_id=self._user_id, metadata=metadata or {}
        )

        return result.get("id", "")

    def search_memories(
        self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search memories by query.

        Args:
            query: Search query
            limit: Number of results to return
            filters: Optional filters for metadata

        Returns:
            List of matching memories with scores
        """
        if not self.client:
            raise RuntimeError("Plugin not initialized")

        results = self.client.search(
            query, user_id=self._user_id, limit=limit, filters=filters or {}
        )

        return results

    def get_all_memories(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all memories for the user.

        Args:
            limit: Maximum number of memories to return

        Returns:
            List of memories
        """
        if not self.client:
            raise RuntimeError("Plugin not initialized")

        memories = self.client.get_all(user_id=self._user_id, limit=limit)

        return memories

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if deleted successfully
        """
        if not self.client:
            raise RuntimeError("Plugin not initialized")

        try:
            self.client.delete(memory_id, user_id=self._user_id)
            return True
        except Exception:
            return False

    def remember_task(self, task: Dict[str, Any]) -> str:
        """Remember a task for pattern learning.

        Args:
            task: Task dict with title, body, labels, etc.

        Returns:
            Memory ID
        """
        text = f"Task: {task.get('title', '')} - {task.get('body', '')}"
        metadata = {
            "type": "task",
            "labels": task.get("labels", []),
            "priority": task.get("priority", ""),
        }

        return self.add_memory(text, metadata)

    def remember_decision(self, decision: str, context: Optional[str] = None) -> str:
        """Remember a design decision.

        Args:
            decision: The decision made
            context: Optional context about why

        Returns:
            Memory ID
        """
        text = f"Decision: {decision}"
        if context:
            text += f" - Context: {context}"

        metadata = {"type": "decision"}

        return self.add_memory(text, metadata)

    def remember_learning(self, learning: str, tags: Optional[List[str]] = None) -> str:
        """Remember a learning or insight.

        Args:
            learning: The learning/insight
            tags: Optional tags for categorization

        Returns:
            Memory ID
        """
        text = f"Learning: {learning}"
        metadata = {"type": "learning", "tags": tags or []}

        return self.add_memory(text, metadata)

    def get_context_for_task(self, task_title: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get relevant memories for a task.

        Args:
            task_title: Task title to search for
            limit: Number of relevant memories to return

        Returns:
            List of relevant memories
        """
        return self.search_memories(task_title, limit=limit, filters={"type": "task"})

    def get_related_decisions(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get related design decisions.

        Args:
            query: Query to search for
            limit: Number of decisions to return

        Returns:
            List of relevant decisions
        """
        return self.search_memories(query, limit=limit, filters={"type": "decision"})

    def get_patterns(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get learned patterns.

        Args:
            category: Optional category filter (task, decision, learning)

        Returns:
            List of pattern memories
        """
        filters = {}
        if category:
            filters["type"] = category

        return self.get_all_memories(limit=50)

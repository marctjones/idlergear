"""Integration between FileRegistry and Daemon for multi-agent coordination."""

import asyncio
from typing import Any, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FileRegistryDaemonBridge:
    """Bridge between FileRegistry events and Daemon broadcasts.

    This class listens to FileRegistry events and broadcasts them to all
    connected agents via the daemon, enabling multi-agent coordination.
    """

    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize the bridge.

        Args:
            registry_path: Path to file registry (defaults to .idlergear/file_registry.json)
        """
        self.registry_path = registry_path
        self._daemon_client = None
        self._registry = None

    async def start(self) -> None:
        """Start the bridge by connecting to daemon and registry."""
        try:
            from idlergear.daemon.client import DaemonClient
            from idlergear.file_registry import FileRegistry

            # Connect to daemon
            self._daemon_client = DaemonClient()
            await self._daemon_client.connect()

            # Subscribe to registry events
            self._registry = FileRegistry(self.registry_path)
            self._registry.on("file_registered", self._on_file_registered)
            self._registry.on("file_deprecated", self._on_file_deprecated)

            logger.info("FileRegistry-Daemon bridge started")
        except Exception as e:
            logger.warning(f"Failed to start FileRegistry-Daemon bridge: {e}")
            # Don't fail if daemon isn't available - just degrade gracefully

    async def stop(self) -> None:
        """Stop the bridge."""
        if self._daemon_client:
            await self._daemon_client.disconnect()
            self._daemon_client = None

    def _on_file_registered(self, data: Dict[str, Any]) -> None:
        """Handle file_registered event from FileRegistry."""
        # Run async broadcast in event loop
        if self._daemon_client:
            asyncio.create_task(self._broadcast_registry_change("registered", data))

    def _on_file_deprecated(self, data: Dict[str, Any]) -> None:
        """Handle file_deprecated event from FileRegistry."""
        # Run async broadcast in event loop
        if self._daemon_client:
            asyncio.create_task(self._broadcast_registry_change("deprecated", data))

    async def _broadcast_registry_change(
        self, action: str, data: Dict[str, Any]
    ) -> None:
        """Broadcast registry change to all agents via daemon.

        Args:
            action: "registered" or "deprecated"
            data: Event data from FileRegistry
        """
        try:
            # Construct broadcast message
            message = {
                "type": "registry_changed",
                "action": action,
                "file_path": data.get("path"),
                "successor": data.get("successor"),
                "reason": data.get("reason"),
                "status": data.get("status"),
                "timestamp": data.get("timestamp"),
            }

            # Broadcast via daemon
            await self._daemon_client.call("message.broadcast", {
                "event": "file_registry.changed",
                "data": message
            })

            logger.debug(f"Broadcasted file registry change: {action} {data.get('path')}")
        except Exception as e:
            logger.warning(f"Failed to broadcast registry change: {e}")


# Global instance for integration with FileRegistry
_bridge_instance: Optional[FileRegistryDaemonBridge] = None


async def init_file_registry_daemon_bridge(registry_path: Optional[Path] = None) -> None:
    """Initialize the global FileRegistry-Daemon bridge.

    Args:
        registry_path: Path to file registry
    """
    global _bridge_instance

    if _bridge_instance is None:
        _bridge_instance = FileRegistryDaemonBridge(registry_path)
        await _bridge_instance.start()


async def stop_file_registry_daemon_bridge() -> None:
    """Stop the global FileRegistry-Daemon bridge."""
    global _bridge_instance

    if _bridge_instance:
        await _bridge_instance.stop()
        _bridge_instance = None


def get_file_registry_bridge() -> Optional[FileRegistryDaemonBridge]:
    """Get the global FileRegistry-Daemon bridge instance.

    Returns:
        Bridge instance or None if not initialized
    """
    return _bridge_instance

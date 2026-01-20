"""Base plugin system for IdlerGear integrations."""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import toml


class PluginCapability(str, Enum):
    """Capabilities that plugins can provide."""

    # Observability
    OBSERVABILITY_EXPORT = "observability.export"
    OBSERVABILITY_METRICS = "observability.metrics"
    OBSERVABILITY_TRACING = "observability.tracing"

    # Vector Search
    VECTOR_SEARCH = "vector.search"
    VECTOR_EMBEDDING = "vector.embedding"
    VECTOR_STORAGE = "vector.storage"

    # Memory
    MEMORY_EXPERIENTIAL = "memory.experiential"
    MEMORY_HIERARCHICAL = "memory.hierarchical"
    MEMORY_PATTERN_LEARNING = "memory.pattern_learning"

    # RAG
    RAG_RETRIEVAL = "rag.retrieval"
    RAG_GRAPH = "rag.graph"
    RAG_HYBRID = "rag.hybrid"


class PluginConfig:
    """Plugin configuration loaded from config.toml."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize plugin config.

        Args:
            config_path: Path to config.toml (defaults to .idlergear/config.toml)
        """
        if config_path is None:
            config_path = Path.cwd() / ".idlergear" / "config.toml"

        self.config_path = config_path
        self.config: Dict[str, Any] = {}

        if config_path.exists():
            self.config = toml.load(config_path)

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin configuration dict (empty if not configured)
        """
        plugins = self.config.get("plugins", {})
        return plugins.get(plugin_name, {})

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled.

        Args:
            plugin_name: Name of the plugin

        Returns:
            True if enabled (defaults to False if not configured)
        """
        plugin_config = self.get_plugin_config(plugin_name)
        return plugin_config.get("enabled", False)


class IdlerGearPlugin(ABC):
    """Base class for all IdlerGear plugins.

    Plugins extend IdlerGear functionality by integrating with external tools.
    All plugins must implement this interface.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the plugin.

        Args:
            config: Plugin configuration from config.toml
        """
        self.config = config
        self._initialized = False

    @abstractmethod
    def name(self) -> str:
        """Return the plugin name.

        Returns:
            Plugin name (e.g., "langfuse", "llama-index")
        """
        pass

    @abstractmethod
    def capabilities(self) -> List[PluginCapability]:
        """Return list of capabilities this plugin provides.

        Returns:
            List of PluginCapability enums
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the plugin.

        This is called once when the plugin is loaded.
        Setup connections, load models, etc.

        Raises:
            Exception: If initialization fails
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the plugin.

        Cleanup resources, close connections, etc.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the plugin is healthy.

        Returns:
            True if plugin is working correctly
        """
        pass

    def is_initialized(self) -> bool:
        """Check if plugin has been initialized.

        Returns:
            True if initialize() has been called
        """
        return self._initialized

    def mark_initialized(self) -> None:
        """Mark plugin as initialized."""
        self._initialized = True


class PluginRegistry:
    """Registry for managing IdlerGear plugins.

    The registry loads plugins from configuration and manages their lifecycle.
    """

    def __init__(self, config: Optional[PluginConfig] = None):
        """Initialize the plugin registry.

        Args:
            config: Plugin configuration (loads default if None)
        """
        self.config = config or PluginConfig()
        self.plugins: Dict[str, IdlerGearPlugin] = {}
        self._plugin_classes: Dict[str, type] = {}

    def register_plugin_class(self, plugin_class: type) -> None:
        """Register a plugin class.

        Args:
            plugin_class: Plugin class (must inherit from IdlerGearPlugin)

        Raises:
            ValueError: If plugin_class is not a valid plugin
        """
        if not issubclass(plugin_class, IdlerGearPlugin):
            raise ValueError(f"{plugin_class} must inherit from IdlerGearPlugin")

        # Instantiate to get name
        temp_instance = plugin_class({})
        plugin_name = temp_instance.name()

        self._plugin_classes[plugin_name] = plugin_class

    def load_plugin(self, plugin_name: str) -> Optional[IdlerGearPlugin]:
        """Load and initialize a plugin.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            Initialized plugin instance, or None if not enabled/registered

        Raises:
            Exception: If plugin initialization fails
        """
        # Check if enabled
        if not self.config.is_plugin_enabled(plugin_name):
            return None

        # Check if already loaded
        if plugin_name in self.plugins:
            return self.plugins[plugin_name]

        # Check if registered
        if plugin_name not in self._plugin_classes:
            raise ValueError(f"Plugin not registered: {plugin_name}")

        # Instantiate plugin
        plugin_class = self._plugin_classes[plugin_name]
        plugin_config = self.config.get_plugin_config(plugin_name)
        plugin = plugin_class(plugin_config)

        # Initialize
        plugin.initialize()
        plugin.mark_initialized()

        # Store
        self.plugins[plugin_name] = plugin

        return plugin

    def load_all_plugins(self) -> None:
        """Load all enabled plugins."""
        for plugin_name in self._plugin_classes.keys():
            if self.config.is_plugin_enabled(plugin_name):
                self.load_plugin(plugin_name)

    def get_plugin(self, plugin_name: str) -> Optional[IdlerGearPlugin]:
        """Get a loaded plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance, or None if not loaded
        """
        return self.plugins.get(plugin_name)

    def get_plugins_by_capability(
        self, capability: PluginCapability
    ) -> List[IdlerGearPlugin]:
        """Get all plugins that provide a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of plugins with that capability
        """
        return [
            plugin
            for plugin in self.plugins.values()
            if capability in plugin.capabilities()
        ]

    def shutdown_all(self) -> None:
        """Shutdown all loaded plugins."""
        for plugin in self.plugins.values():
            plugin.shutdown()
        self.plugins.clear()

    def list_available_plugins(self) -> List[str]:
        """List all registered plugin names.

        Returns:
            List of plugin names
        """
        return list(self._plugin_classes.keys())

    def list_loaded_plugins(self) -> List[str]:
        """List all currently loaded plugin names.

        Returns:
            List of loaded plugin names
        """
        return list(self.plugins.keys())

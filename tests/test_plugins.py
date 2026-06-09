"""Tests for plugin system."""

import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from idlergear.plugins.base import (
    IdlerGearPlugin,
    PluginCapability,
    PluginConfig,
    PluginRegistry,
)


class MockPlugin(IdlerGearPlugin):
    """Mock plugin for testing."""

    def name(self) -> str:
        return "mock"

    def capabilities(self) -> List[PluginCapability]:
        return [PluginCapability.OBSERVABILITY_METRICS]

    def initialize(self) -> None:
        self.mark_initialized()

    def shutdown(self) -> None:
        pass

    def health_check(self) -> bool:
        return self.is_initialized()


class AnotherMockPlugin(IdlerGearPlugin):
    """Another mock plugin for testing."""

    def name(self) -> str:
        return "another"

    def capabilities(self) -> List[PluginCapability]:
        return [PluginCapability.OBSERVABILITY_EXPORT]

    def initialize(self) -> None:
        self.mark_initialized()

    def shutdown(self) -> None:
        pass

    def health_check(self) -> bool:
        return True


def test_plugin_config_no_file():
    """Test PluginConfig with non-existent file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "nonexistent.toml"
        config = PluginConfig(config_path)

        assert config.get_plugin_config("test") == {}
        assert config.is_plugin_enabled("test") is False


def test_plugin_config_with_file():
    """Test PluginConfig with config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"

        # Write config
        config_path.write_text(
            """
[plugins.mock]
enabled = true
setting1 = "value1"

[plugins.disabled]
enabled = false
"""
        )

        config = PluginConfig(config_path)

        # Check enabled plugin
        mock_config = config.get_plugin_config("mock")
        assert mock_config["enabled"] is True
        assert mock_config["setting1"] == "value1"
        assert config.is_plugin_enabled("mock") is True

        # Check disabled plugin
        assert config.is_plugin_enabled("disabled") is False


def test_plugin_registry_register():
    """Test registering plugin classes."""
    registry = PluginRegistry()

    registry.register_plugin_class(MockPlugin)
    assert "mock" in registry.list_available_plugins()


def test_plugin_registry_register_invalid():
    """Test registering invalid plugin class."""
    registry = PluginRegistry()

    with pytest.raises(ValueError, match="must inherit from IdlerGearPlugin"):
        registry.register_plugin_class(dict)  # type: ignore


def test_plugin_registry_load_disabled():
    """Test loading disabled plugin returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(
            """
[plugins.mock]
enabled = false
"""
        )

        config = PluginConfig(config_path)
        registry = PluginRegistry(config)
        registry.register_plugin_class(MockPlugin)

        plugin = registry.load_plugin("mock")
        assert plugin is None


def test_plugin_registry_load_enabled():
    """Test loading enabled plugin."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(
            """
[plugins.mock]
enabled = true
"""
        )

        config = PluginConfig(config_path)
        registry = PluginRegistry(config)
        registry.register_plugin_class(MockPlugin)

        plugin = registry.load_plugin("mock")
        assert plugin is not None
        assert plugin.name() == "mock"
        assert plugin.is_initialized()


def test_plugin_registry_load_unregistered():
    """Test loading unregistered plugin raises error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(
            """
[plugins.nonexistent]
enabled = true
"""
        )

        config = PluginConfig(config_path)
        registry = PluginRegistry(config)

        with pytest.raises(ValueError, match="Plugin not registered"):
            registry.load_plugin("nonexistent")


def test_plugin_registry_get_plugin():
    """Test getting loaded plugin."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(
            """
[plugins.mock]
enabled = true
"""
        )

        config = PluginConfig(config_path)
        registry = PluginRegistry(config)
        registry.register_plugin_class(MockPlugin)

        # Load plugin
        plugin1 = registry.load_plugin("mock")

        # Get plugin (should return same instance)
        plugin2 = registry.get_plugin("mock")

        assert plugin1 is plugin2


def test_plugin_registry_get_by_capability():
    """Test getting plugins by capability."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(
            """
[plugins.mock]
enabled = true

[plugins.another]
enabled = true
"""
        )

        config = PluginConfig(config_path)
        registry = PluginRegistry(config)
        registry.register_plugin_class(MockPlugin)
        registry.register_plugin_class(AnotherMockPlugin)

        # Load all
        registry.load_all_plugins()

        # Get by capability
        metrics_plugins = registry.get_plugins_by_capability(
            PluginCapability.OBSERVABILITY_METRICS
        )
        assert len(metrics_plugins) == 1
        assert metrics_plugins[0].name() == "mock"

        observability_plugins = registry.get_plugins_by_capability(
            PluginCapability.OBSERVABILITY_EXPORT
        )
        assert len(observability_plugins) == 1
        assert observability_plugins[0].name() == "another"


def test_plugin_registry_load_all():
    """Test loading all enabled plugins."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(
            """
[plugins.mock]
enabled = true

[plugins.another]
enabled = true
"""
        )

        config = PluginConfig(config_path)
        registry = PluginRegistry(config)
        registry.register_plugin_class(MockPlugin)
        registry.register_plugin_class(AnotherMockPlugin)

        registry.load_all_plugins()

        loaded = registry.list_loaded_plugins()
        assert "mock" in loaded
        assert "another" in loaded


def test_plugin_registry_shutdown():
    """Test shutting down all plugins."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(
            """
[plugins.mock]
enabled = true
"""
        )

        config = PluginConfig(config_path)
        registry = PluginRegistry(config)
        registry.register_plugin_class(MockPlugin)

        registry.load_all_plugins()
        assert len(registry.list_loaded_plugins()) == 1

        registry.shutdown_all()
        assert len(registry.list_loaded_plugins()) == 0


def test_plugin_health_check():
    """Test plugin health check."""
    plugin = MockPlugin({})

    # Not initialized yet
    assert plugin.health_check() is False

    # Initialize
    plugin.initialize()
    assert plugin.health_check() is True

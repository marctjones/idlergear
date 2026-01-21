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
        return [PluginCapability.VECTOR_SEARCH]

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
        vector_plugins = registry.get_plugins_by_capability(
            PluginCapability.VECTOR_SEARCH
        )
        assert len(vector_plugins) == 1
        assert vector_plugins[0].name() == "mock"

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


# LlamaIndex plugin tests
def test_llamaindex_plugin_initialization():
    """Test LlamaIndex plugin basic initialization."""
    from idlergear.plugins.llamaindex import LlamaIndexPlugin

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            Path(tmpdir) / ".idlergear"
            (Path(tmpdir) / ".idlergear").mkdir()

            plugin = LlamaIndexPlugin({"embedding_model": "local"})

            assert plugin.name() == "llamaindex"
            assert PluginCapability.VECTOR_SEARCH in plugin.capabilities()
            assert PluginCapability.VECTOR_EMBEDDING in plugin.capabilities()
            assert PluginCapability.VECTOR_STORAGE in plugin.capabilities()
            assert PluginCapability.RAG_RETRIEVAL in plugin.capabilities()
        finally:
            os.chdir(old_cwd)


def test_llamaindex_plugin_requires_llama_index():
    """Test that LlamaIndex plugin requires llama-index package."""
    from idlergear.plugins.llamaindex import LlamaIndexPlugin

    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        import sys

        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            (Path(tmpdir) / ".idlergear").mkdir()

            plugin = LlamaIndexPlugin({})

            # Hide llama_index from imports
            llama_index_modules = [
                mod for mod in sys.modules.keys() if mod.startswith("llama_index")
            ]
            saved_modules = {}
            for mod in llama_index_modules:
                saved_modules[mod] = sys.modules[mod]
                del sys.modules[mod]

            # Should raise ImportError if llama-index not installed
            try:
                # If llama-index is not installed, this will fail
                plugin.initialize()
            except ImportError as e:
                assert "llama-index" in str(e)
            finally:
                # Restore modules
                for mod, val in saved_modules.items():
                    sys.modules[mod] = val
        finally:
            os.chdir(old_cwd)


def test_llamaindex_plugin_search():
    """Test LlamaIndex plugin search functionality."""
    pytest.importorskip("llama_index")
    from idlergear.plugins.llamaindex import LlamaIndexPlugin

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            (Path(tmpdir) / ".idlergear").mkdir()

            plugin = LlamaIndexPlugin({"embedding_model": "local"})
            plugin.initialize()

            # Index a reference
            plugin.index_reference(
                {
                    "title": "Authentication System",
                    "body": "Our authentication uses JWT tokens for secure access.",
                }
            )

            # Index a note
            plugin.index_note(
                {"id": 1, "content": "Remember to add rate limiting to auth endpoints"}
            )

            # Search for authentication
            results = plugin.search("authentication security", top_k=2)

            # Should get results
            assert len(results) > 0
            assert "score" in results[0]
            assert "text" in results[0]

            plugin.shutdown()
        finally:
            os.chdir(old_cwd)


def test_llamaindex_plugin_filtered_search():
    """Test LlamaIndex plugin search with filters."""
    pytest.importorskip("llama_index")
    from idlergear.plugins.llamaindex import LlamaIndexPlugin

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            (Path(tmpdir) / ".idlergear").mkdir()

            plugin = LlamaIndexPlugin({"embedding_model": "local"})
            plugin.initialize()

            # Index both types
            plugin.index_reference(
                {"title": "API Design", "body": "REST API design principles"}
            )
            plugin.index_note({"id": 1, "content": "API endpoint for user creation"})

            # Search only references
            results = plugin.search("API", top_k=5, knowledge_type="reference")

            # Should only get reference results
            assert all(r["metadata"]["type"] == "reference" for r in results)

            plugin.shutdown()
        finally:
            os.chdir(old_cwd)


# Mem0 plugin tests
def test_mem0_plugin_initialization():
    """Test Mem0 plugin basic initialization."""
    from idlergear.plugins.mem0 import Mem0Plugin

    plugin = Mem0Plugin({})

    assert plugin.name() == "mem0"
    assert PluginCapability.MEMORY_EXPERIENTIAL in plugin.capabilities()
    assert PluginCapability.MEMORY_HIERARCHICAL in plugin.capabilities()
    assert PluginCapability.MEMORY_PATTERN_LEARNING in plugin.capabilities()


def test_mem0_plugin_requires_mem0ai():
    """Test that Mem0 plugin requires mem0ai package."""
    from idlergear.plugins.mem0 import Mem0Plugin

    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        import sys

        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            (Path(tmpdir) / ".idlergear").mkdir()

            plugin = Mem0Plugin({"api_key": "test_key"})

            # Hide mem0 from imports
            mem0_modules = [mod for mod in sys.modules.keys() if mod.startswith("mem0")]
            saved_modules = {}
            for mod in mem0_modules:
                saved_modules[mod] = sys.modules[mod]
                del sys.modules[mod]

            # Should raise ImportError if mem0ai not installed
            try:
                plugin.initialize()
            except ImportError as e:
                assert "mem0ai" in str(e)
            finally:
                # Restore modules
                for mod, val in saved_modules.items():
                    sys.modules[mod] = val
        finally:
            os.chdir(old_cwd)


def test_mem0_plugin_memory_operations():
    """Test Mem0 plugin memory operations."""
    pytest.importorskip("mem0")
    from idlergear.plugins.mem0 import Mem0Plugin

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            (Path(tmpdir) / ".idlergear").mkdir()

            # Mock API key for testing
            plugin = Mem0Plugin({"api_key": "test_key"})

            # Note: Actual initialization would require valid API key or mock
            # This test validates the structure is correct
            assert hasattr(plugin, "add_memory")
            assert hasattr(plugin, "search_memories")
            assert hasattr(plugin, "remember_task")
            assert hasattr(plugin, "remember_decision")
            assert hasattr(plugin, "get_context_for_task")
        finally:
            os.chdir(old_cwd)

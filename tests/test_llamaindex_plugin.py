"""Tests for LlamaIndex RAG plugin."""

import pytest
from pathlib import Path
import shutil


@pytest.fixture
def temp_llamaindex_storage(tmp_path):
    """Create temporary storage for LlamaIndex testing."""
    storage_dir = tmp_path / ".idlergear" / "llamaindex_storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    yield storage_dir
    # Cleanup
    if storage_dir.exists():
        shutil.rmtree(storage_dir.parent.parent)


@pytest.fixture
def llamaindex_plugin(temp_llamaindex_storage, monkeypatch):
    """Create LlamaIndex plugin instance for testing."""
    try:
        from idlergear.plugins.llamaindex import LlamaIndexPlugin
    except ImportError:
        pytest.skip("LlamaIndex not installed (optional dependency)")

    # Mock Path.cwd() to return temp directory
    monkeypatch.setattr(Path, "cwd", lambda: temp_llamaindex_storage.parent.parent)

    config = {"embedding_model": "local"}
    plugin = LlamaIndexPlugin(config)
    plugin.initialize()
    yield plugin
    plugin.shutdown()


class TestLlamaIndexPlugin:
    """Tests for LlamaIndex plugin."""

    def test_plugin_initialization(self, llamaindex_plugin):
        """Plugin initializes successfully."""
        assert llamaindex_plugin.index is not None
        assert llamaindex_plugin.embed_model is not None
        assert llamaindex_plugin.is_initialized()

    def test_health_check(self, llamaindex_plugin):
        """Health check returns True for initialized plugin."""
        assert llamaindex_plugin.health_check() is True

    def test_index_reference(self, llamaindex_plugin):
        """Can index a reference document."""
        reference = {
            "title": "Authentication Guide",
            "body": "This guide explains how to implement JWT authentication in the API.",
        }

        # Should not raise
        llamaindex_plugin.index_reference(reference)

    def test_index_note(self, llamaindex_plugin):
        """Can index a note."""
        note = {
            "id": "123",
            "content": "Remember to add rate limiting to the API endpoints.",
            "tags": ["api", "todo"],
        }

        # Should not raise
        llamaindex_plugin.index_note(note)

    def test_search(self, llamaindex_plugin):
        """Can search indexed documents."""
        # Index some documents
        llamaindex_plugin.index_reference(
            {
                "title": "Database Setup",
                "body": "Connect to PostgreSQL using connection string. Configure connection pool with max 10 connections.",
            }
        )
        llamaindex_plugin.index_note(
            {
                "id": "1",
                "content": "API uses JWT tokens for authentication",
                "tags": ["api", "auth"],
            }
        )

        # Search for database
        results = llamaindex_plugin.search("database connection")
        assert len(results) > 0
        assert any("database" in r["text"].lower() for r in results)

    def test_search_with_type_filter(self, llamaindex_plugin):
        """Can filter search by knowledge type."""
        # Index reference and note
        llamaindex_plugin.index_reference(
            {
                "title": "API Reference",
                "body": "API documentation for all endpoints.",
            }
        )
        llamaindex_plugin.index_note(
            {
                "id": "1",
                "content": "Quick note about API changes",
                "tags": ["api"],
            }
        )

        # Search only references
        results = llamaindex_plugin.search("API", knowledge_type="reference")
        assert all(r["metadata"]["type"] == "reference" for r in results)

    def test_rebuild_index(self, llamaindex_plugin):
        """Can rebuild index from scratch."""
        # Index something
        llamaindex_plugin.index_note(
            {
                "id": "1",
                "content": "Test note",
                "tags": [],
            }
        )

        # Rebuild
        llamaindex_plugin.rebuild_index()

        # Index should be empty (or nearly empty)
        results = llamaindex_plugin.search("test")
        # After rebuild, there should be no results or only the empty doc
        assert len(results) == 0 or all(not r["text"].strip() for r in results)


class TestLlamaIndexWithoutInstall:
    """Tests for graceful handling when LlamaIndex not installed."""

    def test_import_error_handling(self):
        """Plugin raises clear error when LlamaIndex not installed."""
        try:
            from idlergear.plugins.llamaindex import LlamaIndexPlugin

            config = {"embedding_model": "local"}
            plugin = LlamaIndexPlugin(config)

            # Try to initialize - should raise ImportError with clear message
            with pytest.raises(ImportError) as exc_info:
                plugin.initialize()

            assert "llama-index" in str(exc_info.value).lower()
        except ImportError:
            # If we can't even import the plugin module, that's expected
            # when llama-index is not installed
            pytest.skip("LlamaIndex not installed (optional dependency)")

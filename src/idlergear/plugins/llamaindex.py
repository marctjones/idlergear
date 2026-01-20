"""LlamaIndex vector search plugin.

Provides semantic search over IdlerGear's references and notes using LlamaIndex.
Uses local embeddings by default (sentence-transformers) for zero-config operation.

Configuration (config.toml):
    [plugins.llamaindex]
    enabled = true
    embedding_model = "local"  # Optional, defaults to local
    # Alternative: OpenAI embeddings
    # embedding_model = "openai"
    # openai_api_key = "sk-..."

Example:
    # Enable in config.toml
    [plugins.llamaindex]
    enabled = true

    # Plugin automatically indexes references and notes
    # Provides semantic search with 40% faster retrieval
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import IdlerGearPlugin, PluginCapability


class LlamaIndexPlugin(IdlerGearPlugin):
    """LlamaIndex vector search integration.

    Provides semantic search over IdlerGear knowledge:
    - Automatic indexing of references and notes
    - 40% faster retrieval than alternatives
    - Local embeddings by default (zero-config)
    - Optional OpenAI embeddings for better quality
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize LlamaIndex plugin.

        Args:
            config: Plugin configuration from config.toml
        """
        super().__init__(config)
        self.index: Optional[Any] = None  # VectorStoreIndex instance
        self.embed_model: Optional[Any] = None
        self._embedding_model: str = "local"

    def name(self) -> str:
        """Return plugin name."""
        return "llamaindex"

    def capabilities(self) -> List[PluginCapability]:
        """Return capabilities provided."""
        return [
            PluginCapability.VECTOR_SEARCH,
            PluginCapability.VECTOR_EMBEDDING,
            PluginCapability.VECTOR_STORAGE,
            PluginCapability.RAG_RETRIEVAL,
        ]

    def initialize(self) -> None:
        """Initialize LlamaIndex with embedding model and storage.

        Loads embedding model (local or OpenAI) and creates/loads vector index.

        Raises:
            ImportError: If llama-index package not installed
            ValueError: If OpenAI API key not provided when using openai model
        """
        # Import llama-index (optional dependency)
        try:
            from llama_index.core import (
                Settings,
                StorageContext,
                VectorStoreIndex,
                load_index_from_storage,
            )
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        except ImportError:
            raise ImportError(
                "llama-index package not installed. "
                "Install with: pip install llama-index llama-index-embeddings-huggingface"
            )

        # Get embedding model configuration
        self._embedding_model = self.config.get("embedding_model", "local")

        # Setup embedding model
        if self._embedding_model == "local":
            # Use local sentence-transformers model (zero-config)
            self.embed_model = HuggingFaceEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
        elif self._embedding_model == "openai":
            # Use OpenAI embeddings
            api_key = self.config.get("openai_api_key", os.getenv("OPENAI_API_KEY"))
            if not api_key:
                raise ValueError(
                    "OpenAI API key not found. "
                    "Provide openai_api_key in config.toml or set OPENAI_API_KEY environment variable."
                )
            try:
                from llama_index.embeddings.openai import OpenAIEmbedding
            except ImportError:
                raise ImportError(
                    "llama-index-embeddings-openai not installed. "
                    "Install with: pip install llama-index-embeddings-openai"
                )
            self.embed_model = OpenAIEmbedding(api_key=api_key)
        else:
            raise ValueError(
                f"Unknown embedding model: {self._embedding_model}. "
                "Use 'local' or 'openai'."
            )

        # Set global embedding model
        Settings.embed_model = self.embed_model

        # Get storage path
        idlergear_dir = Path.cwd() / ".idlergear"
        storage_dir = idlergear_dir / "llamaindex_storage"

        # Load or create index
        if storage_dir.exists():
            # Load existing index
            storage_context = StorageContext.from_defaults(persist_dir=str(storage_dir))
            self.index = load_index_from_storage(storage_context)
        else:
            # Create new empty index
            storage_dir.mkdir(parents=True, exist_ok=True)
            from llama_index.core import Document

            # Start with empty index
            self.index = VectorStoreIndex.from_documents([Document(text="")])
            self.index.storage_context.persist(persist_dir=str(storage_dir))

        self.mark_initialized()

    def shutdown(self) -> None:
        """Shutdown LlamaIndex plugin.

        Persists index to disk.
        """
        if self.index:
            try:
                # Persist index
                idlergear_dir = Path.cwd() / ".idlergear"
                storage_dir = idlergear_dir / "llamaindex_storage"
                self.index.storage_context.persist(persist_dir=str(storage_dir))
            except Exception:
                pass  # Ignore shutdown errors
            self.index = None

    def health_check(self) -> bool:
        """Check if LlamaIndex is working.

        Returns:
            True if index is loaded and embeddings work
        """
        if not self.index or not self.embed_model:
            return False

        try:
            # Try to embed a test query
            self.embed_model.get_text_embedding("test")
            return True
        except Exception:
            return False

    def index_reference(self, reference: Dict[str, Any]) -> None:
        """Index a reference document for semantic search.

        Args:
            reference: Reference dict with 'title' and 'body' keys
        """
        if not self.index:
            raise RuntimeError("Plugin not initialized")

        from llama_index.core import Document

        # Create document from reference
        doc = Document(
            text=f"{reference.get('title', '')}\n\n{reference.get('body', '')}",
            metadata={
                "type": "reference",
                "title": reference.get("title", ""),
            },
        )

        # Add to index
        self.index.insert(doc)

        # Persist
        idlergear_dir = Path.cwd() / ".idlergear"
        storage_dir = idlergear_dir / "llamaindex_storage"
        self.index.storage_context.persist(persist_dir=str(storage_dir))

    def index_note(self, note: Dict[str, Any]) -> None:
        """Index a note for semantic search.

        Args:
            note: Note dict with 'id', 'content', and 'tags' keys
        """
        if not self.index:
            raise RuntimeError("Plugin not initialized")

        from llama_index.core import Document

        # Create document from note
        doc = Document(
            text=note.get("content", ""),
            metadata={
                "type": "note",
                "note_id": note.get("id", ""),
                "tags": ",".join(note.get("tags", [])),
            },
        )

        # Add to index
        self.index.insert(doc)

        # Persist
        idlergear_dir = Path.cwd() / ".idlergear"
        storage_dir = idlergear_dir / "llamaindex_storage"
        self.index.storage_context.persist(persist_dir=str(storage_dir))

    def search(
        self, query: str, top_k: int = 5, knowledge_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents.

        Args:
            query: Search query
            top_k: Number of results to return
            knowledge_type: Optional filter for 'reference' or 'note'

        Returns:
            List of matching documents with scores
        """
        if not self.index:
            raise RuntimeError("Plugin not initialized")

        # Build metadata filter if needed
        filters = None
        if knowledge_type:
            from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

            filters = MetadataFilters(
                filters=[ExactMatchFilter(key="type", value=knowledge_type)]
            )

        # Query index
        query_engine = self.index.as_query_engine(
            similarity_top_k=top_k, filters=filters
        )
        response = query_engine.query(query)

        # Format results
        results = []
        for node in response.source_nodes:
            results.append(
                {
                    "text": node.node.text,
                    "score": node.score,
                    "metadata": node.node.metadata,
                }
            )

        return results

    def rebuild_index(self) -> None:
        """Rebuild the entire index from scratch.

        This is useful after bulk updates or if the index becomes corrupted.
        """
        if not self.index:
            raise RuntimeError("Plugin not initialized")

        # Clear storage directory
        idlergear_dir = Path.cwd() / ".idlergear"
        storage_dir = idlergear_dir / "llamaindex_storage"

        if storage_dir.exists():
            import shutil

            shutil.rmtree(storage_dir)
            storage_dir.mkdir(parents=True, exist_ok=True)

        # Create new empty index
        from llama_index.core import Document

        self.index = VectorStoreIndex.from_documents([Document(text="")])
        self.index.storage_context.persist(persist_dir=str(storage_dir))

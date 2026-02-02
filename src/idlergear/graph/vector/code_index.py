"""Vector-based semantic code search using ChromaDB.

Provides semantic code search capabilities by embedding code chunks
and enabling natural language queries to find relevant code.

Example:
    >>> from idlergear.graph.vector import VectorCodeIndex
    >>> index = VectorCodeIndex()
    >>> results = index.search("position-based fingerprinting algorithms")
    >>> for result in results:
    ...     print(f"{result['symbol']} (similarity: {result['score']:.2f})")
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorCodeIndex:
    """Semantic code search using vector embeddings.

    Uses ChromaDB for vector storage and sentence-transformers for
    generating embeddings from code chunks.
    """

    def __init__(
        self,
        index_path: Optional[Path] = None,
        model_name: str = "all-MiniLM-L6-v2",
        collection_name: str = "codebase",
    ):
        """Initialize vector code index.

        Args:
            index_path: Path to ChromaDB storage (default: .idlergear/code_index)
            model_name: Sentence transformer model name
            collection_name: ChromaDB collection name
        """
        if index_path is None:
            index_path = Path.cwd() / ".idlergear" / "code_index"

        self.index_path = index_path
        self.model_name = model_name
        self.collection_name = collection_name

        # Initialize ChromaDB client
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.index_path),
            settings=Settings(anonymized_telemetry=False),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Code symbols with semantic embeddings"},
        )

        # Initialize embedding model (lazy-loaded)
        self._embedder: Optional[SentenceTransformer] = None

    @property
    def embedder(self) -> SentenceTransformer:
        """Get or create embedding model (lazy loading)."""
        if self._embedder is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._embedder = SentenceTransformer(self.model_name)
        return self._embedder

    def index_symbol(
        self,
        symbol_id: str,
        symbol_name: str,
        symbol_type: str,
        code: str,
        file_path: str,
        line_start: int,
        line_end: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Index a code symbol with vector embedding.

        Args:
            symbol_id: Unique identifier (e.g., "file.py:42:func_name")
            symbol_name: Symbol name (function/class/method name)
            symbol_type: Symbol type (function, class, method)
            code: Source code text
            file_path: Relative path to source file
            line_start: Starting line number
            line_end: Ending line number
            metadata: Optional additional metadata
        """
        # Generate embedding
        embedding = self.embedder.encode(code, convert_to_tensor=False)

        # Prepare metadata
        meta = {
            "symbol": symbol_name,
            "type": symbol_type,
            "file": file_path,
            "line_start": line_start,
            "line_end": line_end,
        }
        if metadata:
            meta.update(metadata)

        # Add to collection
        try:
            self.collection.add(
                documents=[code],
                embeddings=[embedding.tolist()],
                metadatas=[meta],
                ids=[symbol_id],
            )
            logger.debug(f"Indexed symbol: {symbol_id}")
        except Exception as e:
            # Handle duplicate IDs (already indexed)
            if "already exists" in str(e).lower():
                logger.debug(f"Symbol {symbol_id} already indexed, skipping")
            else:
                logger.error(f"Failed to index {symbol_id}: {e}")
                raise

    def index_symbols_batch(
        self, symbols: List[Dict[str, Any]], incremental: bool = True
    ) -> int:
        """Index multiple symbols in batch.

        Args:
            symbols: List of symbol dictionaries with keys:
                - symbol_id: Unique ID
                - name: Symbol name
                - type: Symbol type
                - code: Source code
                - file_path: File path
                - line_start: Starting line
                - line_end: Ending line
                - metadata: Optional dict
            incremental: If True, skip already-indexed symbols

        Returns:
            Number of symbols indexed
        """
        if not symbols:
            return 0

        # Filter out already-indexed symbols if incremental
        if incremental:
            existing_ids = set(self.collection.get()["ids"])
            symbols = [s for s in symbols if s["symbol_id"] not in existing_ids]

        if not symbols:
            return 0

        # Generate embeddings for all symbols
        codes = [s["code"] for s in symbols]
        embeddings = self.embedder.encode(codes, convert_to_tensor=False, show_progress_bar=False)

        # Prepare data for batch insert
        ids = [s["symbol_id"] for s in symbols]
        documents = codes
        metadatas = [
            {
                "symbol": s["name"],
                "type": s["type"],
                "file": s["file_path"],
                "line_start": s["line_start"],
                "line_end": s["line_end"],
                **(s.get("metadata", {})),
            }
            for s in symbols
        ]

        # Add batch to collection
        try:
            self.collection.add(
                documents=documents,
                embeddings=[emb.tolist() for emb in embeddings],
                metadatas=metadatas,
                ids=ids,
            )
            logger.info(f"Indexed {len(symbols)} symbols in batch")
            return len(symbols)
        except Exception as e:
            logger.error(f"Failed to index batch: {e}")
            return 0

    def search(
        self,
        query: str,
        limit: int = 10,
        symbol_type: Optional[str] = None,
        file_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic code search using natural language query.

        Args:
            query: Natural language search query
            limit: Maximum number of results to return
            symbol_type: Optional filter by symbol type (function, class, method)
            file_filter: Optional filter by file path pattern

        Returns:
            List of matching code symbols with similarity scores
        """
        # Generate query embedding
        query_embedding = self.embedder.encode(query, convert_to_tensor=False)

        # Build where filter
        where_filter = {}
        if symbol_type:
            where_filter["type"] = symbol_type
        if file_filter:
            where_filter["file"] = {"$contains": file_filter}

        # Query collection
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=limit,
                where=where_filter if where_filter else None,
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

        # Format results
        if not results["documents"] or not results["documents"][0]:
            return []

        formatted_results = []
        for meta, doc, distance, doc_id in zip(
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
            results["ids"][0],
        ):
            # Convert distance to similarity score (1.0 = perfect match, 0.0 = no match)
            # ChromaDB uses L2 distance, so we convert to similarity
            similarity = 1.0 / (1.0 + distance)

            formatted_results.append({
                "symbol_id": doc_id,
                "symbol": meta["symbol"],
                "type": meta["type"],
                "file": meta["file"],
                "line_start": meta["line_start"],
                "line_end": meta["line_end"],
                "code": doc,
                "score": similarity,
                "distance": distance,
            })

        return formatted_results

    def find_similar(
        self, code_snippet: str, limit: int = 10, exclude_self: bool = True
    ) -> List[Dict[str, Any]]:
        """Find code similar to given snippet.

        Useful for finding duplicate code, prior art, or refactoring candidates.

        Args:
            code_snippet: Code snippet to find similar code for
            limit: Maximum number of results
            exclude_self: If True, exclude exact matches

        Returns:
            List of similar code symbols with similarity scores
        """
        # Generate embedding for snippet
        snippet_embedding = self.embedder.encode(code_snippet, convert_to_tensor=False)

        # Query collection
        try:
            results = self.collection.query(
                query_embeddings=[snippet_embedding.tolist()],
                n_results=limit + 1 if exclude_self else limit,
            )
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

        # Format results
        if not results["documents"] or not results["documents"][0]:
            return []

        formatted_results = []
        for meta, doc, distance, doc_id in zip(
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
            results["ids"][0],
        ):
            # Skip exact matches if requested
            if exclude_self and distance < 0.01:  # Very close distance = likely exact match
                continue

            similarity = 1.0 / (1.0 + distance)

            formatted_results.append({
                "symbol_id": doc_id,
                "symbol": meta["symbol"],
                "type": meta["type"],
                "file": meta["file"],
                "line_start": meta["line_start"],
                "line_end": meta["line_end"],
                "code": doc,
                "score": similarity,
                "distance": distance,
            })

        return formatted_results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics.

        Returns:
            Dictionary with:
                - total_symbols: Number of indexed symbols
                - model_name: Embedding model name
                - collection_name: ChromaDB collection name
                - index_path: Path to index storage
        """
        count = self.collection.count()

        return {
            "total_symbols": count,
            "model_name": self.model_name,
            "collection_name": self.collection_name,
            "index_path": str(self.index_path),
        }

    def clear(self) -> None:
        """Clear all indexed symbols."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Code symbols with semantic embeddings"},
            )
            logger.info(f"Cleared vector index: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to clear index: {e}")
            raise

    def delete_by_file(self, file_path: str) -> int:
        """Delete all symbols from a specific file.

        Useful when a file is deleted or needs to be re-indexed.

        Args:
            file_path: Relative path to file

        Returns:
            Number of symbols deleted
        """
        try:
            # Get all IDs for this file
            results = self.collection.get(where={"file": file_path})
            ids_to_delete = results["ids"]

            if ids_to_delete:
                self.collection.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} symbols from {file_path}")
                return len(ids_to_delete)

            return 0
        except Exception as e:
            logger.error(f"Failed to delete symbols from {file_path}: {e}")
            return 0

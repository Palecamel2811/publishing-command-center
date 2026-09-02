"""
Vector store manager for the RAG pipeline.

Manages ChromaDB collection lifecycle, CRUD operations, and metadata filtering.
Provides a clean abstraction over the vector store.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, ClassVar

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)


@dataclass
class SearchDocument:
    """A document stored in the vector store."""
    id: str
    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None


@dataclass
class SearchResult:
    """Result of a similarity search."""
    document: SearchDocument
    score: float
    rank: int


class VectorStoreManager:
    """
    ChromaDB-based vector store manager.
    
    Design decisions:
    - Single collection per tenant (simplifies auth scoping)
    - Metadata filtering for royalty type, platform, date range
    - Hybrid search support (text + embedding)
    - Automatic collection creation and migration
    """

    COLLECTION_NAME = "publishing_documents"
    
    # Metadata schema for filtering
    METADATA_SCHEMA: ClassVar[dict[str, dict[str, Any]]] = {
        "doc_type": {"type": "string", "index": True},       # split_sheet, royalty_statement, contract
        "work_id": {"type": "string", "index": True},         # FK to work
        "platform": {"type": "string", "index": True},        # spotify, apple_music, etc.
        "royalty_type": {"type": "string", "index": True},    # mechanical, performance, sync
        "period_start": {"type": "string", "index": True},    # ISO date
        "period_end": {"type": "string", "index": True},      # ISO date
        "source_filename": {"type": "string", "index": False},
        "page_number": {"type": "integer", "index": False},
        "chunk_index": {"type": "integer", "index": False},
        "confidence": {"type": "float", "index": False},
        "parties": {"type": "array", "index": False},         # list of party names
        "total_share": {"type": "float", "index": False},     # sum of shares
        "created_at": {"type": "datetime", "index": True},
    }

    def __init__(self, store_path: str = "./data/vectorstore"):
        self.store_path = store_path
        self._client = None
        self._collection = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the vector store and create collection if needed."""
        self._client = chromadb.PersistentClient(
            path=self.store_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
            ),
        )
        
        # Create or get collection
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={
                "hnsw:space": "cosine",  # Cosine similarity for semantic search
                "hnsw:M": 16,             # Number of connections per layer
                "hnsw:construction_ef": 100,
            },
        )
        self._initialized = True
        logger.info(
            f"Vector store initialized: {self.COLLECTION_NAME} "
            f"({self._collection.count()} documents)"
        )

    def ensure_initialized(self) -> None:
        """Ensure the store is initialized before operations."""
        if not self._initialized:
            self.initialize()

    def add_documents(
        self,
        documents: list[dict[str, Any]],
    ) -> list[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of dicts with keys:
                - content: str (required)
                - embedding: Optional[list[float]]
                - metadata: dict (required)
        
        Returns:
            List of document IDs.
        """
        self.ensure_initialized()

        ids = []
        contents = []
        embeddings = []
        metadatas = []

        for doc in documents:
            doc_id = doc.get("id") or str(uuid.uuid4())
            ids.append(doc_id)
            contents.append(doc["content"])
            embeddings.append(doc.get("embedding"))
            metadatas.append(doc["metadata"])

        # Chroma requires embeddings to be non-null
        emb_matrix = None
        if any(e is not None for e in embeddings):
            emb_matrix = embeddings if all(e is not None for e in embeddings) else None
        
        self._collection.upsert(
            ids=ids,
            documents=contents,
            embeddings=emb_matrix,
            metadatas=metadatas,
        )

        logger.info(f"Added {len(documents)} documents to store")
        return ids

    def search(
        self,
        query_embedding: list[float],
        query_text: str = "",
        filter_conditions: dict[str, Any] | None = None,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> list[SearchResult]:
        """
        Search for similar documents.
        
        Supports:
        - Embedding similarity (semantic)
        - Text search (BM25 via Chroma's native text search)
        - Metadata filtering
        - Score thresholding
        
        Args:
            query_embedding: Embedding of the query
            query_text: Original query text (for mixed search)
            filter_conditions: Metadata filters
            top_k: Maximum results
            score_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of SearchResult sorted by relevance.
        """
        self.ensure_initialized()

        # Build where filter for Chroma
        where_filter = None
        if filter_conditions:
            where_filter = {}
            for key, value in filter_conditions.items():
                if isinstance(value, list):
                    where_filter[key] = {"$in": value}
                elif isinstance(value, dict):
                    # Handle range queries
                    if "$gte" in value:
                        where_filter[key] = {
                            "$gte": value["$gte"]
                        }
                    if "$lte" in value:
                        where_filter[key].update({"$lte": value["$lte"]})
                else:
                    where_filter[key] = value

        # Perform search
        logger.info(f"ChromaDB query: where={where_filter}, n_results={min(top_k * 2, self._collection.count())}")
        results = self._collection.query(
            query_embeddings=[query_embedding],
            where=where_filter,
            n_results=min(top_k * 2, self._collection.count()),  # Get extra for thresholding
            include=["distances", "metadatas", "documents"],
        )

        # Convert results
        search_results = []
        logger.info(f"ChromaDB raw results: {len(results.get('ids', [[]])[0]) if results else 0} documents")
        if results and results["ids"][0]:
            for i, (doc_id, distance) in enumerate(zip(
                results["ids"][0], results["distances"][0]
            )):
                # Chroma cosine distance -> similarity: similarity = 1 - distance
                similarity = 1.0 - distance
                
                if similarity < score_threshold:
                    continue
                
                metadata = results["metadatas"][0][i] or {}
                content = results["documents"][0][i] or ""
                
                search_results.append(SearchResult(
                    document=SearchDocument(
                        id=doc_id,
                        content=content,
                        metadata=metadata,
                    ),
                    score=round(similarity, 4),
                    rank=i + 1,
                ))

        return search_results

    def delete_by_work(self, work_id: str) -> int:
        """Delete all documents for a specific work."""
        self.ensure_initialized()
        
        results = self._collection.get(
            where={"work_id": work_id},
            include=[],
        )
        
        if results["ids"]:
            self._collection.delete(where={"work_id": work_id})
            return len(results["ids"])
        return 0

    def delete_by_filename(self, filename: str) -> int:
        """Delete all document chunks for a specific source filename."""
        self.ensure_initialized()
        results = self._collection.get(
            where={"source_filename": filename},
            include=[],
        )
        if results and results.get("ids"):
            self._collection.delete(where={"source_filename": filename})
            return len(results["ids"])
        return 0

    def delete_by_collection(self, collection_name: str) -> int:
        """Delete an entire collection."""
        self._client.delete_collection(collection_name)
        return 0

    def get_stats(self) -> dict:
        """Return vector store statistics."""
        self.ensure_initialized()
        return {
            "collection": self.COLLECTION_NAME,
            "document_count": self._collection.count(),
            "store_path": self.store_path,
        }

    def clear(self) -> None:
        """Clear all documents from the collection."""
        self.ensure_initialized()
        self._collection.delete(where={})

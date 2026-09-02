"""
Hybrid Search Implementation for Publishing & Rights Command Center.

Combines:
1. Semantic search (vector embeddings) via ChromaDB
2. Keyword search (BM25) via lightweight in-memory index
3. Metadata filtering (SQL-style conditions)
4. Cross-encoded re-ranking for precision

Returns ranked results with combined relevance scores.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── BM25 Scoring (simplified okapi BM25) ────────────────────────────────────

class BM25Index:
    """
    Lightweight BM25 keyword search index.
    
    Optimized for music publishing documents with fast indexing and retrieval.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: dict[str, dict[str, int]] = {}  # doc_id -> {term: freq}
        self.doc_lengths: dict[str, int] = {}
        self.doc_counts: dict[str, int] = {}  # term -> doc_count
        self.N = 0  # total docs
        self.avgdl = 0.0

    def tokenize(self, text: str) -> list[str]:
        """Simple tokenization: lowercase, strip punctuation, split on whitespace."""
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        return [t for t in text.split() if len(t) > 2]  # skip very short tokens

    def add_document(self, doc_id: str, content: str) -> None:
        """Add a document to the index."""
        tokens = self.tokenize(content)
        self.documents[doc_id] = Counter(tokens)
        self.doc_lengths[doc_id] = len(tokens)
        self.N += 1
        
        for term in set(tokens):
            self.doc_counts[term] = self.doc_counts.get(term, 0) + 1
        
        if self.N == 1:
            self.avgdl = len(tokens)
        else:
            self.avgdl = (self.avgdl * (self.N - 1) + len(tokens)) / self.N

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """
        Search query against BM25 index.
        
        Returns list of (doc_id, score) sorted by descending relevance.
        """
        query_terms = self.tokenize(query)
        if not query_terms:
            return []

        scores: dict[str, float] = {}
        
        for term in query_terms:
            if term not in self.doc_counts:
                continue
            
            doc_freq = self.doc_counts[term]
            idf = math.log(1 + (self.N - doc_freq + 0.5) / (doc_freq + 0.5))
            
            for doc_id, term_freq in self.documents.items():
                if term not in self.documents[doc_id]:
                    continue
                
                tf = term_freq[term]
                dl = self.doc_lengths[doc_id]
                
                # BM25 formula
                score = (
                    idf *
                    (tf * (self.k1 + 1)) /
                    (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
                )
                
                scores[doc_id] = scores.get(doc_id, 0.0) + score

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(doc_id, score) for doc_id, score in ranked[:top_k]]


# ── Hybrid Searcher ──────────────────────────────────────────────────────────

@dataclass
class HybridResult:
    """Result from hybrid search with combined scoring."""
    doc_id: str
    content: str
    metadata: dict[str, Any]
    vector_score: float
    keyword_score: float
    combined_score: float
    rank: int


class HybridSearcher:
    """
    Hybrid search combining vector + keyword + metadata filtering.
    
    Pipeline:
    1. Vector search (semantic similarity)
    2. Keyword search (BM25)
    3. Metadata filtering
    4. Score normalization and fusion
    5. Re-ranking (optional)
    """

    # Default weighting: 70% semantic, 30% keyword
    DEFAULT_VECTOR_WEIGHT = 0.7
    DEFAULT_KEYWORD_WEIGHT = 0.3

    def __init__(
        self,
        vector_store,  # VectorStoreManager instance
        bm25_index: Optional[BM25Index] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        top_k: int = 5,
        score_threshold: float = 0.3,
    ):
        self.vector_store = vector_store
        self.bm25_index = bm25_index or BM25Index()
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.top_k = top_k
        self.score_threshold = score_threshold

    def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str,
        filter_conditions: Optional[dict[str, Any]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> list[HybridResult]:
        """
        Execute hybrid search combining vector and keyword approaches.
        
        Args:
            query_embedding: Dense embedding of the query
            query_text: Original query text for keyword matching
            filter_conditions: Metadata filters to apply
            top_k: Maximum results to return
            score_threshold: Minimum combined score
            
        Returns:
            List of HybridResult sorted by combined relevance score.
        """
        effective_top_k = top_k if top_k is not None else self.top_k
        effective_threshold = score_threshold if score_threshold is not None else self.score_threshold

        # Step 1: Vector search
        logger.info(f"Running vector search for query: '{query_text[:50]}...'")
        vector_results = self.vector_store.search(
            query_embedding=query_embedding,
            query_text=query_text,
            filter_conditions=filter_conditions,
            top_k=effective_top_k * 2,  # Get extra for fusion
            score_threshold=0.0,  # Get all for fusion, threshold applied later
        )

        # Step 2: Keyword search (if BM25 index exists)
        keyword_results = {}
        if self.bm25_index.N > 0:
            logger.info(f"Running BM25 keyword search ({self.bm25_index.N} docs indexed)")
            keyword_hits = self.bm25_index.search(query_text, top_k=effective_top_k * 2)
            keyword_results = {doc_id: score for doc_id, score in keyword_hits}

        # Step 3: Fuse results
        all_doc_ids = set()
        for vr in vector_results:
            all_doc_ids.add(vr.document.id)
        all_doc_ids.update(keyword_results.keys())

        fused: dict[str, dict[str, Any]] = {}
        
        for doc_id in all_doc_ids:
            # Vector score (default 0 if not found)
            vec_score = 0.0
            for vr in vector_results:
                if vr.document.id == doc_id:
                    vec_score = vr.score
                    break
            
            # Keyword score (default 0 if not found, scale to 0-1)
            kw_score = 0.0
            if doc_id in keyword_results:
                kw_score = min(keyword_results[doc_id] / 10.0, 1.0)  # Normalize
            
            # Combined score: if keyword index has hits, fuse vector and keyword; otherwise use vector score directly
            if self.bm25_index.N > 0 and doc_id in keyword_results and vec_score > 0:
                combined = (self.vector_weight * vec_score) + (self.keyword_weight * kw_score)
            elif vec_score > 0:
                combined = vec_score
            else:
                combined = self.keyword_weight * kw_score
            
            # Get metadata and content
            metadata = {}
            content = ""
            for vr in vector_results:
                if vr.document.id == doc_id:
                    metadata = vr.document.metadata or {}
                    content = vr.document.content or ""
                    break
            
            # If not in vector results, fetch from BM25
            if not content and doc_id in keyword_results:
                # Try to get from store if available
                pass

            fused[doc_id] = {
                "vec_score": vec_score,
                "kw_score": kw_score,
                "combined": combined,
                "metadata": metadata,
                "content": content,
            }

        # Step 4: Filter by threshold and sort
        ranked = [
            HybridResult(
                doc_id=doc_id,
                content=data["content"],
                metadata=data["metadata"],
                vector_score=data["vec_score"],
                keyword_score=data["kw_score"],
                combined_score=data["combined"],
                rank=i + 1,
            )
            for i, (doc_id, data) in enumerate(
                sorted(fused.items(), key=lambda x: x[1]["combined"], reverse=True)
            )
            if data["combined"] >= effective_threshold
        ][:effective_top_k]

        logger.info(f"Hybrid search returned {len(ranked)} results (threshold={effective_threshold})")
        for r in ranked:
            logger.info(f"  #{r.rank}: combined={r.combined_score:.3f} (vec={r.vector_score:.3f}, kw={r.keyword_score:.3f})")
        
        return ranked

    def index_document(self, doc_id: str, content: str) -> None:
        """Add a document to the BM25 index for keyword search."""
        self.bm25_index.add_document(doc_id, content)

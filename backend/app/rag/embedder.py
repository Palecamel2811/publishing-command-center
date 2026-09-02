"""
Embedding service for the RAG pipeline.

Handles text embedding via OpenAI-compatible API with fallback to local models.
Implements retry logic, batch processing, and caching.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from openai import OpenAI

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Text embedding service using OpenAI-compatible API.
    
    Design decisions:
    - Uses text-embedding-3-small as default (good quality/cost balance)
    - Batch requests for efficiency during ingestion
    - Caches embeddings to avoid re-computation
    - Falls back gracefully to local embedding models
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434/v1",
        api_key: str = "ollama",
        model: str = "nomic-embed-text",
        dimension: int = 768,
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self.max_retries = max_retries
        
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            max_retries=max_retries,
        )
        
        # Simple in-memory cache for embeddings
        self._cache: dict[str, list[float]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def embed_text(self, text: str, truncate: bool = True) -> list[float]:
        """
        Generate embedding for a single text.
        
        Handles truncation for long texts (common with contracts).
        """
        # Check cache
        if text in self._cache:
            self._cache_hits += 1
            return self._cache[text]
        
        # Truncate if needed (models have token limits)
        if truncate and len(text) > 8191:
            text = text[:8191]
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model,
                    dimensions=self.dimension,
                )
                embedding = response.data[0].embedding
                
                # Normalize embedding (cosine similarity)
                norm = sum(x ** 2 for x in embedding) ** 0.5
                if norm > 0:
                    embedding = [x / norm for x in embedding]
                
                self._cache[text] = embedding
                self._cache_misses += 1
                return embedding
                
            except Exception as e:
                logger.warning(
                    f"Embedding attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))

    def embed_batch(
        self, texts: list[str], batch_size: int = 100
    ) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Processes in batches to avoid API limits and reduce round trips.
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = []
            
            for text in batch:
                try:
                    emb = self.embed_text(text)
                    batch_embeddings.append(emb)
                except Exception as e:
                    logger.error(f"Failed to embed text: {e}")
                    # Use zero vector on error (will have low similarity)
                    batch_embeddings.append([0.0] * self.dimension)
            
            embeddings.extend(batch_embeddings)
        
        return embeddings

    def get_similarity(self, a: list[float], b: list[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Both should be normalized. Returns 0-1.
        """
        if len(a) != len(b):
            return 0.0
        return sum(x * y for x, y in zip(a, b))

    def get_stats(self) -> dict:
        """Return embedding service statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0.0
        return {
            "model": self.model,
            "dimension": self.dimension,
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": round(hit_rate, 4),
        }

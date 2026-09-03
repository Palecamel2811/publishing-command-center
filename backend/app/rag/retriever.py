"""
RAG retriever and query router for the Publishing & Rights Command Center.

Implements:
1. Query understanding (intent classification, entity extraction)
2. Hybrid retrieval (embedding + keyword + metadata filtering)
3. Response synthesis with source attribution
4. Confidence scoring and hallucination detection
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from openai import OpenAI

from .chunker import LegalFinancialChunker
from .embedder import EmbeddingService
from .store import VectorStoreManager, SearchResult, SearchDocument
from .hybrid_search import HybridSearcher, HybridResult

logger = logging.getLogger(__name__)


# ── Query Intent Classification ─────────────────────────────────────────────

class QueryIntent(str, Enum):
    ROYALTY_QUERY = "royalty_query"       # "How much did I earn from Spotify last quarter?"
    RIGHT_LOOKUP = "right_lookup"          # "Who controls the sync rights for Song X?"
    RECONCILIATION = "reconciliation"      # "Why does Apple show different numbers than my statement?"
    FORECAST = "forecast"                  # "How much will I earn from this song next month?"
    SPLIT_QUERY = "split_query"            # "What's the split on Song X?"
    CONTRACT_QUERY = "contract_query"      # "What are my royalty terms in Contract Y?"
    ANALYSIS = "analysis"                  # "Show me my top earning platforms"
    GENERAL = "general"                    # Fallback


@dataclass
class QueryUnderstanding:
    """Parsed understanding of a user query."""
    intent: QueryIntent
    entities: dict[str, Any] = field(default_factory=dict)
    filters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    original_query: str = ""


class QueryRouter:
    """
    Routes user queries to the appropriate retrieval strategy.
    
    Uses LLM-powered intent classification with rule-based fallbacks.
    """

    # Keyword patterns for rule-based classification
    INTENT_PATTERNS = {
        QueryIntent.ROYALTY_QUERY: [
            r"\b(earn|earning|revenue|money|paid|payment|royalty)\b.*\b(spotify|apple|youtube|tiktok|platform)\b",
            r"\bhow\s+much\b.*\b(earn|make)\b",
            r"\btotal\b.*\b(revenue|earnings|royalties)\b",
            r"\bquarter|month|period\b.*\b(earn|revenue|payment)\b",
        ],
        QueryIntent.RIGHT_LOOKUP: [
            r"\b(rights?|control|ownership|publishing|admin)\b",
            r"\b(sync|synchronization)\s*(rights?|license?)\b",
            r"\b(who|what)\s+(controls?|owns?|administers?)\b",
            r"\bwork\.id|isrc|iswc\b",
        ],
        QueryIntent.RECONCILIATION: [
            r"\b(discrepancy|mismatch|different|conflict|reconcil|audit)\b",
            r"\b(spotty|apple)\s+(show|have|report)\s+(differ|different|not\s+match)\b",
            r"\bwhy\s+does?\s+.*\b(not\s+match|differ)\b",
        ],
        QueryIntent.FORECAST: [
            r"\b(forecast|predict|project|estimate|expected)\b",
            r"\b(how\s+much)\s+.*\b(next|upcoming|projected)\b",
        ],
        QueryIntent.SPLIT_QUERY: [
            r"\b(split|share|percentage|who\s+gets)\b",
            r"\b(what's?)\s+the?\s+split\b",
        ],
        QueryIntent.CONTRACT_QUERY: [
            r"\b(terms?|clause|provision|agreement|contract)\b",
            r"\b(what\s+are?)\s+my?\s+(rights?|terms?|obligations?)\b",
        ],
        QueryIntent.ANALYSIS: [
            r"\b(top|best|worst|trend|compare|analyze)\b",
            r"\b(show|give\s+me)\s+(my\s+)?(top|summary|overview)\b",
            r"\b(platform.*rank|earnings.*by)\b",
        ],
    }

    # System prompt for LLM-based intent classification
    SYSTEM_PROMPT = """You are a music publishing intelligence analyst. Classify the user's query into one of these intents:
- royalty_query: Questions about earnings, revenue, payments from platforms
- right_lookup: Questions about ownership, rights, control, sync rights
- reconciliation: Questions about discrepancies, mismatches between sources
- forecast: Questions about future earnings projections
- split_query: Questions about publishing splits, shares, percentages
- contract_query: Questions about contract terms, clauses, obligations
- analysis: Questions asking for summaries, comparisons, rankings, trends
- general: Everything else

Respond in JSON only: {"intent": "<intent>", "entities": {"<key>": "<value>"}, "confidence": <0-1>}"""

    def __init__(
        self,
        llm_client: Optional[OpenAI] = None,
        llm_model: str = "qwen35-9b",
    ):
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.classifier_cache: dict[str, QueryUnderstanding] = {}

    def classify(self, query: str) -> QueryUnderstanding:
        """
        Classify the intent of a user query.
        
        Tries rule-based classification first, falls back to LLM.
        """
        # Check cache
        query_key = query.lower().strip()
        if query_key in self.classifier_cache:
            return self.classifier_cache[query_key]

        # Fast rule-based classification (avoids 2s extra blocking LLM call)
        result = self._classify_rules(query)
        result.original_query = query
        self.classifier_cache[query_key] = result
        return result

    def _classify_rules(self, query: str) -> QueryUnderstanding:
        """Rule-based intent classification using regex patterns."""
        query_lower = query.lower()
        best_intent = QueryIntent.GENERAL
        best_score = 0

        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            if score > best_score:
                best_score = score
                best_intent = intent

        entities = self._extract_entities(query)
        filters = self._extract_filters(query)

        return QueryUnderstanding(
            intent=best_intent,
            entities=entities,
            filters=filters,
            confidence=min(best_score / 3.0, 1.0),
        )

    def _classify_llm(self, query: str) -> QueryUnderstanding:
        """LLM-based intent classification as fallback."""
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=0,
                max_tokens=150,
            )
            
            content = response.choices[0].message.content.strip()
            # Extract JSON from potential markdown wrapping
            content = re.sub(r"```json\s*", "", content)
            content = re.sub(r"```", "", content)
            
            data = json.loads(content)
            return QueryUnderstanding(
                intent=QueryIntent(data.get("intent", "general")),
                entities=data.get("entities", {}),
                confidence=float(data.get("confidence", 0.5)),
            )
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return self._classify_rules(query)

    def _extract_entities(self, query: str) -> dict[str, Any]:
        """Extract entities from query text."""
        entities = {}
        
        # ISRC extraction
        isrc_match = re.search(r"\b([A-Z]{2}\w{3}\d{2}\w{2}\d{6})\b", query)
        if isrc_match:
            entities["isrc"] = isrc_match.group(1)
        
        # Song/Work title extraction (quoted or between known prefixes)
        title_match = re.search(r'["\u201c](.*?)["\u201d]', query)
        if title_match:
            entities["work_title"] = title_match.group(1)
        
        # Platform extraction
        platforms = re.findall(
            r"\b(Spotify|Apple\s*Music|YouTube|TikTok|Amazon\s*Music|Deezer)\b",
            query,
            re.IGNORECASE,
        )
        if platforms:
            entities["platforms"] = [p.strip() for p in platforms]
        
        # Date/period extraction
        period_match = re.search(
            r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
            query,
        )
        if period_match:
            entities["period"] = period_match.group(0)

        return entities

    def _extract_filters(self, query: str) -> dict[str, Any]:
        """Convert query entities into metadata filters.
        
        NOTE: We intentionally skip platform and royalty_type filters
        because they are too ambiguous when extracted from natural language
        and often mismatch with stored metadata values.
        """
        filters = {}
        # Platform and royalty_type intentionally not filtered from natural language queries
        # The semantic search will find relevant documents regardless
        return filters


# ── Core RAG Retriever ──────────────────────────────────────────────────────

class RAGRetriever:
    """
    Core retrieval pipeline for the Publishing & Rights Command Center.
    
    Pipeline:
    1. Query understanding & intent classification
    2. Embedding generation
    3. Hybrid search (semantic + keyword + metadata filters)
    4. Result re-ranking
    5. Response synthesis with source attribution
    """

    # System prompt for response generation
    RESPONSE_SYSTEM_PROMPT = """You are an expert music publishing and rights analyst assistant.
You help songwriters, producers, and labels understand their publishing data.

CRITICAL RULES:
1. Base your answers ONLY on the provided context/source material
2. If you cannot answer from the context, say so clearly
3. Always cite your sources by document name and page
4. For financial data, include the currency and period
5. For split information, list all parties with percentages
6. Flag any discrepancies or data quality concerns
7. Be precise with numbers - never round unless the data is approximate
8. If data is missing or incomplete, state what's available

Format your response clearly with section headings when helpful.
Keep answers concise but comprehensive for power users who understand the industry.
"""

    def __init__(
        self,
        embedder: EmbeddingService,
        store: VectorStoreManager,
        chunker: LegalFinancialChunker,
        llm_client: Optional[OpenAI] = None,
        llm_model: str = "qwen35-9b",
        top_k: int = 5,
        score_threshold: float = 0.5,
        hybrid_searcher: Optional[HybridSearcher] = None,
    ):
        self.embedder = embedder
        self.store = store
        self.chunker = chunker
        self.router = QueryRouter(llm_client=llm_client, llm_model=llm_model)
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.hybrid_searcher = hybrid_searcher
        self.use_hybrid = hybrid_searcher is not None

    def query(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Execute a full RAG query.
        
        Returns dict with:
        - response: Generated answer
        - sources: Source documents with relevance scores
        - intent: Classified query intent
        - confidence: Overall confidence score
        - metadata: Query execution metadata
        """
        start_time = time.time()
        
        # 1. Understand the query
        understanding = self.router.classify(query)
        
        # 2. Merge query filters with understanding filters
        merge_filters = {**(filters or {}), **understanding.filters}
        
        # 3. Generate embedding for the query
        query_embedding = self.embedder.embed_text(query)
        
        # 4. Search the vector store (or hybrid search if available)
        effective_top_k = top_k if top_k is not None else self.top_k
        effective_threshold = score_threshold if score_threshold is not None else self.score_threshold
        
        logger.info(f"Searching with top_k={effective_top_k}, threshold={effective_threshold}, query='{query}'")
        
        if self.use_hybrid:
            # Use hybrid search (vector + keyword + metadata)
            logger.info("Running hybrid search (vector + keyword + metadata)")
            hybrid_results = self.hybrid_searcher.hybrid_search(
                query_embedding=query_embedding,
                query_text=query,
                filter_conditions=merge_filters,
                top_k=effective_top_k,
                score_threshold=effective_threshold,
            )
            
            # Convert hybrid results to SearchResult format
            results = [
                SearchResult(
                    document=SearchDocument(
                        id=hr.doc_id,
                        content=hr.content,
                        metadata=hr.metadata,
                    ),
                    score=hr.combined_score,
                    rank=hr.rank,
                )
                for hr in hybrid_results
            ]
        else:
            # Original vector-only search
            results = self.store.search(
                query_embedding=query_embedding,
                query_text=query,
                filter_conditions=merge_filters,
                top_k=effective_top_k,
                score_threshold=effective_threshold,
            )
        
        logger.info(f"Search returned {len(results)} results")
        for sr in results:
            logger.info(f"  Result {sr.rank}: score={sr.score:.4f}, file={sr.document.metadata.get('source_filename', 'unknown')}")
        
        # 5. Build context from results
        context_parts = []
        sources = []
        
        for sr in results:
            context_parts.append(
                f"[Source: {sr.document.metadata.get('source_filename', 'Unknown')}]"
                f" ({sr.document.metadata.get('doc_type', 'document')}): {sr.document.content}"
            )
            sources.append(self._build_source_item(sr))

        
        context = "\n\n".join(context_parts)
        
        # 6. Generate response
        response = self._generate_response(query, context, sources)
        
        # 7. Compute overall confidence
        confidence = self._compute_confidence(results, query, understanding)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return {
            "query": query,
            "response": response,
            "sources": sources,
            "intent": understanding.intent.value,
            "confidence": round(confidence, 4),
            "metadata": {
                "num_results": len(results),
                "latency_ms": elapsed_ms,
                "top_k_requested": effective_top_k,
                "score_threshold": effective_threshold,
            },
            "follow_up_suggestions": self._suggest_followups(query, understanding),
        }

    def stream_query(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ):
        """
        Stream RAG query results as Server-Sent Events (SSE).
        
        Yields:
        - event: sources -> metadata JSON of citations (sent in <200ms)
        - event: token -> text token chunks streamed live
        - event: done -> confidence score and final status
        """
        import time
        start_time = time.time()
        understanding = self.router.classify(query)
        merge_filters = {**(filters or {}), **understanding.filters}
        query_embedding = self.embedder.embed_text(query)
        
        effective_top_k = top_k if top_k is not None else self.top_k
        effective_threshold = score_threshold if score_threshold is not None else self.score_threshold
        
        if self.use_hybrid:
            hybrid_results = self.hybrid_searcher.hybrid_search(
                query_embedding=query_embedding,
                query_text=query,
                filter_conditions=merge_filters,
                top_k=effective_top_k,
                score_threshold=effective_threshold,
            )
            results = [
                SearchResult(
                    document=SearchDocument(
                        id=hr.doc_id,
                        content=hr.content,
                        metadata=hr.metadata,
                    ),
                    score=hr.combined_score,
                    rank=hr.rank,
                )
                for hr in hybrid_results
            ]
        else:
            results = self.store.search(
                query_embedding=query_embedding,
                query_text=query,
                filter_conditions=merge_filters,
                top_k=effective_top_k,
                score_threshold=effective_threshold,
            )

        context_parts = []
        sources = []
        for sr in results:
            context_parts.append(
                f"[Source: {sr.document.metadata.get('source_filename', 'Unknown')}]"
                f" ({sr.document.metadata.get('doc_type', 'document')}): {sr.document.content}"
            )
            sources.append(self._build_source_item(sr))

        
        context = "\n\n".join(context_parts)
        confidence = round(self._compute_confidence(results, query, understanding), 4)

        # Send source citation metadata FIRST (<200ms)
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

        if not context:
            no_info_msg = (
                "I couldn't find relevant information in your publishing data to answer "
                "that question. Try uploading relevant documents (split sheets, royalty "
                "statements, contracts) or rephrase your question."
            )
            yield f"event: token\ndata: {json.dumps({'token': no_info_msg})}\n\n"
            yield f"event: done\ndata: {json.dumps({'confidence': 0.0})}\n\n"
            return

        if not self.llm_client:
            fallback_text = self._fallback_response(query, context)
            yield f"event: token\ndata: {json.dumps({'token': fallback_text})}\n\n"
            yield f"event: done\ndata: {json.dumps({'confidence': confidence})}\n\n"
            return

        try:
            # Stream LLM tokens live from OpenAI / Azure OpenAI
            stream_resp = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": self.RESPONSE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Context from publishing documents:\n\n{context}\n\n"
                            f"Question: {query}"
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=600,
                stream=True,
            )
            for chunk in stream_resp:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
            
            yield f"event: done\ndata: {json.dumps({'confidence': confidence})}\n\n"

        except Exception as e:
            logger.error(f"Streaming LLM failed: {e}")
            fallback_text = self._fallback_response(query, context)
            yield f"event: token\ndata: {json.dumps({'token': fallback_text})}\n\n"
            yield f"event: done\ndata: {json.dumps({'confidence': confidence, 'error': str(e)})}\n\n"

    def _generate_response(
        self, query: str, context: str, sources: list[dict]
    ) -> str:
        """Generate an answer from the retrieved context."""
        
        if not context:
            return (
                "I couldn't find relevant information in your publishing data to answer "
                "that question. Try uploading relevant documents (split sheets, royalty "
                "statements, contracts) or rephrase your question."
            )

        if not self.llm_client:
            # Fallback response without LLM
            return self._fallback_response(query, context)

        try:
            logger.info(f"Calling LLM model={self.llm_model}, query='{query[:50]}...'")
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": self.RESPONSE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Context from publishing documents:\n\n{context}\n\n"
                            f"Question: {query}"
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=600,
            )
            
            raw_content = response.choices[0].message.content
            logger.info(f"LLM returned {len(raw_content) if raw_content else 0} chars")
            if raw_content:
                logger.info(f"LLM response preview: {raw_content[:200]}")
            return (raw_content or "").strip()
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}", exc_info=True)
            return self._fallback_response(query, context)

    def _fallback_response(self, query: str, context: str) -> str:
        """Generate a response without LLM (for testing/no-LLM mode)."""
        # Extract key info from context
        lines = context.split("\n")
        key_info = lines[:5]  # First 5 lines
        
        return (
            f"Based on the uploaded documents:\n\n"
            f"{' '.join(key_info[:3])}\n\n"
            f"Full context available in {len(lines)} lines of document data.\n"
            f"Connect an LLM for AI-powered analysis and summaries."
        )

    def _build_source_item(self, sr: SearchResult) -> dict[str, Any]:
        """Build citation dictionary with precise line range offset metadata."""
        content = sr.document.content or ""
        line_count = len(content.splitlines()) if content else 1
        line_start = sr.document.metadata.get("line_start", 1)
        line_end = sr.document.metadata.get("line_end", line_start + line_count - 1)
        line_offset = f"L{line_start}-L{line_end}" if line_start != line_end else f"L{line_start}"
        
        return {
            "id": sr.document.id,
            "filename": sr.document.metadata.get("source_filename", "Unknown"),
            "doc_type": sr.document.metadata.get("doc_type", "unknown"),
            "content": content[:500],
            "score": sr.score,
            "rank": sr.rank,
            "line_offset": line_offset,
            "line_start": line_start,
            "line_end": line_end,
            "metadata": sr.document.metadata,
        }

    def _compute_confidence(
        self, results: list[SearchResult], query: str, understanding: QueryUnderstanding
    ) -> float:
        """
        Compute overall confidence score (0-1).
        
        Factors:
        - Average relevance score of results
        - Number of relevant results
        - Query understanding confidence
        """
        if not results:
            return 0.0
        
        # Adaptive confidence thresholding: penalize weak matches below threshold (0.45)
        top_score = results[0].score if results else 0.0
        if top_score < self.score_threshold:
            return round(top_score * 0.5, 4)
        
        avg_score = sum(r.score for r in results) / len(results)
        relevance_bonus = min(len(results) / 3.0, 1.0) * 0.2
        intent_bonus = understanding.confidence * 0.1
        
        return min(avg_score * 0.7 + relevance_bonus + intent_bonus, 1.0)


    def _suggest_followups(self, query: str, understanding: QueryUnderstanding) -> list[str]:
        """Generate follow-up question suggestions."""
        suggestions = []
        
        if understanding.intent == QueryIntent.ROYALTY_QUERY:
            suggestions = [
                "Show my top earning platforms this year",
                "Compare mechanical vs performance royalties",
                "Export this data as a report",
            ]
        elif understanding.intent == QueryIntent.RIGHT_LOOKUP:
            suggestions = [
                "Show all rights holders for this work",
                "Check for split sheet discrepancies",
                "View associated contracts",
            ]
        elif understanding.intent == QueryIntent.RECONCILIATION:
            suggestions = [
                "Show detailed platform breakdown",
                "Flag all disputed entries",
                "Generate reconciliation report",
            ]
        elif understanding.intent == QueryIntent.SPLIT_QUERY:
            suggestions = [
                "Show all works by this party",
                "Find unmatched splits",
                "Export split sheet",
            ]
        else:
            suggestions = [
                "What are my total earnings this year?",
                "Show my publishing works",
                "What sync licenses do I have?",
            ]
        
        return suggestions[:3]

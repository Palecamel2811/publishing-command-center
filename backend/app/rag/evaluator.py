"""
RAGAS Evaluation Pipeline for Publishing & Rights Command Center.

Implements comprehensive evaluation of the RAG pipeline using:
- Faithfulness: Is the answer supported by the context?
- Answer Relevancy: How relevant is the answer to the question?
- Context Precision: Does the context contain the right information?
- Context Recall: Does the context cover all aspects needed for the answer?

Also provides:
- Synthetic dataset generation from ingested documents
- Evaluation report generation
- Continuous monitoring via stored metrics
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import json
from openai import OpenAI

from .chunker import LegalFinancialChunker
from .embedder import EmbeddingService
from .store import VectorStoreManager
from .hybrid_search import HybridSearcher

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of a RAGAS evaluation run."""
    run_id: str
    timestamp: str
    dataset_size: int
    metrics: dict[str, float]
    scores: list[dict[str, Any]]
    summary: str
    status: str = "completed"
    error: Optional[str] = None


@dataclass
class EvalQuestion:
    """A question-answer pair for evaluation."""
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    metadata: dict[str, Any] = field(default_factory=dict)


class RAGEvaluator:
    """
    RAGAS evaluation pipeline for the Publishing & Rights Command Center.
    
    Pipeline:
    1. Generate synthetic QA pairs from ingested documents
    2. Run RAG pipeline to get predicted answers
    3. Evaluate using RAGAS metrics
    4. Generate reports and store results
    """

    def __init__(
        self,
        llm_client: OpenAI,
        llm_model: str,
        embedder: EmbeddingService,
        store: VectorStoreManager,
        hybrid_searcher: HybridSearcher,
        chunker: LegalFinancialChunker,
        eval_dir: str = "./data/evaluations",
    ):
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.embedder = embedder
        self.store = store
        self.hybrid_searcher = hybrid_searcher
        self.chunker = chunker
        self.eval_dir = Path(eval_dir)
        self.eval_dir.mkdir(parents=True, exist_ok=True)
        
        # LLM providers for RAGAS (initialized lazily)
        self.llm_provider = None
        self.embedding_provider = None

    def _ensure_ragas_providers(self) -> None:
        """Initialize RAGAS LLM and embedding providers if not already initialized."""
        if self.llm_provider is not None and self.embedding_provider is not None:
            return
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings

        # Configure LLM
        self.llm_provider = LangchainLLMWrapper(
            ChatOpenAI(
                model=self.llm_model,
                openai_api_base=str(self.llm_client.base_url),
                openai_api_key=self.llm_client.api_key,
                temperature=0,
            )
        )

        # Configure embeddings
        self.embedding_provider = LangchainEmbeddingsWrapper(
            OpenAIEmbeddings(
                model=self.embedder.model,
                openai_api_base=self.embedder.base_url,
                openai_api_key=self.embedder.api_key,
            )
        )

    def generate_eval_dataset(
        self,
        num_questions: int = 10,
        doc_types: Optional[list[str]] = None,
    ) -> list[EvalQuestion]:
        """
        Generate synthetic QA pairs from ingested documents for evaluation.
        
        Uses LLM to create realistic questions based on actual document content.
        """
        if self.store._collection.count() == 0:
            logger.warning("No documents in vector store to generate questions from")
            return []

        # Get sample documents
        docs = self.store._collection.get(limit=num_questions * 3, include=["documents", "metadatas"])
        
        questions: list[EvalQuestion] = []
        
        system_prompt = """You are a music publishing intelligence analyst creating test questions for a RAG system.
Based on the provided document text, generate a realistic question that a publisher/songwriter might ask,
along with the exact answer grounded in the text.

Rules:
- Questions should be specific and answerable from the text
- Answers must be verbatim or closely paraphrased from the document
- Include relevant financial figures, names, dates exactly as shown
- If the text contains split information, create split-related questions
- If the text contains royalty data, create earnings/royalty questions

Respond in JSON format ONLY:
{
  "question": "The question to ask",
  "answer": "The exact answer from the document",
  "ground_truth": "The ground truth answer for evaluation"
}"""

        # Generate questions in batches
        batch_size = min(num_questions, 5)
        for i in range(0, len(docs["ids"]), batch_size):
            batch_docs = docs["documents"][i:i + batch_size]
            batch_meta = docs["metadatas"][i:i + batch_size]
            
            for idx, (content, metadata) in enumerate(zip(batch_docs, batch_meta)):
                if content is None or len(content.strip()) < 100:
                    continue
                
                try:
                    response = self.llm_client.chat.completions.create(
                        model=self.llm_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Document:\n{content}\n\nGenerate a question:"},
                        ],
                        temperature=0.3,
                        max_tokens=250,
                    )
                    
                    # Extract JSON from response
                    raw = response.choices[0].message.content.strip()
                    raw = raw.replace("```json", "").replace("```", "").strip()
                    
                    import json
                    qa = json.loads(raw)
                    
                    # Query the system to get the retrieved context
                    query_embedding = self.embedder.embed_text(qa["question"])
                    results = self.store.search(
                        query_embedding=query_embedding,
                        query_text=qa["question"],
                        top_k=3,
                        score_threshold=0.0,
                    )
                    
                    contexts = [r.document.content for r in results]
                    
                    questions.append(EvalQuestion(
                        question=qa["question"],
                        answer=qa.get("answer", ""),
                        contexts=contexts if contexts else [content],
                        ground_truth=qa.get("ground_truth", qa.get("answer", "")),
                        metadata={
                            "source": metadata.get("source_filename", "unknown"),
                            "doc_type": metadata.get("doc_type", "unknown"),
                            "generated_at": datetime.utcnow().isoformat(),
                        },
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to generate question {i + idx}: {e}")
                    continue
                
                if len(questions) >= num_questions:
                    break
            
            if len(questions) >= num_questions:
                break

        logger.info(f"Generated {len(questions)} evaluation questions")
        return questions

    def run_evaluation(
        self,
        dataset: list[EvalQuestion],
        run_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Run RAGAS evaluation on the test dataset.
        
        Measures:
        - faithfulness: Answer grounded in context?
        - answer_relevancy: Answer relevant to question?
        - context_precision: Context contains needed info?
        - context_recall: Context covers all aspects?
        """
        start_time = time.time()
        
        if not dataset:
            return EvaluationResult(
                run_id=run_id or "eval_manual",
                timestamp=datetime.utcnow().isoformat(),
                dataset_size=0,
                metrics={},
                scores=[],
                summary="No dataset provided for evaluation",
                status="skipped",
            )

        # Prepare RAGAS dataset
        ragas_dataset = []
        for i, qa in enumerate(dataset):
            # Query the RAG pipeline for predicted answers
            query_embedding = self.embedder.embed_text(qa.question)
            results = self.hybrid_searcher.hybrid_search(
                query_embedding=query_embedding,
                query_text=qa.question,
                top_k=3,
                score_threshold=0.0,
            )
            
            # Build context from top results
            contexts = [r.content for r in results[:3]] if results else []
            
            # If hybrid search fails, fall back to vector store
            if not contexts:
                store_results = self.store.search(
                    query_embedding=query_embedding,
                    query_text=qa.question,
                    top_k=3,
                    score_threshold=0.0,
                )
                contexts = [r.document.content for r in store_results]
            
            # Generate predicted answer via LLM
            context_str = "\n\n".join([f"Doc {i}: {c}" for i, c in enumerate(contexts)])
            
            try:
                response = self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a music publishing assistant. Answer based ONLY on the provided context.",
                        },
                        {
                            "role": "user",
                            "content": f"Context:\n{context_str}\n\nQuestion: {qa.question}",
                        },
                    ],
                    temperature=0.1,
                    max_tokens=500,
                )
                predicted_answer = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"LLM generation failed for question {i}: {e}")
                predicted_answer = "Error generating answer"
            
            ragas_dataset.append({
                "question": qa.question,
                "actual_answer": predicted_answer,
                "contexts": contexts,
                "ground_truth": qa.ground_truth,
            })

        # Run RAGAS evaluation
        try:
            self._ensure_ragas_providers()
            from ragas import EvaluationDataset as RAGASEvaluationDataset, evaluate
            from ragas.metrics import (
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            )
            
            eval_dataset = RAGASEvaluationDataset.from_pandas(
                __import__("pandas").DataFrame(ragas_dataset)
            )
            
            # Run evaluation
            evaluation_result = evaluate(
                eval_dataset,
                metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                llm=self.llm_provider,
                embeddings=self.embedding_provider,
                raise_exception=False,
            )
            
            # Extract scores
            scores = []
            for row in evaluation_result["row"]:
                scores.append({
                    "question": row["question"],
                    "faithfulness": row.get("faithfulness", 0),
                    "answer_relevancy": row.get("answer_relevancy", 0),
                    "context_precision": row.get("context_precision", 0),
                    "context_recall": row.get("context_recall", 0),
                })
            
            # Calculate averages
            metrics = {
                "faithfulness": float(evaluation_result["faithfulness"]),
                "answer_relevancy": float(evaluation_result["answer_relevancy"]),
                "context_precision": float(evaluation_result["context_precision"]),
                "context_recall": float(evaluation_result["context_recall"]),
            }
            
            # Generate summary
            elapsed = time.time() - start_time
            summary = (
                f"RAGAS Evaluation Complete ({len(scores)} questions, {elapsed:.1f}s)\n"
                f"Faithfulness: {metrics['faithfulness']:.2f}\n"
                f"Answer Relevancy: {metrics['answer_relevancy']:.2f}\n"
                f"Context Precision: {metrics['context_precision']:.2f}\n"
                f"Context Recall: {metrics['context_recall']:.2f}"
            )
            
            result = EvaluationResult(
                run_id=run_id or f"eval_{int(time.time())}",
                timestamp=datetime.utcnow().isoformat(),
                dataset_size=len(scores),
                metrics=metrics,
                scores=scores,
                summary=summary,
            )
            
            # Save results to disk
            self._save_evaluation_result(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}", exc_info=True)
            return EvaluationResult(
                run_id=run_id or "eval_failed",
                timestamp=datetime.utcnow().isoformat(),
                dataset_size=len(dataset),
                metrics={},
                scores=[],
                summary=f"Evaluation failed: {str(e)}",
                status="failed",
                error=str(e),
            )

    def _save_evaluation_result(self, result: EvaluationResult) -> None:
        """Save evaluation result to disk for historical tracking."""
        filepath = self.eval_dir / f"{result.run_id}.json"
        
        data = {
            "run_id": result.run_id,
            "timestamp": result.timestamp,
            "dataset_size": result.dataset_size,
            "metrics": result.metrics,
            "scores": result.scores,
            "summary": result.summary,
            "status": result.status,
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Saved evaluation result to {filepath}")

    def get_evaluation_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get historical evaluation results."""
        results = []
        eval_files = sorted(
            self.eval_dir.glob("eval_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]
        
        for filepath in eval_files:
            try:
                with open(filepath) as f:
                    data = json.load(f)
                results.append(data)
            except Exception as e:
                logger.warning(f"Failed to load eval result {filepath}: {e}")
        
        return results

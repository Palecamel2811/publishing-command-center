"""
Publishing & Rights Command Center - FastAPI Application

Main entry point that wires together:
- Document ingestion
- RAG retrieval pipeline
- Reconciliation service
- REST API endpoints
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

from .config import Settings
from .models import (
    IngestResult,
    RAGQuery,
    RAGResponse,
    RoyaltySummary,
)
from .rag.chunker import LegalFinancialChunker
from .rag.embedder import EmbeddingService
from .rag.retriever import RAGRetriever
from .rag.store import VectorStoreManager
from .rag.hybrid_search import HybridSearcher
from .rag.evaluator import RAGEvaluator
from .services.ingestion import DocumentIngestionService
from .services.reconciliation import ReconciliationService
from .db.database import init_db, get_session, engine
from .db.models import Work, Split, RoyaltyEntry as RelRoyaltyEntry, SyncLicense as RelSyncLicense, DocumentChunk
from sqlmodel import select, Session
from sqlalchemy.orm import selectinload

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Settings ────────────────────────────────────────────────────────────────

settings = Settings()

# ── Shared Services ─────────────────────────────────────────────────────────

_llm_client: OpenAI | None = None
_embedder: EmbeddingService | None = None
_vector_store: VectorStoreManager | None = None
_rag_retriever: RAGRetriever | None = None
_hybrid_searcher: HybridSearcher | None = None
_evaluator: RAGEvaluator | None = None
_ingestion_service: DocumentIngestionService | None = None
_reconciliation_service: ReconciliationService | None = None

# Sample data stores
_sample_works: list[dict[str, Any]] = []
_sample_royalties: list[dict[str, Any]] = []
_sample_sync_licenses: list[dict[str, Any]] = []


def _get_llm_client() -> OpenAI:
    global _llm_client
    if _llm_client is None:
        _llm_client = OpenAI(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
        )
    return _llm_client


def _get_embedder() -> EmbeddingService:
    global _embedder
    if _embedder is None:
        _embedder = EmbeddingService(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
        )
    return _embedder


def _get_vector_store() -> VectorStoreManager:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreManager(store_path=settings.resolved_vector_store_path)
        _vector_store.initialize()
    return _vector_store


def _get_rag_retriever() -> RAGRetriever:
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever(
            embedder=_get_embedder(),
            store=_get_vector_store(),
            chunker=LegalFinancialChunker(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            ),
            llm_client=_get_llm_client(),
            llm_model=settings.llm_model,
            top_k=settings.top_k,
            score_threshold=settings.score_threshold,
            hybrid_searcher=_get_hybrid_searcher(),
        )
    return _rag_retriever


def _get_hybrid_searcher() -> HybridSearcher:
    global _hybrid_searcher
    if _hybrid_searcher is None:
        _hybrid_searcher = HybridSearcher(
            vector_store=_get_vector_store(),
            vector_weight=0.7,
            keyword_weight=0.3,
            top_k=settings.top_k,
            score_threshold=settings.score_threshold,
        )
    return _hybrid_searcher


def _get_evaluator() -> RAGEvaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = RAGEvaluator(
            llm_client=_get_llm_client(),
            llm_model=settings.llm_model,
            embedder=_get_embedder(),
            store=_get_vector_store(),
            hybrid_searcher=_get_hybrid_searcher(),
            chunker=LegalFinancialChunker(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            ),
            eval_dir="./data/evaluations",
        )
    return _evaluator


def _get_ingestion_service() -> DocumentIngestionService:
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = DocumentIngestionService(
            settings=settings,
            embedder=_get_embedder(),
            store=_get_vector_store(),
            llm_client=_get_llm_client(),
        )
    return _ingestion_service


def _get_reconciliation_service() -> ReconciliationService:
    global _reconciliation_service
    if _reconciliation_service is None:
        _reconciliation_service = ReconciliationService()
    return _reconciliation_service


def _warmup_bm25_index() -> None:
    """Index all existing documents in the vector store into BM25 for keyword search."""
    store = _get_vector_store()
    searcher = _get_hybrid_searcher()
    
    if store._collection.count() == 0:
        return
    
    # Get all documents
    docs = store._collection.get(include=["documents", "metadatas"])
    
    for i in range(len(docs["ids"])):
        doc_id = docs["ids"][i]
        content = docs["documents"][i] or ""
        if content:
            searcher.index_document(doc_id, content)
    
    logger.info(f"BM25 index warmed up: {searcher.bm25_index.N} documents indexed")


# ── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("Starting Publishing & Rights Command Center...")
    logger.info(f"LLM endpoint: {settings.openai_base_url}")
    logger.info(f"LLM model: {settings.llm_model}")
    logger.info(f"Embedding model: {settings.embedding_model}")
    logger.info(f"Vector store: {settings.vector_store_path}")
    logger.info(f"Database: {settings.database_url}")
    
    # Initialize services
    _get_llm_client()
    _get_embedder()
    _get_vector_store()
    _get_hybrid_searcher()
    _get_evaluator()
    _get_ingestion_service()
    _get_reconciliation_service()
    
    # Initialize relational database
    init_db()
    logger.info("Database tables initialized")

    # Auto-populate sample dataset on cloud startup if database is empty
    with Session(engine) as session:
        first_work = session.exec(select(Work)).first()
        if not first_work:
            logger.info("Empty database detected on startup — auto-populating 88 sample documents...")
            try:
                import subprocess
                subprocess.Popen(["python3", "scripts/populate_sample_data.py"])
            except Exception as pop_err:
                logger.warning(f"Auto-populate trigger failed: {pop_err}")
    
    # Warm up BM25 index with existing documents
    _warmup_bm25_index()
    
    app.state.start_time = time.time()
    logger.info("All services initialized")
    yield

    
    # Shutdown
    logger.info("Shutting down Publishing & Rights Command Center...")


# ── App Factory ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Publishing & Rights Command Center",
    description=(
        "AI-powered music publishing data management. Track, reconcile, and "
        "visualize royalties, rights, and splits across DSPs, PROs, and sync platforms."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - allow all production origins and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        uptime = time.time() - app.state.start_time
    except AttributeError:
        uptime = 0
    return {
        "status": "healthy",
        "version": "1.0.0",
        "llm_endpoint": settings.openai_base_url,
        "llm_model": settings.llm_model,
        "vector_store": _get_vector_store().get_stats(),
        "embedder": _get_embedder().get_stats(),
        "uptime_seconds": uptime,
    }


# ── Dashboard Endpoints ─────────────────────────────────────────────────────

@app.get("/api/dashboard")
async def get_dashboard(period: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get full dashboard data for the power user interface."""
    from datetime import datetime
    
    with Session(engine) as session:
        # 1. Works with earnings and platform counts (eager-load relationships)
        works_stmt = select(Work).options(selectinload(Work.splits), selectinload(Work.royalties), selectinload(Work.sync_licenses)).order_by(Work.title)
        works = session.exec(works_stmt).all()
        
        # 2. Royalty Summary
        all_royalties = session.exec(select(RelRoyaltyEntry)).all()
        
        # Collect unique non-empty period_start options for the frontend dropdown
        available_periods = sorted(list(set(r.period_start for r in all_royalties if r.period_start)))
        
        if start_date or end_date:
            royalties = []
            for r in all_royalties:
                r_date = r.period_start or r.created_at.strftime("%Y-%m-%d")
                if start_date and r_date < start_date:
                    continue
                if end_date and r_date > end_date:
                    continue
                royalties.append(r)
        elif period and period.lower() != "all":
            royalties = [r for r in all_royalties if r.period_start == period]
        else:
            royalties = all_royalties
        
        total_gross = sum(r.gross_amount for r in royalties)
        total_net = sum(r.net_amount for r in royalties)
        total_fees = total_gross - total_net
        
        by_platform: dict[str, float] = {}
        by_type: dict[str, float] = {}
        by_work: dict[str, float] = {}
        
        for r in royalties:
            by_platform[r.platform] = by_platform.get(r.platform, 0) + r.net_amount
            by_type[r.royalty_type] = by_type.get(r.royalty_type, 0) + r.net_amount
            work = next((w for w in works if str(w.id) == str(r.work_id)), None)
            work_title = work.title if work else "Unknown"
            by_work[work_title] = by_work.get(work_title, 0) + r.net_amount
        
        # 3. Recent Royalties (last 5)
        recent_stmt = select(RelRoyaltyEntry).order_by(RelRoyaltyEntry.created_at.desc()).limit(5)
        recent_royalties = session.exec(recent_stmt).all()
        
        # 4. Sync Licenses
        sync_stmt = select(RelSyncLicense)
        sync_licenses = session.exec(sync_stmt).all()
        
        # 5. Pending Splits (splits with < 100% verified)
        pending_splits = []
        for work in works:
            splits = [s for s in work.splits]
            total_share = sum(s.share_percentage for s in splits)
            if total_share < 100.0:
                pending_splits.append({
                    "work": work.title,
                    "missing": f"{100.0 - total_share:.1f}% unallocated",
                    "status": "pending",
                    "priority": "high" if (100.0 - total_share) > 10 else "medium",
                })
        
        # 6. Alerts (placeholder logic)
        alerts = []
        if len(works) == 0:
            alerts.append({"type": "info", "message": "No works ingested yet. Upload split sheets to get started.", "date": datetime.utcnow().isoformat()})
        
        if start_date or end_date:
            p_start = start_date or "Beginning"
            p_end = end_date or "Present"
        else:
            p_start = period if (period and period.lower() != "all") else ("All Time" if royalties else None)
            p_end = period if (period and period.lower() != "all") else ("All Time" if royalties else None)

        return {
            "summary": RoyaltySummary(
                total_gross=total_gross,
                total_net=total_net,
                total_fees=total_fees,
                count=len(royalties),
                period_start=p_start,
                period_end=p_end,
                by_platform=by_platform,
                by_type=by_type,
                by_work=by_work,
            ).model_dump(),
            "available_periods": available_periods,
            "recent_royalties": [
                {
                    "id": str(r.id),
                    "work": next((w.title for w in works if str(w.id) == str(r.work_id)), "Unknown"),
                    "platform": r.platform,
                    "type": r.royalty_type,
                    "amount": r.net_amount,
                    "period": f"{r.period_start} to {r.period_end}",
                    "date": r.created_at.isoformat(),
                }
                for r in recent_royalties
            ],
            "works": [
                {
                    "id": str(w.id),
                    "title": w.title,
                    "isrc": w.isrc,
                    "iswc": w.iswc,
                    "splits_count": len(w.splits),
                    "total_earnings": w.total_earnings,
                    "platforms": list(set(r.platform for r in royalties if str(r.work_id) == str(w.id))),
                    "status": w.status,
                    "splits": [
                        {
                            "party": s.party_name,
                            "share": s.share_percentage,
                            "pro": getattr(s, "pro", None) or "Unknown",
                            "type": getattr(s, "share_type", "writer")
                        }
                        for s in w.splits
                    ]
                }
                for w in works
            ],
            "sync_licenses": [
                {
                    "id": str(s.id),
                    "work": next((w.title for w in works if str(w.id) == str(s.work_id)), "Unknown"),
                    "title": s.title,
                    "licensee": s.licensee,
                    "media_type": s.media_type,
                    "fee": s.fee,
                    "currency": s.currency,
                    "status": s.status,
                    "term_end": s.term_end,
                }
                for s in sync_licenses
            ],
            "reconciliation_status": {
                "total_discrepancies": len(pending_splits),
                "critical": sum(1 for p in pending_splits if (100.0 - sum(s.share_percentage for s in next((w.splits for w in works if w.title == p["work"]), []))) > 20),
                "high": sum(1 for p in pending_splits if 10 < (100.0 - sum(s.share_percentage for s in next((w.splits for w in works if w.title == p["work"]), []))) <= 20),
                "medium": sum(1 for p in pending_splits if 5 < (100.0 - sum(s.share_percentage for s in next((w.splits for w in works if w.title == p["work"]), []))) <= 10),
                "low": sum(1 for p in pending_splits if (100.0 - sum(s.share_percentage for s in next((w.splits for w in works if w.title == p["work"]), []))) <= 5),
                "last_run": datetime.utcnow().isoformat(),
            },
            "pending_splits": pending_splits,
            "alerts": alerts,
            "revenue_trend": [
                {"month": k, "amount": round(v, 2)}
                for k, v in sorted(
                    {
                        (r.period_start or r.created_at.strftime("%Y-%m")): sum(
                            x.net_amount for x in royalties if (x.period_start or x.created_at.strftime("%Y-%m")) == (r.period_start or r.created_at.strftime("%Y-%m"))
                        )
                        for r in royalties
                    }.items(),
                    key=lambda item: (
                        item[0].split()[1] + "-Q" + item[0].split()[0][1] if ("Q" in item[0] and len(item[0].split()) == 2) else item[0]
                    )
                )
            ] if royalties else [],
        }


@app.get("/api/dashboard/royalties")
async def get_royalties(
    platform: Optional[str] = None,
    royalty_type: Optional[str] = None,
    limit: int = 50,
):
    """Get filtered royalty data from the relational database."""
    with Session(engine) as session:
        stmt = select(RelRoyaltyEntry)
        if platform:
            stmt = stmt.where(RelRoyaltyEntry.platform == platform)
        if royalty_type:
            stmt = stmt.where(RelRoyaltyEntry.royalty_type == royalty_type)
        stmt = stmt.order_by(RelRoyaltyEntry.created_at.desc()).limit(limit)
        entries = session.exec(stmt).all()
        
        works_stmt = select(Work)
        works_map = {str(w.id): w.title for w in session.exec(works_stmt).all()}
        
        total_gross = sum(r.gross_amount for r in entries)
        total_net = sum(r.net_amount for r in entries)
        
        return {
            "royalties": [
                {
                    "id": str(r.id),
                    "work_id": str(r.work_id),
                    "work": works_map.get(str(r.work_id), "Unknown"),
                    "platform": r.platform,
                    "type": r.royalty_type,
                    "period": f"{r.period_start} to {r.period_end}" if r.period_start else "N/A",
                    "period_start": r.period_start,
                    "period_end": r.period_end,
                    "gross_amount": r.gross_amount,
                    "fees_deducted": r.fees_deducted,
                    "amount": r.net_amount,
                    "currency": r.currency,
                    "source_document": r.source_document,
                    "date": r.created_at.isoformat(),
                }
                for r in entries
            ],
            "summary": {
                "total_gross": total_gross,
                "total_net": total_net,
                "total_fees": total_gross - total_net,
                "count": len(entries),
            },
        }


# ── Work Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/works")
async def list_works(status: str = "active"):
    """List all works with summary data."""
    with Session(engine) as session:
        stmt = select(Work).options(selectinload(Work.splits), selectinload(Work.royalties))
        if status != "all":
            stmt = stmt.where(Work.status == status)
        works = session.exec(stmt).all()
        return {
            "works": [
                {
                    "id": str(w.id),
                    "title": w.title,
                    "isrc": w.isrc,
                    "iswc": w.iswc,
                    "splits_count": len(w.splits),
                    "total_earnings": w.total_earnings or sum(r.net_amount for r in w.royalties),
                    "platforms": list(set(r.platform for r in w.royalties)),
                    "status": w.status,
                }
                for w in works
            ],
            "count": len(works),
        }


@app.post("/api/works", status_code=201)
async def create_work(work: Work):
    """Create a new work entry."""
    with Session(engine) as session:
        session.add(work)
        session.commit()
        session.refresh(work)
        return {
            "work": {
                "id": str(work.id),
                "title": work.title,
                "isrc": work.isrc,
                "iswc": work.iswc,
                "splits_count": len(work.splits) if work.splits else 0,
                "total_earnings": work.total_earnings,
                "status": work.status,
            },
            "created": True,
        }


# ── Sync License Endpoints ──────────────────────────────────────────────────

@app.get("/api/sync-licenses")
async def list_sync_licenses(status: str = "active"):
    """List sync licenses."""
    with Session(engine) as session:
        stmt = select(RelSyncLicense)
        if status != "all":
            stmt = stmt.where(RelSyncLicense.status == status)
        licenses = session.exec(stmt).all()
        
        works_stmt = select(Work)
        works_map = {str(w.id): w.title for w in session.exec(works_stmt).all()}
        
        return {
            "sync_licenses": [
                {
                    "id": str(s.id),
                    "work_id": str(s.work_id),
                    "work": works_map.get(str(s.work_id), "Unknown"),
                    "title": s.title,
                    "licensee": s.licensee,
                    "media_type": s.media_type,
                    "territory": s.territory,
                    "term_start": s.term_start,
                    "term_end": s.term_end,
                    "fee": s.fee,
                    "currency": s.currency,
                    "status": s.status,
                }
                for s in licenses
            ],
            "count": len(licenses),
        }


@app.post("/api/sync-licenses", status_code=201)
async def create_sync_license(license_data: RelSyncLicense):
    """Create a new sync license entry."""
    with Session(engine) as session:
        session.add(license_data)
        session.commit()
        session.refresh(license_data)
        return {"sync_license": license_data.model_dump(), "created": True}


# ── Document Ingestion Endpoints ────────────────────────────────────────────

@app.post("/api/ingest/upload")
async def ingest_file(
    file: UploadFile = File(...),
    doc_type: str = Form(None),
    work_id: str = Form(None),
):
    """
    Upload and ingest a document.
    
    Supported formats: PDF, CSV, Excel, Word, PowerPoint, TXT
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    try:
        ingestion_service = _get_ingestion_service()
        with Session(engine) as db_session:
            result = await ingestion_service.ingest_file(
                file_path=f"./data/uploads/{file.filename}",
                file_name=file.filename,
                file_data=content,
                doc_type=doc_type,
                work_id=work_id,
                db_session=db_session,
            )
        _warmup_bm25_index()
        return {"result": result.model_dump(), "success": True}
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest/batch")
async def ingest_batch(
    files: list[UploadFile] = File(...),
    doc_type: str = Form(None),
):
    """Upload and ingest multiple files at once."""
    results = []
    ingestion_service = _get_ingestion_service()
    
    with Session(engine) as db_session:
        for file in files:
            content = await file.read()
            try:
                result = await ingestion_service.ingest_file(
                    file_path=f"./data/uploads/{file.filename}",
                    file_name=file.filename,
                    file_data=content,
                    doc_type=doc_type,
                    db_session=db_session,
                )
                results.append({
                    "filename": file.filename,
                    "chunks": result.chunks_created,
                    "works": result.works_found,
                    "warnings": result.warnings,
                    "result": result.model_dump(),
                })
            except Exception as e:
                logger.error(f"Batch ingestion error for {file.filename}: {e}")
                results.append({
                    "filename": file.filename,
                    "error": str(e),
                    "chunks": 0,
                    "warnings": [str(e)],
                })
    
    _warmup_bm25_index()

    return {
        "results": results,
        "total": len(results),
        "successful": sum(1 for r in results if "result" in r and r.get("chunks", 0) > 0),
        "failed": sum(1 for r in results if "error" in r or r.get("chunks", 0) == 0),
    }


def _find_document_file(filename: str) -> Optional[Path]:
    import re
    base_data = (Path(__file__).resolve().parent.parent.parent / "data").resolve()
    if not base_data.exists():
        return None
    
    stem_name = Path(filename).name.lower()
    clean_stem = re.sub(r"\.(pdf|txt|csv|docx|xlsx)$", "", stem_name, flags=re.IGNORECASE)

    # Direct candidate paths
    for folder in ["uploads", "splitsheets", "royalties", "contracts", ""]:
        for name_variant in [filename, stem_name, f"{clean_stem}.pdf", f"{clean_stem}.pdf.txt", f"{clean_stem}.txt", f"{clean_stem}.csv"]:
            candidate = base_data / folder / name_variant if folder else base_data / name_variant
            if candidate.exists() and candidate.is_file():
                return candidate

    # Recursive search
    for found_file in base_data.rglob("*"):
        if found_file.is_file():
            fname_lower = found_file.name.lower()
            if (
                fname_lower == stem_name or
                fname_lower == f"{stem_name}.txt" or
                (len(clean_stem) >= 3 and clean_stem in fname_lower)
            ):
                return found_file

    return None


@app.get("/api/ingest/history")
async def get_ingestion_history(limit: int = 20):
    """Get recent ingestion history for active files on disk."""
    with Session(engine) as session:
        chunks_stmt = select(DocumentChunk).order_by(DocumentChunk.created_at.desc()).limit(limit * 20)
        chunks = session.exec(chunks_stmt).all()
        seen = set()
        history = []
        for c in chunks:
            if c.source_filename not in seen:
                seen.add(c.source_filename)
                # Verify file still exists on disk
                if _find_document_file(c.source_filename):
                    history.append({
                        "id": c.doc_id,
                        "filename": c.source_filename,
                        "doc_type": c.doc_type,
                        "work_title": c.work_title,
                        "created_at": c.created_at.isoformat(),
                    })
                    if len(history) >= limit:
                        break
        return {"history": history, "count": len(history)}


@app.get("/api/documents/view/{filename:path}")
async def view_document(filename: str, download: bool = False):
    """View/download original document file by filename."""
    found_file = _find_document_file(filename)
    if found_file:
        ext = found_file.suffix.lower()
        media_type = "application/pdf" if ext == ".pdf" else \
                     "text/plain" if ext in (".txt", ".log") else \
                     "text/csv" if ext == ".csv" else \
                     "application/octet-stream"
        
        disposition = f'attachment; filename="{found_file.name}"' if download else f'inline; filename="{found_file.name}"'
        return FileResponse(path=str(found_file), media_type=media_type, headers={"Content-Disposition": disposition})

    raise HTTPException(status_code=404, detail=f"Document '{filename}' not found on disk")


@app.delete("/api/documents/{filename:path}")
async def delete_document(filename: str):
    """Delete a document, its vector store chunks, and relational records."""
    try:
        with Session(engine) as session:
            # Delete relational document chunks
            doc_chunks = session.exec(select(DocumentChunk).where(DocumentChunk.source_filename == filename)).all()

            for dc in doc_chunks:
                session.delete(dc)

            # Delete splits referencing this source document
            splits = session.exec(select(Split).where(Split.source_document == filename)).all()
            affected_work_ids = {s.work_id for s in splits if s.work_id}
            for s in splits:
                session.delete(s)

            # Delete royalties referencing this source document
            royalties = session.exec(select(RelRoyaltyEntry).where(RelRoyaltyEntry.source_document == filename)).all()
            affected_work_ids.update({r.work_id for r in royalties if r.work_id})
            for r in royalties:
                session.delete(r)

            # Recalculate earnings for affected works; remove orphan works
            for wid in affected_work_ids:
                work = session.exec(select(Work).where(Work.id == wid)).first()
                if work:
                    remaining_royalties = session.exec(select(RelRoyaltyEntry).where(RelRoyaltyEntry.work_id == wid)).all()
                    remaining_splits = session.exec(select(Split).where(Split.work_id == wid)).all()
                    remaining_syncs = session.exec(select(RelSyncLicense).where(RelSyncLicense.work_id == wid)).all()

                    if not remaining_royalties and not remaining_splits and not remaining_syncs:
                        # Work is completely empty — delete it so it doesn't linger on dashboard
                        store = _get_vector_store()
                        store.delete_by_work(work.title)
                        session.delete(work)
                    else:
                        r_sum = sum(r.net_amount for r in remaining_royalties)
                        s_sum = sum(s.fee * 0.5 for s in remaining_syncs)
                        work.total_earnings = r_sum + s_sum
                        session.add(work)

            session.commit()


        return {
            "status": "success",
            "filename": filename,
            "vector_chunks_deleted": chunks_deleted,
            "relational_records_deleted": len(doc_chunks) + len(royalties),
        }
    except Exception as e:
        logger.error(f"Failed to delete document {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/works/{work_id}")
async def delete_work(work_id: str):
    """Delete a work and all associated splits, royalties, and sync licenses."""
    try:
        with Session(engine) as session:
            work = session.exec(select(Work).where(Work.id == work_id)).first()
            if not work:
                raise HTTPException(status_code=404, detail="Work not found")

            # Delete related entities
            for s in work.splits:
                session.delete(s)
            for r in work.royalties:
                session.delete(r)
            for sl in work.sync_licenses:
                session.delete(sl)

            # Delete from vector store
            store = _get_vector_store()
            store.delete_by_work(work.title)

            session.delete(work)
            session.commit()

        return {"status": "success", "work_id": work_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete work {work_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/export")
async def export_reports(report_type: str = "royalties"):
    """Export reports as CSV."""
    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    with Session(engine) as session:
        if report_type == "works":
            writer.writerow(["Title", "ISRC", "ISWC", "Status", "Splits Count", "Total Earnings"])
            works = session.exec(select(Work).options(selectinload(Work.splits))).all()
            for w in works:
                writer.writerow([w.title, w.isrc or "", w.iswc or "", w.status, len(w.splits), f"{w.total_earnings:.2f}"])
        elif report_type == "sync":
            writer.writerow(["Work", "Licensee", "Media Type", "Territory", "Fee", "Status", "Term End"])
            syncs = session.exec(select(RelSyncLicense)).all()
            works_map = {str(w.id): w.title for w in session.exec(select(Work)).all()}
            for s in syncs:
                writer.writerow([works_map.get(str(s.work_id), "Unknown"), s.licensee, s.media_type, s.territory or "", f"{s.fee:.2f}", s.status, s.term_end or ""])
        elif report_type in ["royalties", "default"]:
            writer.writerow(["Work", "Platform", "Royalty Type", "Period Start", "Period End", "Gross Amount", "Fees Deducted", "Net Amount", "Source Document", "Date"])
            royalties = session.exec(select(RelRoyaltyEntry).order_by(RelRoyaltyEntry.created_at.desc())).all()
            works_map = {str(w.id): w.title for w in session.exec(select(Work)).all()}
            for r in royalties:
                writer.writerow([
                    works_map.get(str(r.work_id), "Unknown"),
                    r.platform,
                    r.royalty_type,
                    r.period_start,
                    r.period_end,
                    f"{r.gross_amount:.2f}",
                    f"{r.fees_deducted:.2f}",
                    f"{r.net_amount:.2f}",
                    r.source_document or "",
                    r.created_at.isoformat(),
                ])
        else:
            raise HTTPException(status_code=400, detail=f"Invalid report_type '{report_type}'. Must be royalties, works, or sync.")

                
    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=publishing_{report_type}_export.csv"}
    )


# ── RAG Query Endpoint ──────────────────────────────────────────────────────

@app.post("/api/query", response_model=RAGResponse)
async def rag_query(query: RAGQuery):
    """
    Query your publishing data with natural language.
    
    Examples:
    - "How much did I earn from Spotify last quarter?"
    - "Who controls the sync rights for Midnight Echoes?"
    - "Show my top earning platforms"
    - "Reconcile Apple Music vs ASCAP data"
    """
    try:
        retriever = _get_rag_retriever()
        result = retriever.query(
            query=query.query,
            filters=query.filters,
            top_k=query.top_k,
            score_threshold=query.score_threshold,
        )
        return result
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query/stream")
async def rag_query_stream(query: RAGQuery):
    """
    Stream RAG query response in real-time as Server-Sent Events (SSE).
    Provides <200ms time-to-first-token.
    """
    try:
        retriever = _get_rag_retriever()
        return StreamingResponse(
            retriever.stream_query(
                query=query.query,
                filters=query.filters,
                top_k=query.top_k,
                score_threshold=query.score_threshold,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error(f"Streaming query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Reconciliation Endpoint ─────────────────────────────────────────────────

@app.post("/api/reconcile/run")
async def run_reconciliation(data: Optional[dict[str, Any]] = None):
    """
    Run reconciliation checks on royalty data.
    
    Expects data_sources array with platform data to compare.
    """
    from dataclasses import asdict
    try:
        req_data = data or {}
        data_sources = req_data.get("data_sources", [])
        
        # If no data_sources provided in payload, load from DB
        if not data_sources:
            with Session(engine) as session:
                royalties = session.exec(select(RelRoyaltyEntry)).all()
                works_map = {str(w.id): w.title for w in session.exec(select(Work)).all()}
                by_work: dict[str, list[RelRoyaltyEntry]] = {}
                for r in royalties:
                    w_title = works_map.get(str(r.work_id), "Unknown")
                    by_work.setdefault(w_title, []).append(r)
                
                for w_title, r_list in by_work.items():
                    for r in r_list:
                        data_sources.append({
                            "work_title": w_title,
                            "platform": r.platform,
                            "gross_revenue": r.gross_amount,
                            "net_revenue": r.net_amount,
                            "period_start": r.period_start,
                            "period_end": r.period_end,
                        })

        service = _get_reconciliation_service()
        result = service.check_reconciliation(
            data_sources=data_sources,
            splits=req_data.get("splits"),
            period_start=req_data.get("period_start"),
            period_end=req_data.get("period_end"),
        )
        return asdict(result)
    except Exception as e:
        logger.error(f"Reconciliation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Vector Store Management ─────────────────────────────────────────────────

@app.get("/api/store/stats")
async def get_store_stats():
    """Get vector store statistics."""
    return _get_vector_store().get_stats()


@app.post("/api/store/clear")
async def clear_store():
    """Clear all documents from the vector store."""
    _get_vector_store().clear()
    return {"message": "Store cleared", "success": True}


# ── Embedding Stats ─────────────────────────────────────────────────────────

@app.get("/api/embedder/stats")
async def get_embedder_stats():
    """Get embedding service statistics."""
    return _get_embedder().get_stats()


# ── RAGAS Evaluation Endpoints ──────────────────────────────────────────────

@app.post("/api/eval/generate-dataset")
async def generate_eval_dataset(num_questions: int = 10):
    """
    Generate synthetic QA pairs from ingested documents for evaluation.
    """
    try:
        evaluator = _get_evaluator()
        dataset = evaluator.generate_eval_dataset(num_questions=num_questions)
        return {
            "status": "success",
            "questions_generated": len(dataset),
            "questions": [
                {
                    "id": i,
                    "question": q.question,
                    "ground_truth": q.ground_truth,
                    "source": q.metadata.get("source", "unknown"),
                }
                for i, q in enumerate(dataset)
            ],
        }
    except Exception as e:
        logger.error(f"Dataset generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/eval/run")
async def run_evaluation(run_id: Optional[str] = None, num_questions: int = 10):
    """
    Run RAGAS evaluation on the generated test dataset.
    
    Measures:
    - faithfulness: Is the answer grounded in the context?
    - answer_relevancy: How relevant is the answer to the question?
    - context_precision: Does the context contain the right information?
    - context_recall: Does the context cover all aspects needed?
    """
    try:
        evaluator = _get_evaluator()
        
        # Generate or load dataset
        dataset = evaluator.generate_eval_dataset(num_questions=num_questions)
        
        if not dataset:
            raise HTTPException(
                status_code=400,
                detail="No documents in vector store to evaluate. Ingest documents first.",
            )
        
        # Run evaluation
        result = evaluator.run_evaluation(dataset=dataset, run_id=run_id)
        
        return {
            "status": result.status,
            "run_id": result.run_id,
            "dataset_size": result.dataset_size,
            "metrics": result.metrics,
            "summary": result.summary,
            "scores": result.scores,
            "error": result.error,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/eval/history")
async def get_evaluation_history(limit: int = 10):
    """Get historical evaluation results."""
    try:
        evaluator = _get_evaluator()
        history = evaluator.get_evaluation_history(limit=limit)
        return {"evaluations": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Failed to load evaluation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.debug,
    )

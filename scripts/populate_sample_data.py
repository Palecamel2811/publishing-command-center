#!/usr/bin/env python3
"""
Populate the vector store with sample publishing data.

Walks through /data/ directories, chunks documents using LegalFinancialChunker,
generates embeddings via EmbeddingService, and upserts into ChromaDB.

Usage:
    cd backend && python ../scripts/populate_sample_data.py
    OR
    cd ../scripts && python populate_sample_data.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import Settings
from app.rag.chunker import LegalFinancialChunker
from app.rag.embedder import EmbeddingService
from app.rag.store import VectorStoreManager
from app.db.database import init_db, engine, Session
from app.services.ingestion import DocumentIngestionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("populate_sample_data")


def parse_spotify_filename(filepath: Path) -> dict:
    """Parse filename like golden_hour_spotify_q1_2024.pdf.txt"""
    stem = filepath.stem  # .pdf.txt -> .pdf -> empty
    # Get the part before .pdf.txt
    name = filepath.name.replace(".pdf.txt", "")
    parts = name.split("_")
    
    work_id = parts[0]  # golden_hour
    work_title = " ".join(p.capitalize() for p in work_id.split("_"))
    platform = parts[1]  # spotify
    period = parts[2] if len(parts) > 2 else "unknown"  # q1_2024
    
    return {
        "work_id": work_id,
        "work_title": work_title,
        "platform": platform,
        "period": period,
    }


def parse_split_filename(filepath: Path) -> dict:
    """Parse filename like golden_hour_split.pdf.txt"""
    stem = filepath.name.replace(".pdf.txt", "")
    work_id = stem.replace("_split", "")
    work_title = " ".join(p.capitalize() for p in work_id.split("_"))
    
    return {
        "work_id": work_id,
        "work_title": work_title,
        "doc_type": "split_sheet",
    }


def parse_contract_filename(filepath: Path) -> dict:
    """Parse filename like golden_hour_sync_contract.pdf.txt"""
    stem = filepath.name.replace(".pdf.txt", "")
    work_id = stem.replace("_sync_contract", "")
    work_title = " ".join(p.capitalize() for p in work_id.split("_"))
    
    return {
        "work_id": work_id,
        "work_title": work_title,
        "doc_type": "sync_contract",
    }


def determine_doc_type(filepath: Path) -> str:
    """Determine document type from path and content."""
    # Data lives in project root /data/, not backend/data/
    data_root = Path(__file__).parent.parent / "data"
    rel_path = str(filepath.relative_to(data_root))

    if "splitsheet" in rel_path.lower() or "split" in rel_path.lower():
        return "split_sheet"
    elif "contract" in rel_path.lower() or "license" in rel_path.lower():
        return "license_contract"
    else:
        return "royalty_statement"


def extract_metadata_from_content(
    filepath: Path,
    doc_type: str,
    content: str,
) -> dict:
    """Extract structured metadata from document content."""
    metadata: dict = {}
    filename = filepath.name
    
    # Try to parse from content if filename parsing fails
    import re
    
    # Work title from content
    work_match = re.search(r"Work:\s*([^\n|,]{3,100})", content, re.IGNORECASE)
    if work_match:
        metadata["work_title"] = work_match.group(1).strip()
        if "work_id" not in metadata:
            work_id = work_match.group(1).strip().lower().replace(" ", "_")
            metadata["work_id"] = work_id
    
    # Period from content
    period_match = re.search(r"Period:\s*(Q\d?\s*\d{4}|[A-Za-z]+\s+\d{4})", content)
    if period_match:
        metadata["period"] = period_match.group(1).strip()
    
    # Platform from content
    platform_match = re.search(r"(Spotify|Apple\s*Music|YouTube|TikTok|Amazon\s*Music)", content, re.IGNORECASE)
    if platform_match:
        platform = platform_match.group(1).strip().lower().replace(" ", "_")
        metadata["platform"] = platform
    
    # ISRC
    isrc_match = re.search(r"ISRC:\s*([A-Z0-9-]+)", content)
    if isrc_match:
        metadata["isrc"] = isrc_match.group(1).strip()
    
    # ISWC
    iswc_match = re.search(r"ISWC:\s*([A-Z0-9-]+)", content)
    if iswc_match:
        metadata["iswc"] = iswc_match.group(1).strip()
    
    # Royalty type for statements
    if doc_type == "royalty_statement":
        mech_match = re.search(r"Mechanical Revenue:\s*\$([\d,]+\.?\d*)", content)
        if mech_match:
            metadata["mechanical_revenue"] = mech_match.group(1).replace(",", "")
        
        total_match = re.search(r"Gross Revenue:\s*\$([\d,]+\.?\d*)", content)
        if total_match:
            metadata["gross_revenue"] = total_match.group(1).replace(",", "")
        
        net_match = re.search(r"NET PAYMENT:\s*\$([\d,]+\.?\d*)", content)
        if net_match:
            metadata["net_payment"] = net_match.group(1).replace(",", "")
        
        streams_match = re.search(r"Total Streams:\s*([\d,]+)", content)
        if streams_match:
            metadata["total_streams"] = streams_match.group(1).replace(",", "")
    
    # Parties for split sheets
    parties = []
    party_pattern = re.compile(r"^\s*([A-Za-z\s&.\-]+?)\s*[|/]\s*(\d+(?:\.\d+)?)\s*%(.*)$", re.MULTILINE)
    for match in party_pattern.finditer(content):
        name = match.group(1).strip()
        share = float(match.group(2))
        parties.append({"name": name, "share": share})
    
    if parties:
        metadata["parties"] = [p["name"] for p in parties]
        metadata["total_share"] = sum(p["share"] for p in parties)
    
    return metadata


def ingest_file(
    filepath: Path,
    chunker: LegalFinancialChunker,
    embedder: EmbeddingService,
    store: VectorStoreManager,
    config: Settings,
) -> dict:
    """Ingest a single file into the vector store."""
    filename = filepath.name
    doc_type = determine_doc_type(filepath)
    
    logger.info(f"Processing: {filename} (type: {doc_type})")
    
    # Read content
    content = filepath.read_text(encoding="utf-8")
    if not content.strip():
        logger.warning(f"  Skipped empty file: {filename}")
        return {"success": False, "reason": "empty file"}
    
    # Extract metadata
    metadata = extract_metadata_from_content(filepath, doc_type, content)
    work_id = metadata.get("work_id", "unknown")
    
    # Chunk document
    chunks = chunker.chunk_document(
        text=content,
        doc_type=doc_type,
        source_filename=filename,
        work_id=work_id,
    )
    
    if not chunks:
        logger.warning(f"  No chunks generated for {filename}")
        return {"success": False, "reason": "no chunks"}
    
    # Prepare documents for storage
    # Use filename in ID to avoid collisions across different files
    # (e.g., golden_hour_spotify_q1 and golden_hour_apple_music_q1
    #  would both have ID golden_hour_royalty_statement_0 otherwise)
    doc_id_prefix = filename.replace(".pdf.txt", "").replace(" ", "_").replace("-", "_")
    
    documents = []
    for i, (chunk_text, chunk_meta) in enumerate(chunks):
        doc_meta = {
            "doc_type": chunk_meta.doc_type or doc_type,
            "source_filename": filename,
            "work_id": work_id,
            "chunk_index": i,
            "created_at": str(time.time()),
        }
        
        # Add extracted metadata
        for key, value in metadata.items():
            doc_meta[key] = value
        
        # Add chunk-specific metadata
        if chunk_meta.platform:
            doc_meta["platform"] = chunk_meta.platform
        if chunk_meta.royalty_type:
            doc_meta["royalty_type"] = chunk_meta.royalty_type
        if chunk_meta.period_start:
            doc_meta["period_start"] = chunk_meta.period_start
        if chunk_meta.parties:
            doc_meta["parties"] = chunk_meta.parties
        
        # Embed the chunk
        try:
            embedding = embedder.embed_text(chunk_text, truncate=True)
        except Exception as e:
            logger.error(f"  Embedding failed for {filename}: {e}")
            continue
        
        documents.append({
            "id": f"{doc_id_prefix}_chunk_{i}",
            "content": chunk_text,
            "embedding": embedding,
            "metadata": doc_meta,
        })
    
    # Upsert into store
    if documents:
        store.add_documents(documents)
        logger.info(f"  ✓ Added {len(documents)} chunks for {filename}")
    
    return {
        "success": True,
        "filename": filename,
        "doc_type": doc_type,
        "chunks": len(documents),
        "metadata": metadata,
    }


async def run_population():
    """Main ingestion pipeline populating both ChromaDB and SQLite DB."""
    project_root = Path(__file__).parent.parent
    
    # Initialize components
    config = Settings()
    init_db()
    
    embedder = EmbeddingService(
        base_url=config.openai_base_url,
        api_key=config.openai_api_key,
        model=config.embedding_model,
        dimension=config.embedding_dimension,
    )
    
    vector_store_path = str(project_root / "data" / "vectorstore")
    store = VectorStoreManager(store_path=vector_store_path)
    store.initialize()
    
    ingestion_service = DocumentIngestionService(
        settings=config,
        embedder=embedder,
        store=store,
    )
    
    # Get data directory
    data_dir = project_root / "data"
    royalty_dir = data_dir / "royalties"
    split_dir = data_dir / "splitsheets"
    contract_dir = data_dir / "contracts"
    
    # Collect all files
    files = []
    for dir_path in [royalty_dir, split_dir, contract_dir]:
        if dir_path.exists():
            files.extend(dir_path.rglob("*.pdf.txt"))
            files.extend(dir_path.rglob("*.csv"))
    
    if not files:
        logger.error(f"No .pdf.txt or .csv files found in {data_dir}")
        sys.exit(1)
    
    logger.info(f"Found {len(files)} files to ingest")
    logger.info(f"Embedding model: {config.embedding_model} ({config.embedding_dimension} dims)")
    logger.info(f"Vector store: {vector_store_path}")
    logger.info(f"Relational DB: {config.database_url}")
    
    results = []
    start_time = time.time()
    
    with Session(engine) as db_session:
        for i, filepath in enumerate(sorted(files), 1):
            try:
                content = filepath.read_bytes()
                result = await ingestion_service.ingest_file(
                    file_path=str(filepath),
                    file_name=filepath.name,
                    file_data=content,
                    db_session=db_session,
                )
                results.append({
                    "success": result.chunks_created > 0,
                    "filename": filepath.name,
                    "chunks": result.chunks_created,
                    "works": result.works_found,
                })
                logger.info(f"[{i}/{len(files)}] ✓ {filepath.name} ({result.chunks_created} chunks, works: {result.works_found})")
            except Exception as e:
                logger.error(f"[{i}/{len(files)}] ✗ {filepath.name}: {e}")
                results.append({"success": False, "filename": filepath.name, "error": str(e)})
    
    elapsed = time.time() - start_time
    
    # Summary
    success_count = sum(1 for r in results if r.get("success"))
    total_chunks = sum(r.get("chunks", 0) for r in results if r.get("success"))
    store_stats = store.get_stats()
    
    logger.info("\n" + "=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Files processed: {len(results)}")
    logger.info(f"Successfully ingested: {success_count}/{len(results)}")
    logger.info(f"Total chunks: {total_chunks}")
    logger.info(f"Time elapsed: {elapsed:.1f}s")
    logger.info(f"Vector store: {store_stats}")
    logger.info(f"Embedder cache: {embedder.get_stats()}")
    logger.info("=" * 60)


def main():
    asyncio.run(run_population())


if __name__ == "__main__":
    main()

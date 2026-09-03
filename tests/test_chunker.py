import pytest
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.rag.chunker import LegalFinancialChunker


def test_chunker_initialization():
    chunker = LegalFinancialChunker(chunk_size=512, chunk_overlap=64)
    assert chunker.chunk_size == 512
    assert chunker.chunk_overlap == 64


def test_chunk_split_sheet():
    chunker = LegalFinancialChunker(chunk_size=512, chunk_overlap=64)
    text = """
    DOCUMENT: Split Sheet - Test Song
    WORK: Test Song
    ISRC: US1234567890
    
    PARTIES:
    | Alice Smith | 60.0% | Writer |
    | Bob Jones   | 40.0% | Producer |
    
    Total Share: 100.0%
    """
    chunks = chunker.chunk_document(
        text=text,
        doc_type="split_sheet",
        source_filename="test_split.pdf.txt",
        work_id="test_song",
    )
    assert len(chunks) >= 1
    content, meta = chunks[0]
    assert "Alice Smith" in content
    assert meta.doc_type == "split_sheet"
    assert meta.work_title == "Test Song"


def test_chunk_royalty_statement():
    chunker = LegalFinancialChunker(chunk_size=512, chunk_overlap=64)
    text = """
    ROYALTY STATEMENT - SPOTIFY
    Period: Q1 2024
    Work: Test Track
    Gross Revenue: $1,250.00
    NET PAYMENT: $1,000.00
    Total Streams: 350,000
    """
    chunks = chunker.chunk_document(
        text=text,
        doc_type="royalty_statement",
        source_filename="test_spotify.pdf.txt",
    )
    assert len(chunks) >= 1
    content, meta = chunks[0]
    assert "Spotify" in meta.platform.capitalize()
    assert meta.period_start == "Q1 2024"


def test_chunk_empty_document():
    chunker = LegalFinancialChunker(chunk_size=512, chunk_overlap=64)
    chunks = chunker.chunk_document(
        text="",
        doc_type="general",
        source_filename="empty.txt",
    )
    # Empty documents produce either 0 chunks or 1 header-only chunk
    assert len(chunks) <= 1


def test_chunk_unstructured_large_text():
    chunker = LegalFinancialChunker(chunk_size=100, chunk_overlap=20)
    # Create multiple paragraphs to trigger chunking across paragraph boundaries
    long_text = "\n\n".join(["Paragraph " + str(p) + " " + " ".join([f"word_{i}" for i in range(50)]) for p in range(5)])
    chunks = chunker.chunk_document(
        text=long_text,
        doc_type="general",
        source_filename="long_text.txt",
    )
    assert len(chunks) > 1
    for content, meta in chunks:
        assert isinstance(content, str)
        assert meta.doc_type == "general"




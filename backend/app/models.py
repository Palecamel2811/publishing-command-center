"""
Pydantic models for the Publishing & Rights Command Center.
Defines all data contracts between frontend and backend.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ───────────────────────────────────────────────────────────────────

class RoyaltyType(str, Enum):
    MECHANICAL = "mechanical"
    PERFORMANCE = "performance"
    SYNCHRONIZATION = "sync"
    NEIGHBORING_RIGHTS = "neighboring_rights"
    PRINT = "print"
    OTHER = "other"


class Platform(str, Enum):
    SPOTIFY = "spotify"
    APPLE_MUSIC = "apple_music"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    AMAZON_MUSIC = "amazon_music"
    DEEZER = "deezer"
    PANDORA = "pandora"
    OTHER = "other"


class PRO(str, Enum):
    ASCAP = "ascap"
    BMI = "bmi"
    SESAC = "sesac"
    GEMA = "gema"
    PRS = "prs"
    SOCAN = "socan"
    OTHER = "other"


class SplitShareType(str, Enum):
    PUBLISHER_SHARE = "publisher"
    SONGWRITER_SHARE = "writer"
    MASTER_RIGHTS = "master"
    PRODUCER_SHARE = "producer"


class DocumentType(str, Enum):
    SPLIT_SHEET = "split_sheet"
    ROYALTY_STATEMENT = "royalty_statement"
    LICENSE_CONTRACT = "license_contract"
    SYNC_AGREEMENT = "sync_agreement"
    DSP_REPORT = "dsp_report"
    PRO_STATEMENT = "pro_statement"
    OTHER = "other"


class QueryIntent(str, Enum):
    ROYALTY_QUERY = "royalty_query"
    RIGHT_LOOKUP = "right_lookup"
    RECONCILIATION = "reconciliation"
    FORECAST = "forecast"
    SPLIT_QUERY = "split_query"
    CONTRACT_QUERY = "contract_query"
    ANALYSIS = "analysis"
    GENERAL = "general"



# ── Core Domain Models ──────────────────────────────────────────────────────

class Work(BaseModel):
    """A musical composition / work entry."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=1, max_length=500)
    isrc: Optional[str] = None  # International Standard Recording Code
    iswc: Optional[str] = None  # International Standard Musical Work Code
    upc: Optional[str] = None
    label: Optional[str] = None
    album: Optional[str] = None
    release_date: Optional[datetime] = None
    genre: Optional[str] = None
    iswc_t: Optional[bool] = False  # ISWC-tagged work
    status: str = "active"  # active, inactive, disputed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Split(BaseModel):
    """A publishing split for a work."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    work_id: str
    party_name: str = Field(..., min_length=1, max_length=200)
    share_percentage: float = Field(..., ge=0.0, le=100.0)
    share_type: SplitShareType = SplitShareType.SONGWRITER_SHARE
    pro: Optional[PRO] = None
    admin_publisher: Optional[str] = None
    sub_publisher: Optional[str] = None
    iswc_verified: bool = False
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RoyaltyEntry(BaseModel):
    """A single royalty payment/recording."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    work_id: str
    platform: Platform
    royalty_type: RoyaltyType
    period_start: datetime
    period_end: datetime
    gross_amount: float = Field(..., ge=0.0)
    fees_deducted: float = Field(default=0.0, ge=0.0)
    net_amount: float = Field(..., ge=0.0)
    currency: str = "USD"
    source_document: Optional[str] = None
    confidence_score: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SyncLicense(BaseModel):
    """A sync licensing agreement."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    work_id: str
    title: str = Field(..., min_length=1)
    licensee: str = Field(..., min_length=1)
    media_type: str  # film, tv, commercial, video_game, etc.
    territory: Optional[str] = None
    term_start: Optional[datetime] = None
    term_end: Optional[datetime] = None
    fee: float = Field(..., ge=0.0)
    currency: str = "USD"
    is_exclusive: bool = False
    is_buyout: bool = False
    status: str = "active"  # active, expired, pending
    contract_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── RAG / Document Models ──────────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    """Metadata for an ingested document chunk."""
    doc_id: str
    doc_type: DocumentType
    source_filename: str
    work_id: Optional[str] = None
    platform: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    page_number: Optional[int] = None
    confidence: Optional[float] = None
    chunk_index: int = 0


class DocumentChunk(BaseModel):
    """A chunk from an ingested document."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str = Field(..., min_length=1)
    metadata: DocumentMetadata
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IngestResult(BaseModel):
    """Result of a document ingestion."""
    document_id: str
    chunks_created: int
    works_found: list[str]
    splits_found: list[dict[str, Any]]
    royalties_found: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)


# ── Query Models ────────────────────────────────────────────────────────────

class RAGQuery(BaseModel):
    """A query to the RAG system."""
    query: str = Field(..., min_length=1, max_length=2000)
    filters: Optional[dict[str, Any]] = None
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    include_raw_chunks: bool = True
    intent: Optional[QueryIntent] = None


class RAGResponse(BaseModel):
    """Response from a RAG query."""
    query: str
    response: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    intent: Optional[QueryIntent] = None
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    follow_up_suggestions: list[str] = Field(default_factory=list)
    latency_ms: int = 0


# ── Dashboard / Analytics Models ────────────────────────────────────────────

class RoyaltySummary(BaseModel):
    """Aggregated royalty summary."""
    total_gross: float = 0.0
    total_net: float = 0.0
    total_fees: float = 0.0
    count: int = 0
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    by_platform: dict[str, float] = Field(default_factory=dict)
    by_type: dict[str, float] = Field(default_factory=dict)
    by_work: dict[str, float] = Field(default_factory=dict)


class DashboardData(BaseModel):
    """Full dashboard data payload."""
    summary: RoyaltySummary
    recent_royalties: list[dict[str, Any]]
    works: list[dict[str, Any]]
    sync_licenses: list[dict[str, Any]]
    reconciliation_status: dict[str, Any]
    pending_splits: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    revenue_trend: list[dict[str, Any]]


# ── Auth Models ─────────────────────────────────────────────────────────────

class User(BaseModel):
    id: str
    email: str
    name: str
    role: str = "user"  # admin, publisher, songwriter, producer
    created_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User

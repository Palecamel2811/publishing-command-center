from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from uuid import uuid4, UUID


# ── Base Model ──────────────────────────────────────────────────────────────

class ModelBase(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


# ── Work ────────────────────────────────────────────────────────────────────

class Work(ModelBase, table=True):
    __tablename__ = "works"

    title: str = Field(index=True, max_length=500)
    isrc: Optional[str] = Field(default=None, index=True)
    iswc: Optional[str] = Field(default=None, index=True)
    label: Optional[str] = None
    status: str = Field(default="active", max_length=50)
    total_earnings: float = Field(default=0.0)

    splits: List["Split"] = Relationship(back_populates="work", cascade_delete=True)
    royalties: List["RoyaltyEntry"] = Relationship(back_populates="work", cascade_delete=True)
    sync_licenses: List["SyncLicense"] = Relationship(back_populates="work", cascade_delete=True)


# ── Split ───────────────────────────────────────────────────────────────────

class Split(ModelBase, table=True):
    __tablename__ = "splits"

    work_id: UUID = Field(foreign_key="works.id", ondelete="CASCADE")
    party_name: str = Field(index=True, max_length=200)
    share_percentage: float = Field(ge=0.0, le=100.0)
    share_type: str = Field(default="songwriter_share", max_length=50)
    pro: Optional[str] = None
    notes: Optional[str] = None

    work: Work = Relationship(back_populates="splits")


# ── Royalty Entry ───────────────────────────────────────────────────────────

class RoyaltyEntry(ModelBase, table=True):
    __tablename__ = "royalty_entries"

    work_id: UUID = Field(foreign_key="works.id", ondelete="CASCADE")
    platform: str = Field(index=True, max_length=50)
    royalty_type: str = Field(max_length=50)
    period_start: str = Field(index=True)
    period_end: str = Field(index=True)
    gross_amount: float
    fees_deducted: float = Field(default=0.0)
    net_amount: float
    currency: str = Field(default="USD", max_length=10)
    source_document: Optional[str] = None

    work: Work = Relationship(back_populates="royalties")


# ── Sync License ────────────────────────────────────────────────────────────

class SyncLicense(ModelBase, table=True):
    __tablename__ = "sync_licenses"

    work_id: UUID = Field(foreign_key="works.id", ondelete="CASCADE")
    title: str
    licensee: str = Field(index=True, max_length=200)
    media_type: str = Field(max_length=100)
    territory: Optional[str] = None
    term_start: Optional[str] = None
    term_end: Optional[str] = None
    fee: float
    currency: str = Field(default="USD", max_length=10)
    status: str = Field(default="active", max_length=50)

    work: Work = Relationship(back_populates="sync_licenses")


# ── Document Chunk (links to both vector and relational DB) ────────────────

class DocumentChunk(ModelBase, table=True):
    __tablename__ = "document_chunks"

    doc_id: str = Field(index=True)
    doc_type: str = Field(index=True, max_length=50)
    source_filename: str
    content: str
    work_title: Optional[str] = None
    chunk_index: int
    parties: Optional[str] = None  # JSON string of list[str]
    confidence: Optional[float] = None

"""
Configuration management for the Publishing & Rights Command Center.
Uses pydantic-settings for type-safe env var loading with defaults.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ConfigDict

# Resolve .env path relative to project root
# __file__ = backend/app/config.py
# parent.parent.parent = project root
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env
    )

    # ── LLM / Embedding ────────────────────────────────────────────────────
    openai_base_url: str = "http://127.0.0.1:8787/v1"
    openai_api_key: str = "sk-local-dev"
    llm_model: str = "qwen35-9b"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # ── Vector Store ───────────────────────────────────────────────────────
    vector_store_path: str = "./data/vectorstore"
    vector_store_type: str = "chroma"

    # ── Application ────────────────────────────────────────────────────────
    app_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    secret_key: str = "change-me-in-production"
    debug: bool = False

    # ── RAG Configuration ─────────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5
    score_threshold: float = 0.3

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./publishing.db"

    @property
    def resolved_vector_store_path(self) -> str:
        """Resolve vector store path consistently regardless of CWD."""
        p = Path(self.vector_store_path)
        if p.is_absolute() and p.exists():
            return str(p)
        # Check relative to cwd
        if p.exists():
            return str(p.resolve())
        # Check project root data dir
        root_data = _PROJECT_ROOT / "data" / "vectorstore"
        return str(root_data.resolve())

    @property
    def resolved_database_url(self) -> str:
        """Resolve database URL consistently regardless of CWD."""
        if self.database_url.startswith("sqlite:///"):
            raw_path = self.database_url.replace("sqlite:///", "")
            p = Path(raw_path)
            if p.is_absolute() and p.exists():
                return f"sqlite:///{p}"
            if p.exists():
                return f"sqlite:///{p.resolve()}"
            # Check project root publishing.db
            root_db = _PROJECT_ROOT / "publishing.db"
            return f"sqlite:///{root_db.resolve()}"
        return self.database_url

    @property
    def is_local_llm(self) -> bool:
        """Detect if we're running against a local endpoint."""
        return "127.0.0.1" in self.openai_base_url or "localhost" in self.openai_base_url


settings = Settings()

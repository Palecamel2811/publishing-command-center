# Publishing & Rights Command Center — State

## Status
**100% Functional MVP Complete** — Backend, Frontend, Vector Store, SQLite Database, and Ingestion Pipeline fully connected and verified.

## Architecture
- **Backend**: FastAPI + Python 3.11, SQLModel / SQLite (`publishing.db`), ChromaDB vector store (`data/vectorstore`), Ollama LLM (`qwen2.5-coder:14b`) + Embeddings (`nomic-embed-text`, 768 dims)
- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind CSS, Recharts, Framer Motion, TanStack Query
- **RAG Pipeline**: Domain-aware legal/financial chunking → Embedding cache → ChromaDB → BM25 + Vector Hybrid Search (0.7 dense / 0.3 sparse) → Query Routing & LLM synthesis with citations
- **Reconciliation Engine**: Automated cross-platform comparison, streaming rate sanity checks, split verification, severity-rated discrepancy reporting
- **Relational Layer**: Full SQLModel persistence for `Work`, `Split`, `RoyaltyEntry`, `SyncLicense`, and `DocumentChunk` with CSV export endpoints

## Completed Features
- ✅ **Backend API & Data Layer**:
  - Instant startup (<1s) with lazy evaluation loading
  - Dynamic dashboard analytics (`/api/dashboard`) with period revenue trending
  - Real-time filtered royalty queries (`/api/dashboard/royalties`)
  - Full CRUD & list endpoints for works (`/api/works`) and sync licenses (`/api/sync-licenses`)
  - Multi-format file ingestion (`/api/ingest/batch`) with database history (`/api/ingest/history`)
  - CSV report exports (`/api/reports/export`) for royalties, works, and sync licenses
- ✅ **Frontend UI**:
  - Interactive Dashboard with live KPI cards, platform revenue breakdown, and trend charts
  - Rights Visualizer (`frontend/components/rights-visualizer.tsx`) with split breakdown & sync license cards
  - Audit & Reconciliation Reports (`frontend/components/reports.tsx`) with live CSV export
  - Ingestion Hub with multi-file drag-and-drop, progress tracking, and batch processing
  - Interactive RAG Assistant with natural language queries, document citations, and confidence scoring
  - Glassmorphic dark fintech aesthetic with keyboard navigation (⌘B, ⌘K, 1-5)
- ✅ **Sample Data & Test Suite**:
  - Sample dataset (68 documents) populated into ChromaDB (261 chunks) and SQLite `publishing.db`
  - Automated pytest test suite in `tests/` covering chunking, hybrid search, reconciliation, and all API endpoints (13/13 passing)

## Running the Application
```bash
# Backend (Port 8000)
cd backend && python -m app.main

# Frontend (Port 3000)
cd frontend && npm run dev

# Run Automated Test Suite
python3 -m pytest tests/

# Re-populate Sample Data
python3 scripts/populate_sample_data.py
```

## Architecture & System Map
See [ARCHITECTURE_MAP.md](file:///Users/theartisluv/projects/publishing-command-center/ARCHITECTURE_MAP.md) for the complete building blocks map, Mermaid data flow diagrams, and technology stack breakdown.

## Future Upgrades & Roadmap
See [FUTURE_ROADMAP.md](file:///Users/theartisluv/projects/publishing-command-center/FUTURE_ROADMAP.md) for the prioritized feature roadmap, architectural enhancements, and low-risk evaluation milestones.

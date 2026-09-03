# Publishing & Rights Command Center — Architecture & Building Blocks Map

A complete structural map of the technology stack, data flows, and architectural building blocks that power the Publishing & Rights Command Center.

---

## 🏗️ System Architecture Overview

```mermaid
flowchart TD
    subgraph Client ["Client Layer (Vercel)"]
        UI["Next.js 14 App Router (TypeScript)"]
        Dashboard["Dashboard & Recharts"]
        SSEConsumer["SSE Token Streamer"]
        DocViewer["In-App PDF / DOCX Viewer"]
        MobileNav["Mobile Bottom App Bar"]
    end

    subgraph API ["Backend API Layer (Heroku)"]
        FastAPI["FastAPI REST Server (Python 3.11)"]
        CORS["CORS Middleware"]
        SSEEngine["StreamingResponse SSE Engine"]
        Router["Query Intent Router"]
    end

    subgraph DataEngine ["Ingestion & Audit Engine"]
        Parsers["Parsers (pypdf, python-docx, openpyxl, pandas)"]
        Chunker["LegalFinancialChunker (Domain Regex)"]
        Reconciler["Reconciliation Audit Engine"]
    end

    subgraph RAG ["Hybrid RAG & Vector Intelligence"]
        ChromaDB[("ChromaDB Vector Store (Dense)")]
        BM25["Okapi BM25 Index (Sparse Keyword)"]
        HybridSearch["Hybrid Score Fusion (70% Dense / 30% Sparse)"]
        EmbedCache["In-Memory LRU Embedding Cache"]
    end

    subgraph Storage ["Relational Database"]
        SQLite[("SQLModel / SQLite (publishing.db)")]
        Models["Work | Split | RoyaltyEntry | SyncLicense | DocumentChunk"]
    end

    subgraph CloudAI ["Cloud AI Layer (Microsoft Azure)"]
        AzureOpenAI["Azure OpenAI Service (gpt-4.1-mini)"]
    end

    %% Connections
    UI -->|HTTPS / REST| FastAPI
    SSEConsumer <-->|SSE Stream (<200ms)| SSEEngine
    FastAPI --> DataEngine
    DataEngine --> Chunker
    DataEngine --> SQLite
    Chunker --> ChromaDB
    FastAPI --> Router
    Router --> HybridSearch
    HybridSearch --> ChromaDB
    HybridSearch --> BM25
    Router -->|Prompt + Context| AzureOpenAI
    AzureOpenAI -->|Token Stream| SSEEngine
```

---

## 🧩 Building Blocks Breakdown

### 1. 🖥️ Frontend & UI Layer (`Vercel`)
* **Next.js 14 App Router:** React 18 client & server components with TypeScript for type-safe rendering.
* **Tailwind CSS & Glassmorphism:** Custom dark-mode fintech aesthetic with dynamic viewport sizing (`h-[100dvh]`) for locked vertical mobile scrolling.
* **Recharts Visualization:** Interactive Area, Bar, and Pie charts with custom dark tooltips and line cursors.
* **Framer Motion:** Smooth page transitions, animated modal overlays, and loading indicators.
* **TanStack React Query:** Asynchronous data fetching, stale-time caching, and automatic refetching.
* **SSE Stream Consumer:** Native JavaScript `fetch()` Reader parsing Server-Sent Event streams (`event: sources`, `event: token`, `event: done`).
* **Mobile-Native UX:** Dedicated mobile bottom navigation bar (`Dashboard`, `AI Query`, `Assets`, `Rights Map`, `Reports`).

---

### 2. ⚡ Backend API Layer (`Heroku`)
* **FastAPI (Python 3.11):** High-performance asynchronous Python web framework.
* **Uvicorn ASGI Server:** Asynchronous request handling and SSE streaming; horizontal/process concurrency is configured at deployment.
* **CORS Middleware:** Multi-origin security configuration allowing cross-domain communication between Vercel and Heroku.
* **StreamingResponse (SSE Engine):** Low-latency token streaming via Server-Sent Events (SSE), with Time-to-First-Token monitored as an operational metric.

---

### 3. 📄 Document Ingestion & Parsing Engine (`ingestion.py`)
* **Multi-Format Parsers:** `pypdf`, `python-docx`, `openpyxl`, `pandas`, `chardet`.
* **Domain-Aware `LegalFinancialChunker`:** Regex-based boundary detection optimized for music publishing:
  - *Split Sheet Strategy:* Atomic party-share row preservation (never cuts names from percentages).
  - *Royalty Statement Strategy:* Period and platform table row grouping.
  - *Contract Strategy:* Legal clause boundary alignment (`Article`, `Clause`, `§`).
* **Resilience Engine:** Graceful zero-vector fallback protecting relational database insertion if cloud vector endpoints encounter network hiccups.

---

### 4. 🧠 Hybrid Search & RAG Intelligence (`rag/`)
* **Dense Vector Search:** ChromaDB vector database storing 768-dim embeddings.
* **Sparse Keyword Search:** Custom in-memory Okapi BM25 index for exact match matching (ISRCs, work titles, party names).
* **Hybrid Score Fusion:** Combines 70% Dense Similarity + 30% Sparse BM25 Keyword matching with metadata filtering (`doc_type`, `work_title`, `period`, `platform`).
* **Query Router & Embedding Cache:** Fast-path regex query classification + in-memory LRU embedding cache.

---

### 5. 🤖 Cloud AI & LLM Engine (`Microsoft Azure`)
* **Azure OpenAI Service:** Enterprise cloud hosting running **`gpt-4.1-mini`**.
* **Low-Variance Generation (`temperature=0.0`):** `temperature=0.0` is used to improve consistency for factual, document-grounded responses; deterministic calculations remain in application code.
* **System Guardrails:** Strict prompt constraints forcing the model to cite exact document sources.

---

### 6. 🗄️ Relational Data & Audit Layer (`publishing.db`)
* **SQLModel & SQLite:** Type-safe Python ORM managing relational entities:
  - `Work` (Composition titles, ISRCs, ISWCs)
  - `Split` (Writer/Publisher share percentages & PRO affiliations)
  - `RoyaltyEntry` (Distributor payout line items, gross/net amounts, platforms)
  - `SyncLicense` (Film/TV/Ad sync licensing terms and media fees)
  - `DocumentChunk` (Indexed chunk tracking and file history)
* **Reconciliation Engine (`reconciliation.py`):** Automated discrepancy scoring algorithm checking contract split compliance against distributor streaming payouts.

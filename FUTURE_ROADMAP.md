# Publishing & Rights Command Center — Future Upgrades Roadmap

This document outlines prioritized, high-ROI future upgrades for the Publishing & Rights Command Center. Upgrades are categorized by architectural layer, ROI, technical risk, and strict implementation priority.

---

## 🎯 Phase 1: Immediate High-ROI Upgrades (Short Term / Low Risk)

These upgrades refine precision, data validation, and UI resilience without breaking existing pipelines.

### 1. RAG Precision & Evaluation Benchmarks
- **Cross-Encoder Re-Ranking**: Implement a lightweight cross-encoder (e.g. `bge-reranker-small`) to re-rank top-10 hybrid search candidates down to the top-3 before LLM prompt injection.
- **Adaptive Confidence Thresholding**: Dynamically filter out retrieved chunks scoring below a tuned relevance cutoff (e.g. `< 0.45`) to prevent hallucinations on obscure queries.
- **RAG Evaluation Framework (Ragas / TruLens)**: Integrate automated RAG evaluation metrics measuring faithfulness, answer relevance, and context recall per query.
- **Citation Precision Highlighting**: Return line numbers or snippet offsets in RAG citations so users can jump directly to the exact line in the document previewer modal.

### 2. Expanded Document Parsers & Multi-Format Ingestion
- **Native PDF Table Extractor**: Integrate `pdfplumber` or `pypdf` native tabular parsers for complex multi-column PDF royalty statements.
- **Scanned PDF OCR Pipeline**: Tesseract OCR fallback for physical split sheet scans or signed agreements that lack digital text layers.
- **Direct Excel (`.xlsx`) Import**: Column mapping for multi-tab distributor royalty reports (e.g., Kobalt, Sony Music Publishing, ASCAP/BMI statements).

### 3. Frontend Error Boundaries & Skeletal States
- **React Error Boundaries**: Component-level error catch blocks around chart rendering and chat streaming to prevent full-page crashes.
- **Skeletal Loading Animations**: Custom shimmer loading skeletons for dashboard cards and table rows while async data resolves.

---

## 🚀 Phase 2: Domain, Memory & Query Routing Upgrades (Medium Term)

Features that expand analytical intelligence, memory, and query routing capabilities.

### 1. Text-to-SQL / Function Calling Query Router (High Priority)
- **Structured Query Translation**: Implement a Text-to-SQL intent router pass. Mathematical and quantitative aggregation questions (*"What were total royalties for Sauce in Q1?"*) are translated into direct SQL queries against `publishing.db`, while semantic policy/contract questions (*"What are the sync terms?"*) route to Hybrid RAG.
- **Deterministic Financial Guardrails**: Enforce database record lineage for all LLM mathematical outputs to eliminate generated or hallucinated sums.

### 2. Multi-Turn Conversational Memory
- **Regex Fast-Pass Pronoun Resolution**: Detect ambiguous pronouns (*"it"*, *"that song"*, *"those splits"*) and use a fast query condenser to reformulate follow-up questions into standalone queries without vector drift.
- **Rolling 2-Turn Context Buffer**: Maintain a lean 2-turn memory window to preserve chat context while protecting context windows.
- **Entity Reset Safeguards**: Automatically clear previous song/contract context whenever a user explicitly introduces a new song title.

### 3. Audit & Reconciliation Engine
- **Automated Discrepancy Alerting**: Push notifications / UI badge warnings when calculated royalty rates deviate from contract terms by > 5%.
- **PRO Split Registration Checker**: Cross-reference internal split sheets against ASCAP / BMI public database APIs to flag unregistered works or missing rightsholder shares.
- **Multi-Currency Conversion Engine**: Real-time currency exchange rates for international territory earnings (GBP, EUR, JPY to USD).

---

## 🔬 Phase 3: Enterprise Cloud Architecture & Scaling (Longer Term)

Enterprise architectural patterns required to deploy multi-tenant SaaS or scale to massive catalog sizes (>100,000 documents).

### 1. Managed Cloud PostgreSQL + `pgvector` Migration (High Priority)
- **Eliminating Ephemeral SQLite**: Migrate `publishing.db` from Heroku ephemeral SQLite to a managed PostgreSQL cloud database (Heroku Postgres, Supabase, or AWS RDS).
- **Unified Vector & Full-Text Search**: Offload vector embeddings to `pgvector` and BM25 sparse keyword search to PostgreSQL `tsvector` / GIN indexes, solving multi-worker index fragmentation.

### 2. SQLGate Enterprise Database Management
- **SQLGate Direct Management Adapter**: Connect SQLGate to local SQLite and production cloud PostgreSQL for visual data auditing, query profiling, and schema management.
- **High-Volume B-Tree Indexing**: Database indexing on `isrc`, `work_id`, `period_start`, and `platform` columns for sub-10ms query execution on catalogs exceeding 100,000 entries.
- **Bulk Audit Package Exporter**: Custom multi-table JOIN export routines generating formatted Excel (`.xlsx`), JSON, and PDF audit packages.

### 3. Production Multi-Tenancy & Row-Level Security (RBAC)
- **Row-Level Security (RLS)**: Enforce `tenant_id == current_user.org_id` metadata filtering on both SQL and vector search layers in ChromaDB/PostgreSQL.
- **Role-Based Access Control (RBAC)**: Admin, Royalty Manager, and Rightsholder view permissions.

---

## 🚫 Deferred / High-Fragility Approaches (Evaluated & Excluded)

- **Word-Level Context Compression (e.g. Headroom / LLMLingua)**: Trimming/compressing words from retrieved chunks carries a high risk of numerical corruption (dropping rightsholder share percentages, altering streaming decimals like `$0.00385`, or truncating period dates). Re-ranking and adaptive thresholding provide far safer token optimization for financial/legal data.
- **LLM-Based Semantic Segmentation During Ingestion**: Avoid calling an LLM for chunk boundary detection during document upload. Introduces high API cost, latency, rate limit risks, and lower reliability than domain-aware regex parsing on structured financial files.

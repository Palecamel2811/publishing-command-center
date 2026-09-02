# Publishing & Rights Command Center — Future Upgrades Roadmap

This document outlines prioritized, high-ROI future upgrades for the Publishing & Rights Command Center. Upgrades are categorized by architectural layer, ROI, and technical risk.

---

## 🎯 Phase 1: High-ROI / Low-Risk Enhancements (Completed / Immediate Next Steps)

These upgrades add significant value to system observability and precision without introducing fragile dependencies or breaking existing pipelines.

### 1. RAG & Retrieval Observability & Precision
- **Cross-Encoder Re-Ranking**: Implement a lightweight cross-encoder (e.g. `bge-reranker-small`) to re-rank top-10 hybrid search candidates down to the top-3 before LLM prompt injection. Higher precision than text compression.
- **Adaptive Confidence Thresholding**: Dynamically filter out retrieved chunks scoring below a tuned relevance cutoff (e.g. `< 0.45`) to prevent hallucinations on obscure queries.
- **Query & Chunk Retrieval Logging**: Log retrieved chunks, BM25 vs Vector scores, and final LLM prompt context to SQLite/JSON log files. Allows empirical inspection of retrieval quality per user query.
- **Structured JSON Summaries**: Pre-extract structured JSON metadata (rates, dates, rightsholders) during ingestion for instant query answers without raw prompt stuffing.
- **Citation Precision Highlighting**: Return line numbers or snippet offsets in RAG citations so users can jump directly to the exact line in the document previewer modal.

### 2. Expanded Document Parsers & Multi-Format Ingestion
- **Native PDF Table Extractor**: Integrate `pdfplumber` or `pypdf` native tabular parsers for complex multi-column PDF royalty statements.
- **Scanned PDF OCR Pipeline**: Optional Tesseract OCR fallback for legacy physical split sheet scans or signed agreements that lack digital text layers.
- **Direct Excel (`.xlsx`) Import**: Direct column mapping for multi-tab distributor royalty reports (e.g., Kobalt, Sony Music Publishing, ASCAP/BMI statements).

---

## 🚀 Phase 2: Domain, Memory & Analytical Upgrades (Medium Term)

Features that expand business capabilities for music publishing and multi-industry domain adaptations.

### 1. Multi-Turn Conversational Memory & Query Reformulation
- **Regex Fast-Pass Pronoun Resolution**: Detect ambiguous pronouns (*"it"*, *"that song"*, *"those splits"*) and use a fast query condenser to reformulate follow-up questions into standalone vector search queries without hallucination risk.
- **Rolling 2-Turn Context Buffer**: Maintain a lean 2-turn memory window to preserve chat context while protecting local model VRAM and API context windows.
- **Entity Reset Safeguards**: Automatically clear previous song/contract context whenever a user explicitly introduces a new song title or rightsholder name.

### 2. Audit & Reconciliation Engine
- **Automated Discrepancy Alerting**: Push notifications / UI badge warnings when calculated royalty rates deviate from contract terms by > 5%.
- **PRO Split Registration Checker**: Cross-reference internal split sheets against ASCAP / BMI public database APIs to flag unregistered works or missing rightsholder shares.
- **Multi-Currency Conversion Engine**: Real-time currency exchange rates for international territory earnings (GBP, EUR, JPY to USD).

### 3. UI & User Experience
- **In-App Interactive Split Sheet Builder**: Visual drag-and-drop rightsholder pie chart editor for creating and exporting signed PDF split sheets.
- **Batch Export PDF Reports**: Generate executive summary PDF reports for audit findings, complete with branded charts and discrepancy tables.
- **Saved Custom Date & Period Views**: Allow users to save custom date range presets (e.g. "2024 Audit Period", "Q3 2024").

---

## 🔬 Phase 3: Advanced RAG & Multi-Tenancy Architecture (Longer Term)

Advanced architectural patterns to deploy if scaling to multi-tenant SaaS or handling massive catalog sizes (>100,000 documents).

### 1. Hierarchical Parent/Child Chunking
- **Parent/Child Indexing**: Store fine-grained child chunks (128 tokens) for vector similarity search alongside parent context blocks (1024 tokens) for LLM synthesis.
- **Use Case**: Best for lengthy legal contracts where specific sub-clauses need tight embedding matching without losing overall section context.

### 2. Production Multi-Tenancy & Enterprise Auth
- **Multi-Tenant Data Isolation**: Organization-level workspace boundaries in SQLite/PostgreSQL and ChromaDB tenant namespaces.
- **Role-Based Access Control (RBAC)**: Admin, Royalty Manager, and Rightsholder view permissions.
- **Cloud Vector Store Migration**: Seamless adapter to migrate ChromaDB to Pinecone, Qdrant, or PGVector for cloud deployment.

---

## 🚫 Deferred / High-Fragility Approaches (Evaluated & Excluded)

- **Word-Level Context Compression (e.g. Headroom / LLMLingua)**: Trimming/compressing words from retrieved chunks carries a high risk of numerical corruption (dropping rightsholder share percentages, altering streaming decimals like `$0.00385`, or truncating period dates). Re-ranking and adaptive thresholding provide far safer token optimization for financial/legal data.
- **LLM-Based Semantic Segmentation During Ingestion**: Avoid calling an LLM for chunk boundary detection during document upload. Introduces high API cost, latency, rate limit risks, and lower reliability than domain-aware regex parsing on structured financial files.

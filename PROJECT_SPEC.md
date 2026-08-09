# Project Specification: CatalogIQ

**CatalogIQ** is an AI-powered Product Intelligence and Catalog Enrichment Platform for industrial commerce. It transforms incomplete, unstructured, or scattered industrial product information (PDFs, images, CSVs, SKUs) into commerce-ready, validated, confidence-scored product records.

---

## 1. Core Architecture

The system uses a modular monolithic architecture with background workers:

```
                  ┌──────────────────────┐
                  │   React Front-end    │
                  └──────────┬───────────┘
                             │ REST API
                             ▼
                  ┌──────────────────────┐
                  │    FastAPI Server    │
                  └────┬───────────┬─────┘
                       │           │
           PostgreSQL  │           │  Redis Queue
     (Source of Truth) │           │  (Celery)
                       ▼           ▼
             ┌───────────┐   ┌───────────┐
             │ Postgres  │   │  Worker   │◄───┐
             └───────────┘   └─────┬─────┘    │ Caching /
                                   │          │ Queue
                                   ├──────────┘
                                   │
                                   ▼
                             ┌───────────┐
                             │ Qdrant Vector
                             │ Database  │
                             └───────────┘
```

---

## 2. Ingestion & Extraction Workflow

1. **Ingest**: ZIP, PDFs, Images, CSVs, manual entries.
2. **Parse**: Extract raw texts/tables (Docling/PaddleOCR abstraction).
3. **Extract**: Structured JSON mapping to product schemas using LLMs (OpenAI/Ollama).
4. **Validate**: Clean dimensions, check required fields, flag cross-source conflicts.
5. **Enrich**: Generate commerce description, SEO tags, categories.
6. **Vector Search & Duplicate Detection**: Embedding storage in Qdrant; match products using cosine similarity.
7. **Human-in-the-Loop**: Catalog managers review, verify, and resolve issues.

---

## 3. Core Database Models (Phase 1)

- **Product**: Relational metadata, status, quality score, dynamic attribute JSONB.
- **Document**: Original file info, SHA-256 hash, paths.
- **ProcessingJob**: Job-level status tracker (queued, completed, failed, total).
- **ProcessingStep**: Granular stage tracking (parsing, extracting, validating, etc.).

---

## 4. Phase-by-Phase Roadmap

* **Phase 1: Foundations** (Docker environment, health checks, storage abstraction, migrations, API route skeleton, frontend boilerplate).
* **Phase 2: Ingestion & Jobs Queue** (Upload flow, Celery jobs, processing status polling).
* **Phase 3: Parsing & AI Extraction** (Docling/OCR services, LLM JSON extraction).
* **Phase 4: Validation & Confidence Engine** (Rules engine, attribute-level confidence).
* **Phase 5: AI Enrichment & Catalog Metrics** (Commerce summaries, SEO data, quality scoring).
* **Phase 6: Search & Vector DB** (Qdrant client, similar matching, duplicates).
* **Phase 7: Human Review & Interactive Copilot** (Dashboard controls, LLM context-aware copilot).
* **Phase 8: Tests, Demo Data & Polishing** (Synthetic dataset, styling).

# CatalogIQ — Enterprise AI Product Intelligence & Catalog Enrichment Platform

**CatalogIQ** is an enterprise-grade, multi-source AI product intelligence and catalog enrichment system. It transforms unstructured industrial product documentation (PDF datasheets, spec sheets, high-resolution product images, catalog archives, and multi-source supplier feeds) into structured, normalized, confidence-scored product attributes with trace evidence provenance and multi-source entity resolution.

---

## 🌟 Key Features & Core Workspaces

### 1. 📊 Operational Overview Dashboard (`/`)
- Real-time catalog summary metrics: **Total Products**, **Documents Processed**, **Active Processing Jobs**, **Review Backlog**, **Catalog Quality Score**, and **Verification Rate**.
- Live activity feed showing document processing stages, recent products, and catalog quality alerts.

### 2. ⚡ Multi-Stage Ingestion & AI Processing Pipeline (`/upload`, `/jobs`)
- **Multimodal Ingestion**: Supports single/bulk PDFs, PNG/JPG images, and multi-file ZIP archives.
- **Multimodal OCR & Layout Analysis**: Structured text extraction, layout parsing, table extraction, and image region extraction.
- **LLM Attribute Extraction**: Contextual extraction of technical industrial attributes (e.g. rated power, voltage, enclosure rating, duty cycle).
- **Confidence Scoring Engine**: Multi-factor scoring (0–100) combining base extraction signals, evidence verification bonuses, normalization success, and source trust multipliers.
- **Evidence Provenance Grounding**: Verbatim evidence snippet extraction with page numbers, document source linking, and bounding boxes.

### 3. 🔍 Semantic Vector Search & Catalog Discovery (`/search`, `/catalog`)
- **Hybrid Search**: Dense vector search via Qdrant vector database combined with structured database filtering (brand, category, SKU, attributes, confidence).
- **FastEmbed & OpenAI Embedding Providers**: Production-grade embedding factory supporting local FastEmbed models and remote OpenAI vector embeddings.
- **Product Intelligence Dashboard**: Complete product view displaying extracted attributes, evidence provenance, raw vs normalized values, and document attachments.

### 4. 🔀 Multi-Source Reconciliation & Entity Resolution (Phase 7)
- **Multi-Source Ingestion**: Merges competing product data claims across manufacturer PDF datasheets, distributor sheets, supplier CSV feeds, and web catalogs.
- **Level 1 & Level 2 Entity Resolution**: SKU normalization, brand matching, model string similarity, and candidate deduplication.
- **Cross-Source Conflict Detection**: Identifies value discrepancies across competing sources, establishes canonical winning values based on source trust levels, and preserves all historical claims.

### 5. 🛡️ Human Review & Resolution Workspace (`/reviews`)
- **Human Review Queue**: Operational workspace for reviewing open validation issues, low-confidence extractions (<75%), missing mandatory attributes, and cross-source conflicts.
- **Source Claim Comparison & Resolution**: Inspects competing claim A vs claim B side-by-side with document quotes, page numbers, and trust scores.
- **Source-Aware Actions**: `Accept Source A Claim`, `Accept Source B Claim`, or `Set Custom Value` with full audit trail logging and quality score recalculation.
- **Idempotency & Conflict Guarding**: Re-submitting identical decisions returns clean idempotency status; conflicting decision changes return HTTP 409 Conflict.

### 6. 🩺 Catalog Health & Quality Intelligence Dashboard (`/health`)
- **Authoritative Quality Scoring**: Overall Catalog Quality Score (`AVG(Product.quality_score)`), Verification Rate, Completeness Rate, and Evidence Coverage %.
- **Product Status Breakdown**: Verified, Needs Review, and Draft distributions with interactive stacked progress visualizer.
- **Category & Brand Health Tables**: SQL-aggregated quality breakdown, verification rates, completeness %, open issue counts, and conflict counts.
- **Products Needing Attention Queue**: Top 10 at-risk products prioritized by `needs_review` status, cross-source conflicts, quality score risk, and open issues.
- **Lowest Quality Products Ranking**: Bottom 10 products sorted by persisted `quality_score ASC`.

---

## 🛠️ Technology Stack

### Backend
- **Framework**: Python 3.11, FastAPI, Pydantic 2.x
- **Database & ORM**: PostgreSQL (Authoritative Source of Truth), SQLModel, SQLAlchemy 2.0, Alembic
- **Vector Database**: Qdrant Vector Search
- **Caching & Queues**: Redis, Celery background workers
- **AI & Embedding Providers**: Qdrant FastEmbed, OpenAI API, Ollama (local LLMs), PyTorch, HuggingFace Transformers

### Frontend
- **Framework**: React 18, Vite, TypeScript
- **State & Data Fetching**: TanStack Query (React Query v5), React Router v6
- **Styling**: Tailwind CSS (Dark Navy Industrial Theme), Lucide Icons

---

## 🏗️ Architecture & Pipeline Flow

```
                                    +-----------------------+
                                    |  Unstructured Docs    |
                                    | (PDF, Images, ZIPs)   |
                                    +-----------+-----------+
                                                |
                                                v
                                    +-----------------------+
                                    |  Ingestion & Storage  |
                                    +-----------+-----------+
                                                |
                                                v
                                    +-----------------------+
                                    |  OCR & Layout Engine  |
                                    +-----------+-----------+
                                                |
                                                v
                                    +-----------------------+
                                    | LLM Attribute Extract |
                                    +-----------+-----------+
                                                |
                                                v
                                    +-----------------------+
                                    |  Confidence & Quality |
                                    |    Scoring Engine     |
                                    +-----------+-----------+
                                                |
                                                v
                                    +-----------------------+
                                    | Multi-Source Reconcil |
                                    |  & Entity Resolution  |
                                    +-----------+-----------+
                                                |
                                                v
                                    +-----------------------+
                                    | PostgreSQL Data Store |
                                    | & Qdrant Vector Index |
                                    +-----------+-----------+
                                                |
       +----------------------------------------+----------------------------------------+
       |                                        |                                        |
       v                                        v                                        v
+--------------+                         +--------------+                         +--------------+
| Overview &   |                         |  Reviews &   |                         |  Catalog     |
| Dashboard    |                         |  Resolution  |                         |  Health      |
+--------------+                         +--------------+                         +--------------+
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 18+
- **Docker & Docker Compose**: Installed and running

---

### 1. Clone & Setup Environment

```bash
git clone https://github.com/parikshiths27/Catalog_iq.git
cd Catalog_iq
```

Copy the example environment file:
```bash
cp .env.example .env
```

---

### 2. Start Infrastructure Containers

Start PostgreSQL, Redis, and Qdrant via Docker Compose:
```bash
docker compose up -d
```

---

### 3. Backend Setup & Run

1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run database migrations:
   ```bash
   alembic upgrade head
   ```
5. Launch FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   - Interactive API Docs (Swagger UI): `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

---

### 4. Frontend Setup & Run

1. Open a new terminal and navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start Vite development server:
   ```bash
   npm run dev
   ```
   - Access web app: `http://localhost:5173`

---

## 📡 Key REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/overview/summary` | Live overview dashboard KPIs, activity feed, and summaries |
| `GET` | `/api/v1/health/catalog` | Strictly read-only catalog health, status breakdown, category/brand quality, and attention queue |
| `GET` | `/api/v1/reviews` | Paginated review backlog queue with issue filters, evidence quotes, and competing claims |
| `POST` | `/api/v1/products/{product_id}/validation/{validation_id}/resolve` | Source-aware human issue resolution (`accept_source_a`, `accept_source_b`, `custom_value`) |
| `GET` | `/api/v1/products` | Paginated catalog product list with status/category/brand filters |
| `GET` | `/api/v1/products/{id}` | Detailed Product Intelligence view with attributes, evidence, and documents |
| `GET` | `/api/v1/products/{id}/reconciliation` | Phase 7 multi-source reconciliation, candidate matches, and winning claim details |
| `POST` | `/api/v1/search` | Hybrid semantic vector search & structured filter query endpoint |
| `POST` | `/api/v1/documents/upload` | Multimodal document upload (PDF, Images, ZIP) |

---

## 🧪 Testing & Quality Assurance

### Backend Pytest Suite
Run full backend test suite:
```powershell
$env:PYTHONPATH="backend"; backend\venv\Scripts\python.exe -m pytest backend/tests -v
```

Run specific test modules:
```powershell
$env:PYTHONPATH="backend"; backend\venv\Scripts\python.exe -m pytest backend/tests/test_catalog_health_api.py backend/tests/test_reviews_api.py backend/tests/test_overview_api.py -v
```

### Frontend TypeScript Verification
Run static type check:
```bash
cd frontend
npx tsc --noEmit
```

---

## 🏷️ Release Tag Milestones

- `catalog-health-complete`: Complete Catalog Health Dashboard & read-only API implementation.
- `reviews-complete`: Complete Reviews & Human Resolution Workspace.
- `phase-7-complete`: Multi-source intelligence, cross-source conflict detection, and entity resolution.
- `phase-6-complete`: Hybrid semantic vector search with Qdrant.
- `phase-5-complete`: Multi-factor confidence scoring & evidence provenance grounding.

---

## 📄 License

CatalogIQ is proprietary software built for enterprise industrial catalog intelligence.

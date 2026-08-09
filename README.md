# CatalogIQ - AI-powered Product Intelligence Platform

CatalogIQ is an enterprise-grade AI Product Intelligence and Catalog Enrichment Platform. It transforms unstructured industrial product documents (datasheets, images, bulk zip archives) into structured, validated, confidence-scored product attributes with trace evidence.

---

## 🛠️ Tech Stack & Services

- **Backend**: FastAPI, SQLModel (SQLAlchemy 2.x), Pydantic 2.x, Celery (Redis)
- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Databases & Queues**: PostgreSQL (Source of Truth), Redis (Queue/Cache), Qdrant (Vector Embeddings)
- **Storage**: Local Storage (dev) & S3-compatible interfaces (prod)

---

## 🚀 Local Development Setup

### 1. Start External Services
Ensure Docker is installed and running. Start the PostgreSQL, Redis, and Qdrant services using:
```bash
docker compose up -d
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` in the root folder and fill in the necessary keys (such as `OPENAI_API_KEY` or LLM choices):
```bash
cp .env.example .env
```

### 3. Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS/Linux**:
     ```bash
     python -m venv venv
     source venv/bin/activate
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations to initialize the database:
   ```bash
   alembic upgrade head
   ```
5. Start the FastAPI backend server:
   ```bash
   uvicorn app.main:app --reload
   ```
   The API documentation will be available at `http://localhost:8000/docs`.

### 4. Frontend Setup
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The application will be accessible at `http://localhost:5173`.

---

## 🧪 Verification & Testing

To run the backend test suite, execute the following from the `backend/` directory with the virtual environment activated:
```bash
pytest
```
This checks API endpoints, health indicators, database connectivity, and mock components.

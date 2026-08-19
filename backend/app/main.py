import os
os.environ["TORCH_COMPILE_DISABLE"] = "1"

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.health import router as health_router
from app.api.v1.products import router as products_router
from app.api.v1.documents import router as documents_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.search import router as search_router
from app.api.v1.overview import router as overview_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.auth import router as auth_router
from app.api.v1.unilog import router as unilog_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create all tables (including the new users table) on startup
    from app.db.session import engine
    from sqlmodel import SQLModel
    from app.models.user import User  # Ensure class registration
    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        import logging
        logging.warning(f"Database table setup: {e}")

    if settings.PROCESSING_MODE.lower() == "celery":
        # Celery is opt-in for deployments that provide Redis and a real worker.
        import threading

        def start_celery_worker():
            try:
                from app.workers.celery_app import celery_app
                worker = celery_app.Worker(concurrency=2, loglevel="INFO")
                worker.start()
            except Exception as err:
                import logging
                logging.warning(f"Embedded worker startup notice: {err}")

        t = threading.Thread(target=start_celery_worker, daemon=True)
        t.start()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="CatalogIQ AI-powered Product Intelligence and Catalog Enrichment Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS for local development (can be locked down in production via settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers under /api/v1 prefix
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(products_router, prefix="/api/v1", tags=["Products"])
app.include_router(documents_router, prefix="/api/v1", tags=["Documents"])
app.include_router(jobs_router, prefix="/api/v1", tags=["Jobs"])
app.include_router(search_router, prefix="/api/v1", tags=["Search"])
app.include_router(overview_router, prefix="/api/v1", tags=["Overview"])
app.include_router(reviews_router, prefix="/api/v1", tags=["Reviews"])
app.include_router(unilog_router, prefix="/api/v1/unilog", tags=["Unilog"])

@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/docs",
        "version": "1.0.0"
    }

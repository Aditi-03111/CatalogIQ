from typing import Dict, Any
from fastapi import APIRouter, Depends, status
from sqlmodel import Session, text
import redis
from qdrant_client import QdrantClient
from app.db.session import get_session
from app.core.config import settings

router = APIRouter(prefix="/health")

@router.get("/live", status_code=status.HTTP_200_OK)
def check_live() -> Dict[str, str]:
    """
    Simple backend liveness check.
    """
    return {"status": "ok", "message": "CatalogIQ Backend is live"}

@router.get("/ready", status_code=status.HTTP_200_OK)
def check_ready(session: Session = Depends(get_session)) -> Dict[str, Any]:
    """
    Checks connection readiness for PostgreSQL, Redis, and Qdrant.
    If a service is degraded, the response remains 200 but marks status as degraded.
    """
    postgres_status = "unhealthy"
    redis_status = "unhealthy"
    qdrant_status = "unhealthy"
    is_degraded = False

    # 1. Verify PostgreSQL
    try:
        session.execute(text("SELECT 1"))
        postgres_status = "healthy"
    except Exception as e:
        postgres_status = f"unhealthy: {str(e)}"
        is_degraded = True

    # 2. Verify Redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        if redis_client.ping():
            redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
        is_degraded = True

    # 3. Verify Qdrant
    try:
        qdrant_client = QdrantClient(url=settings.QDRANT_URL, timeout=2.0)
        # Attempt to list collections as a connectivity ping
        qdrant_client.get_collections()
        qdrant_status = "healthy"
    except Exception as e:
        qdrant_status = f"unhealthy: {str(e)}"
        is_degraded = True

    return {
        "status": "degraded" if is_degraded else "healthy",
        "services": {
            "postgresql": postgres_status,
            "redis": redis_status,
            "qdrant": qdrant_status
        }
    }

import os
os.environ["TORCH_COMPILE_DISABLE"] = "1"

from celery import Celery
from app.core.config import settings

# Initialize Celery app instance named catalogiq
celery_app = Celery(
    "catalogiq",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks.document_processing"]
)

# Apply standard Celery configurations, loading concurrency limits and UTC timezones
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=settings.WORKER_CONCURRENCY,
    task_track_started=True,
    # Graceful timeout configurations
    task_time_limit=300,       # 5 minutes absolute limit
    task_soft_time_limit=180   # 3 minutes soft limit
)

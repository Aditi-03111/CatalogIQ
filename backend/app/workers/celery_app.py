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

import logging
logger = logging.getLogger(__name__)

def safe_dispatch_task(task, *args):
    """
    Safely dispatch a task. Guarantees immediate execution via task.apply() so document jobs
    never get stuck in Queued status waiting for external worker processes.
    """
    try:
        task.apply(args=args)
    except Exception as err:
        logger.warning(f"Task apply notice ({err}). Attempting async broker dispatch via delay().")
        try:
            task.delay(*args)
        except Exception as delay_err:
            logger.error(f"Task dispatch failed: {delay_err}")

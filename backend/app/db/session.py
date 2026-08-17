import os
import logging
from typing import Generator
from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
if ("localhost:5432" in db_url or "127.0.0.1:5432" in db_url) and not os.getenv("DATABASE_URL"):
    db_url = "sqlite:///./catalogiq.db"

try:
    connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
    engine = create_engine(
        db_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args
    )
    with engine.connect() as conn:
        pass
except Exception as err:
    logger.warning(f"Database connection to {db_url} failed ({err}). Falling back to SQLite.")
    db_url = "sqlite:///./catalogiq.db"
    engine = create_engine(db_url, echo=False, future=True, connect_args={"check_same_thread": False})

def get_session() -> Generator[Session, None, None]:
    """
    Dependency helper to yield database sessions for requests.
    """
    with Session(engine) as session:
        yield session

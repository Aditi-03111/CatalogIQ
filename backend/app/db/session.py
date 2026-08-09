from typing import Generator
from sqlmodel import create_engine, Session
from app.core.config import settings

# Create database engine with SQLAlchemy 2.0 behaviors enabled
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True  # Detect stale connections
)

def get_session() -> Generator[Session, None, None]:
    """
    Dependency helper to yield database sessions for requests.
    """
    with Session(engine) as session:
        yield session

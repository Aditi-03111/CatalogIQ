import os
import pytest
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import event

# Setup database dynamically: load from environment or fall back to SQLite
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///file:testdb?mode=memory&cache=shared&uri=true")

@pytest.fixture(name="session")
def session_fixture():
    connect_args = {}
    if TEST_DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False, "uri": True}
        
    engine = create_engine(TEST_DATABASE_URL, connect_args=connect_args)
    
    # Enable foreign keys in SQLite to enforce ON DELETE CASCADE constraints
    if TEST_DATABASE_URL.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

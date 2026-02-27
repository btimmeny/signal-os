"""Shared test fixtures — uses SQLite for fast in-memory testing."""

import os
import uuid

import pytest
from sqlalchemy import create_engine, event, StaticPool
from sqlalchemy.orm import sessionmaker

# Force test config before any app imports
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AGENT_API_KEY"] = "test-key"

from app.db import Base, get_db  # noqa: E402
from app.models import Commitment, Reminder  # noqa: E402, F401 — register models
from app.main import app  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

# Single shared engine with StaticPool so all threads see the same in-memory DB
_engine = create_engine(
    "sqlite://",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(scope="function")
def db_session():
    """Create tables, yield a session, then drop everything."""
    Base.metadata.create_all(bind=_engine)
    TestingSession = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client wired to the test DB session."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


HEADERS = {"X-API-Key": "test-key"}

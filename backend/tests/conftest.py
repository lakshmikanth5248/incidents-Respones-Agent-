"""
Pytest Test Fixtures and Configuration.
Conforms to PRD §17 Testing Strategy.
Sets up isolated in-memory test database, test client, and helper utilities.
"""

import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.data.database import Base, get_db
from src.data.models.incident import Incident
from src.main import create_app

# SQLite in-memory engine with StaticPool so all connections share the same memory instance
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh database session for each test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Provides a FastAPI TestClient wired to the in-memory test database."""
    app = create_app()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def count_incidents(db_session):
    """Helper to query the count of incident records in the database."""
    def _count() -> int:
        return db_session.query(Incident).count()
    return _count


@pytest.fixture(scope="function")
def reset_memory_double():
    """Ensure test double is initialized and injected before test, and reset after."""
    from src.memory.service import memory_service
    from src.memory.test_double import HindsightTestDouble
    double = HindsightTestDouble(bank_id="test-bank")
    memory_service.set_client(double)
    yield double
    double.reset()


"""
Pytest Test Fixtures and Configuration.
Conforms to PRD §17 Testing Strategy.
Sets up isolated in-memory test database, test client, and helper utilities.
"""

import os
import sys
from typing import List
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
from src.data.models.postmortem import PostMortem
from src.data.models.postmortem import utcnow
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


@pytest.fixture
def confirmed_postmortem_incident(client, db_session):
    """
    Factory producing incidents that satisfy the retention preconditions of API-012:
    the incident exists, is resolved, and its post-mortem is confirmed (FR-056, FR-058).

    `confirm_via_api=False` applies the draft -> confirmed transition directly on the
    post-mortem row instead of calling API-011. The confirmation endpoint is owned by
    Feature 12, so driving retention tests through it would couple this suite to
    another feature's implementation. Use the direct transition when the test only
    needs a post-mortem in the confirmed state; the tests that assert the confirmation
    gate itself still use ``confirmed_postmortem=True`` (client flag) and
    ``confirm_postmortem=False`` (stored state) to exercise it.

    Usage:
        inc_id = confirmed_postmortem_incident()
        inc_id = confirmed_postmortem_incident(root_cause="connection pool leak")
        inc_id = confirmed_postmortem_incident(confirm_postmortem=False)  # draft only
    """
    created: List[str] = []

    def _make(
        symptom_description: str = (
            "Payment API returning HTTP 500. "
            "HikariPool-1 - Connection is not available, request timed out after 30000ms."
        ),
        service: str = "payment-api",
        environment: str = "production",
        severity: str = "critical",
        root_cause: str = "Database connection pool exhaustion caused by a leaked connection",
        outcome: str = "successful",
        resolve: bool = True,
        generate_postmortem: bool = True,
        confirm_postmortem: bool = True,
        confirm_via_api: bool = False,
    ) -> str:
        r = client.post("/api/incidents", json={
            "symptom_description": symptom_description,
            "service": service,
            "environment": environment,
            "severity": severity,
        })
        assert r.status_code == 201, r.text
        incident_id = r.json()["id"]
        created.append(incident_id)

        if resolve:
            res = client.post(f"/api/incidents/{incident_id}/resolve", json={
                "actions": [
                    "Rolled back payment-api deployment to v2.4.0",
                    "Terminated stale backend database connections",
                ],
                "runbook_id": "RB-PAY-001",
                "runbook_version": "1.2.0",
                "contributing_factors": [
                    "Traffic spike during flash sale",
                    "Connection pool limit left at the default of 10",
                ],
                "root_cause": root_cause,
                "result": "Latency recovered to under 120ms, error rate dropped to 0.01%",
                "outcome": outcome,
            })
            assert res.status_code == 200, res.text

        if generate_postmortem:
            pm = client.post(f"/api/incidents/{incident_id}/postmortem", json={})
            assert pm.status_code == 200, pm.text

        if confirm_postmortem:
            if confirm_via_api:
                cm = client.post(f"/api/incidents/{incident_id}/postmortem/confirm", json={})
                assert cm.status_code == 200, cm.text
                assert cm.json()["status"] == "confirmed"
            else:
                postmortem = (
                    db_session.query(PostMortem)
                    .filter(PostMortem.incident_id == incident_id)
                    .first()
                )
                assert postmortem is not None, "expected a post-mortem draft to confirm"
                postmortem.status = "confirmed"
                postmortem.reviewed_by = "sre-lead"
                postmortem.confirmed_at = utcnow()
                db_session.query(Incident).filter(
                    Incident.id == incident_id
                ).first().postmortem_status = "confirmed"
                db_session.commit()

        return incident_id

    yield _make


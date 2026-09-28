"""
Integration test verifying live connectivity to the running Vectorize Hindsight service on port 8888.
Tests:
1. Health check against live Hindsight endpoint
2. Live recall against 'incident-response-bank'
3. MemoryService normalization of live Hindsight records
4. Live retain to Hindsight bank
5. End-to-end incident analysis using live Hindsight recall
"""

import pytest
from fastapi.testclient import TestClient
from src.config import settings
from src.memory.client import HindsightClient
from src.memory.service import MemoryService, memory_service
from src.memory.schemas import RecallRequest, RetainRequest, MemoryCandidate, MemoryStatus, EntryType, OutcomeLabel
from src.main import create_app
from src.data.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
def _is_hindsight_live() -> bool:
    try:
        client = HindsightClient(
            base_url=settings.HINDSIGHT_ENDPOINT,
            bank_id=settings.HINDSIGHT_BANK_ID,
            timeout=1.0,
            max_retries=0,
        )
        healthy, _ = client.health_check()
        return healthy
    except Exception:
        return False

pytestmark = pytest.mark.skipif(
    not _is_hindsight_live(),
    reason="Live Hindsight service on port 8888 is not running. Start it to run live tests."
)


def test_live_hindsight_health():
    client = HindsightClient(
        base_url=settings.HINDSIGHT_ENDPOINT,
        bank_id=settings.HINDSIGHT_BANK_ID,
    )
    is_healthy, msg = client.health_check()
    assert is_healthy is True, f"Live Hindsight should be healthy, got: {msg}"
    assert msg == "connected"


def test_live_hindsight_recall_raw():
    client = HindsightClient(
        base_url=settings.HINDSIGHT_ENDPOINT,
        bank_id=settings.HINDSIGHT_BANK_ID,
    )
    res = client.recall(query="database connection pool exhaustion", limit=5)
    assert "results" in res or "memories" in res
    items = res.get("results") or res.get("memories") or []
    assert len(items) > 0, "Expected at least 1 memory returned from live bank"
    first_item = items[0]
    assert "text" in first_item or "body" in first_item


def test_live_hindsight_memory_service_recall():
    client = HindsightClient(
        base_url=settings.HINDSIGHT_ENDPOINT,
        bank_id=settings.HINDSIGHT_BANK_ID,
    )
    svc = MemoryService(client=client)

    req = RecallRequest(
        query="database connection pool exhaustion",
        service="checkout-service",
        limit=5,
    )
    recall_result = svc.recall(req)
    assert recall_result.memory_status == MemoryStatus.OK
    assert recall_result.total_found > 0
    assert len(recall_result.entries) > 0

    top_entry = recall_result.entries[0]
    assert top_entry.body != ""
    print(f"\n[LIVE RECALL TEST PASSED] Successfully recalled {len(recall_result.entries)} memories from Hindsight bank '{settings.HINDSIGHT_BANK_ID}'!")
    print(f"Top entry ID: {top_entry.entry_id}, Source Incident: {top_entry.source_incident_ref}")


def test_live_hindsight_retain():
    client = HindsightClient(
        base_url=settings.HINDSIGHT_ENDPOINT,
        bank_id=settings.HINDSIGHT_BANK_ID,
    )
    svc = MemoryService(client=client)

    candidate = MemoryCandidate(
        entry_type=EntryType.RESOLUTION_PROCEDURE.value,
        service="checkout-service",
        component="postgres",
        body="Scaled down analytics batch workers and doubled pgpool connections to 300 to clear connection saturation.",
        outcome_label=OutcomeLabel.SUCCESSFUL.value,
        confidence="confirmed",
        source_incident_ref="INC-LIVE-TEST-001",
    )
    retain_req = RetainRequest(
        incident_id="INC-LIVE-TEST-001",
        entries=[candidate],
        confirmed=True,
    )
    res = svc.retain(retain_req)
    assert res.status == "retained"
    assert len(res.results) == 1
    assert res.results[0].status == "retained"
    print(f"\n[LIVE RETAIN TEST PASSED] Successfully retained memory candidate into Hindsight bank '{settings.HINDSIGHT_BANK_ID}'!")


def test_live_incident_analysis_pipeline():
    # Setup test DB
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()

    app = create_app()
    def override_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_db

    # Inject live Hindsight client into singleton memory_service
    live_client = HindsightClient(
        base_url=settings.HINDSIGHT_ENDPOINT,
        bank_id=settings.HINDSIGHT_BANK_ID,
    )
    memory_service.set_client(live_client)

    with TestClient(app) as test_client:
        # Create incident
        create_res = test_client.post("/api/incidents", json={
            "service": "checkout-service",
            "environment": "production",
            "symptom_description": "HTTP 504 Gateway Timeout on checkout API with postgres database connection pool saturation.",
        })
        assert create_res.status_code == 201
        inc_id = create_res.json()["id"]

        # Run analysis (full pipeline: interpret -> recall -> compare -> hypothesize)
        analyze_res = test_client.post(f"/api/incidents/{inc_id}/analyze", json={"stage": "hypothesize"})
        assert analyze_res.status_code == 200
        analysis = analyze_res.json()

        assert analysis["incident_id"] == inc_id
        assert analysis["memory_status"] == "ok"
        assert "recall_record" in analysis
        assert analysis["recall_record"]["returned_entries"] is not None
        assert len(analysis["recall_record"]["returned_entries"]) > 0

        # Check comparisons and hypotheses
        assert "comparisons" in analysis
        assert len(analysis["comparisons"]) > 0
        assert "hypotheses" in analysis
        assert len(analysis["hypotheses"]) > 0

        print(f"\n[END-TO-END PIPELINE PASSED] Incident '{inc_id}' analyzed with live Hindsight memory layer!")
        print(f"Memory Status: {analysis['memory_status']}")
        print(f"Recalled memories count: {len(analysis['recall_record']['returned_entries'])}")
        print(f"Top hypothesis: {analysis['hypotheses'][0]['hypothesis']}")

    Base.metadata.drop_all(bind=engine)

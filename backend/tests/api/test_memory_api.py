"""
API Integration Tests for Memory Endpoints.
Conforms to PRD §12.3 (API-011, API-012, API-013, API-014), API-007, and API-016.
Tests the isolated memory integration layer through HTTP API interfaces.
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.memory.service import memory_service
from src.memory.test_double import HindsightTestDouble
from src.memory.schemas import EntryType, OutcomeLabel, ConfidenceLevel




# --------------------------------------------------------------------------
# API-011: POST /api/memory/recall
# --------------------------------------------------------------------------

def test_api_recall_success(client: TestClient, reset_memory_double: HindsightTestDouble):
    """Test successful memory recall via API-011."""
    reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "payment-api",
        "body": "Database deadlock on account ledger rows during concurrent debit transactions.",
        "outcome_label": "successful",
        "confidence": "confirmed",
        "source_incident_ref": "inc-001",
    })

    payload = {
        "query": "Database deadlock ledger concurrent debit",
        "service": "payment-api",
        "limit": 5,
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["memory_status"] == "ok"
    assert data["total_found"] >= 1
    assert len(data["entries"]) >= 1
    entry = data["entries"][0]
    assert entry["service"] == "payment-api"
    assert entry["entry_type"] == "root_cause"
    assert "deadlock" in entry["body"].lower()
    assert "relevance_score" in entry
    assert "relevance_basis" in entry


def test_api_recall_empty(client: TestClient):
    """Test empty memory recall (cold start) via API-011."""
    payload = {
        "query": "Non-existent system failure",
        "service": "new-microservice",
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["memory_status"] == "empty"
    assert data["entries"] == []
    assert data["total_found"] == 0


def test_api_recall_unavailable(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test recall failure when Hindsight is unavailable via API-011.
    Must return HTTP 503 HINDSIGHT_UNAVAILABLE, NEVER an empty success list!
    """
    reset_memory_double.set_mode("unavailable")

    payload = {
        "query": "Connection timeout",
        "service": "payment-api",
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 503

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "HINDSIGHT_UNAVAILABLE"
    assert data["error"]["retryable"] is True


def test_api_recall_validation_empty_query(client: TestClient):
    """Test recall request with empty query and no service is rejected with 422."""
    payload = {
        "query": "   ",
        "service": None,
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 422


# --------------------------------------------------------------------------
# API-012: POST /api/memory/retain
#
# Feature 13 gates retention on a confirmed post-mortem, so these tests drive
# the real lifecycle. See tests/api/test_memory_retain.py for the full matrix.
# --------------------------------------------------------------------------

def test_api_retain_success(client, reset_memory_double, confirmed_postmortem_incident):
    """Test memory retention via API-012."""
    inc_id = confirmed_postmortem_incident()
    payload = {
        "incident_id": inc_id,
        "confirmed": True,
        "entries": [
            {
                "entry_type": "root_cause",
                "service": "auth-service",
                "component": "token-verifier",
                "body": "JWKS cache TTL was set to 0 causing endpoint rate limiting.",
                "outcome_label": "successful",
                "confidence": "confirmed",
                "source_incident_ref": inc_id,
            },
            {
                "entry_type": "resolution_procedure",
                "service": "auth-service",
                "body": "Updated JWKS cache TTL to 3600 seconds in ConfigMap and rolled pods.",
                "outcome_label": "successful",
                "confidence": "confirmed",
                "source_incident_ref": inc_id,
            }
        ]
    }
    response = client.post("/api/memory/retain", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "retained"
    assert len(data["results"]) == 2
    assert all(r["status"] == "retained" for r in data["results"])


def test_api_retain_unconfirmed_rejected(client, reset_memory_double, confirmed_postmortem_incident):
    """Test retention without explicit confirmation is rejected with 409 Conflict."""
    inc_id = confirmed_postmortem_incident()
    payload = {
        "incident_id": inc_id,
        "confirmed": False,
        "entries": [
            {
                "entry_type": "root_cause",
                "service": "orders",
                "body": "Redis evictions caused session loss",
                "source_incident_ref": inc_id,
            }
        ]
    }
    response = client.post("/api/memory/retain", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "CONFLICT"


def test_api_retain_secret_detected_rejected(client, reset_memory_double, confirmed_postmortem_incident):
    """Test candidate containing a secret token is blocked with 422 pre-write."""
    inc_id = confirmed_postmortem_incident()
    payload = {
        "incident_id": inc_id,
        "confirmed": True,
        "entries": [
            {
                "entry_type": "root_cause",
                "service": "orders",
                "body": "Secret key api_key = AKIAIOSFODNN7EXAMPLE used in config",
                "source_incident_ref": inc_id,
            }
        ]
    }
    response = client.post("/api/memory/retain", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "SECRET_DETECTED"


# --------------------------------------------------------------------------
# API-013 & API-014: Experience browsing & Flagging
# --------------------------------------------------------------------------

def test_api_browse_experience(client: TestClient, reset_memory_double: HindsightTestDouble):
    """Test browsing experiences via API-013."""
    reset_memory_double.seed_entries([
        {
            "entry_type": "root_cause",
            "service": "billing",
            "body": "Tax rate API returned 500 error",
            "source_incident_ref": "inc-201",
        },
        {
            "entry_type": "lesson",
            "service": "billing",
            "body": "Always configure circuit breaker for 3rd party tax services",
            "source_incident_ref": "inc-201",
        }
    ])

    response = client.get("/api/memory/experience?service=billing")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["entries"]) == 2


def test_api_flag_experience(client: TestClient, reset_memory_double: HindsightTestDouble):
    """Test flagging an experience record via API-014."""
    mem_id = reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "database",
        "body": "Postgres vacuum freeze stall",
        "source_incident_ref": "inc-301",
    })

    flag_payload = {
        "flag_type": "inapplicable",
        "reason": "We moved from self-hosted Postgres to AWS Aurora Serverless.",
        "note": "No longer relevant to Aurora",
    }
    response = client.post(f"/api/memory/experience/{mem_id}/flag", json=flag_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["entry_id"] == mem_id
    assert data["flagged"]["flag_type"] == "inapplicable"
    assert "inapplicable" in data["action_taken"]


# --------------------------------------------------------------------------
# API-007: GET /api/incidents/{id}/memory
# --------------------------------------------------------------------------

def test_api_incident_memory(client: TestClient, reset_memory_double: HindsightTestDouble):
    """Test retrieving memory recalled for an existing incident."""
    # 1. Create incident
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Database pool exhaustion causing HTTP 500 errors in payments",
        "service": "payment-api",
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    # 2. Seed memory for payment-api
    reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "payment-api",
        "body": "Connection leak in transaction manager exhausted pool limit.",
        "outcome_label": "successful",
        "source_incident_ref": "inc-prior-01",
    })

    # 3. Retrieve incident memory
    mem_res = client.get(f"/api/incidents/{inc_id}/memory")
    assert mem_res.status_code == 200
    mem_data = mem_res.json()
    assert mem_data["incident_id"] == inc_id
    assert mem_data["memory_status"] == "ok"
    assert len(mem_data["entries"]) >= 1


# --------------------------------------------------------------------------
# API-016: Dependency Health Check with Memory
# --------------------------------------------------------------------------

def test_api_health_check_memory_dependency(client: TestClient, reset_memory_double: HindsightTestDouble):
    """Test /api/health reports memory dependency status."""
    # Healthy case
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["dependencies"]["memory"] == "connected"

    # Degraded memory case
    reset_memory_double.set_mode("unavailable")
    res_degraded = client.get("/api/health")
    assert res_degraded.status_code == 503
    data_degraded = res_degraded.json()
    assert data_degraded["status"] == "degraded"
    assert "degraded" in data_degraded["dependencies"]["memory"]

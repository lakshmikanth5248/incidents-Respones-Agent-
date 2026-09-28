"""
API Integration Tests for Feature 1 - Incident Intake & Normalization.
Explicitly implements Tests 1 through 10 from the prompt specification,
plus the ShopKart Payment API real-world scenario.
"""

from unittest.mock import patch
from sqlalchemy.exc import OperationalError
from src.data.models.incident import Incident


def test_test_1_valid_incident(client, count_incidents):
    """
    Test 1 — Valid incident
    Input: Payment API failure + DB exhaustion
    Expected: 201, incident created, normalized fields present, raw text preserved, status = created
    """
    initial_count = count_incidents()
    payload = {
        "symptom_description": "Payment API failure and DB connections are exhausted.",
        "service": "payment-api",
        "severity": "critical",
        "environment": "production"
    }

    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"].startswith("INC-")
    assert data["status"] == "created"
    assert data["raw_symptom_description"] == payload["symptom_description"]
    assert data["symptoms_raw"] == payload["symptom_description"]
    assert data["service"] == "payment-api"
    assert data["severity"] == "critical"
    assert data["environment"] == "production"

    # Normalized fields present
    assert "normalized" in data
    assert any("payment" in s for s in data["normalized"]["symptoms"])
    assert any("database" in s or "connection" in s for s in data["normalized"]["symptoms"])
    assert data["revision"] == 1
    assert "created_at" in data

    # Verify persisted in database
    assert count_incidents() == initial_count + 1


def test_test_2_empty_description(client, count_incidents):
    """
    Test 2 — Empty description
    Input: {"symptom_description": ""}
    Expected: 400 Bad Request, MINIMUM_INPUT_REQUIRED, No database record created
    """
    initial_count = count_incidents()
    payload = {"symptom_description": ""}

    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 400

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "MINIMUM_INPUT_REQUIRED"
    assert "symptom description is required" in data["error"]["message"].lower()

    # Explicit assertion: No database record created!
    assert count_incidents() == initial_count


def test_test_3_whitespace_description(client, count_incidents):
    """
    Test 3 — Whitespace description
    Input: "     "
    Expected: 400 Bad Request, No database record created
    """
    initial_count = count_incidents()
    payload = {"symptom_description": "   \n\t   "}

    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 400

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "MINIMUM_INPUT_REQUIRED"

    # Explicit assertion: No database record created!
    assert count_incidents() == initial_count


def test_test_4_invalid_severity(client, count_incidents):
    """
    Test 4 — Invalid severity
    Expected: 400/422, No database record created
    """
    initial_count = count_incidents()
    payload = {
        "symptom_description": "Payment API has elevated error rates.",
        "severity": "ultra-mega-critical"
    }

    response = client.post("/api/incidents", json=payload)
    assert response.status_code in [400, 422]

    data = response.json()
    assert "error" in data
    assert "severity" in data["error"]["message"].lower() or data["error"]["code"] == "INVALID_ENUM_VALUE"

    # Explicit assertion: No database record created!
    assert count_incidents() == initial_count


def test_test_5_malformed_request(client, count_incidents):
    """
    Test 5 — Malformed request
    Expected: 400 Bad Request, No database record created
    """
    initial_count = count_incidents()

    # 1. Invalid JSON body
    response = client.post(
        "/api/incidents",
        content="this is not valid json { [",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert count_incidents() == initial_count

    # 2. Missing required symptom_description field
    response2 = client.post("/api/incidents", json={"service": "payment-api"})
    assert response2.status_code == 400
    assert response2.json()["error"]["code"] in ["MINIMUM_INPUT_REQUIRED", "INVALID_INPUT"]
    assert count_incidents() == initial_count


def test_test_6_secret_shaped_input(client, count_incidents, caplog):
    """
    Test 6 — Secret-shaped input
    Verify that: secret-shaped values are rejected according to security policy,
    never persisted, and never exposed in logs or API error response.
    """
    initial_count = count_incidents()
    synthetic_api_key = "sk-live-abcdef1234567890abcdef1234567890"

    payload = {
        "symptom_description": f"Payment API failing with auth error: {synthetic_api_key}",
        "service": "payment-api"
    }

    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 400

    data = response.json()
    assert data["error"]["code"] == "SENSITIVE_DATA_DETECTED"

    # Security check: The secret value MUST NOT appear in the API error response!
    assert synthetic_api_key not in response.text

    # Security check: No database record created!
    assert count_incidents() == initial_count

    # Security check: The secret value MUST NOT appear in captured logs!
    for record in caplog.records:
        assert synthetic_api_key not in record.getMessage()


def test_test_7_raw_preservation(client, db_session):
    """
    Test 7 — Raw preservation
    Submit: "Payment API FAILED!!! DB=100/100"
    Verify the stored raw value is exactly the submitted text.
    """
    exact_text = "Payment API FAILED!!! DB=100/100"
    payload = {"symptom_description": exact_text}

    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["raw_symptom_description"] == exact_text
    assert data["symptoms_raw"] == exact_text

    # Verify directly from database
    persisted = db_session.query(Incident).filter(Incident.id == data["id"]).first()
    assert persisted is not None
    assert persisted.symptoms_raw == exact_text


def test_test_8_normalization(client):
    """
    Test 8 — Normalization
    Verify that structured fields are generated without changing the raw input.
    """
    raw_text = "Payment API is failing. DB connections are exhausted after payment-service v2.4 deployment."
    payload = {"symptom_description": raw_text}

    response = client.post("/api/incidents", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["raw_symptom_description"] == raw_text
    assert data["normalized"]["service"] == "payment-api"
    assert any("payment" in s for s in data["normalized"]["symptoms"])
    assert any("database" in s or "connection" in s for s in data["normalized"]["symptoms"])
    assert any("v2.4" in chg for chg in data["normalized"]["recent_changes"])
    assert "database_connection_exhaustion" in data["failure_mode_label"]


def test_test_9_duplicate_and_idempotency_behavior(client, count_incidents):
    """
    Test 9 — Duplicate / retry behavior
    Verify idempotency key prevents duplicate records and FR-008 duplicate flag functions.
    """
    initial_count = count_incidents()
    idempotency_key = "idemp-key-test-999"

    payload = {
        "symptom_description": "Database connection pool exhausted on payment-api.",
        "service": "payment-api"
    }

    # First call with idempotency key
    res1 = client.post("/api/incidents", json=payload, headers={"Idempotency-Key": idempotency_key})
    assert res1.status_code == 201
    id1 = res1.json()["id"]
    assert count_incidents() == initial_count + 1

    # Second call with the same idempotency key (retry)
    res2 = client.post("/api/incidents", json=payload, headers={"Idempotency-Key": idempotency_key})
    assert res2.status_code in [200, 201]
    assert res2.json()["id"] == id1

    # Database count must not increase on idempotent replay
    assert count_incidents() == initial_count + 1

    # Third call without idempotency key but same profile -> FR-008 duplicate detection flag
    res3 = client.post("/api/incidents", json=payload)
    assert res3.status_code == 201
    data3 = res3.json()
    assert data3["id"] != id1
    assert data3["possible_duplicate"] is True
    assert data3["duplicate_of"] == id1
    assert count_incidents() == initial_count + 2


def test_test_10_database_failure(client, count_incidents):
    """
    Test 10 — Database failure simulation
    Simulate a persistence failure.
    Expected: 5xx appropriate error (DB_UNAVAILABLE), No false 201 response.
    """
    initial_count = count_incidents()
    payload = {"symptom_description": "Critical failure in auth-service."}

    with patch("src.data.repositories.incident_repository.IncidentRepository.create", side_effect=OperationalError("Connection timeout", params=None, orig=Exception("DB Down"))):
        response = client.post("/api/incidents", json=payload)

    # Must be 500 error, never a false 201!
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["code"] == "DB_UNAVAILABLE"
    assert "database is unavailable" in data["error"]["message"].lower()

    # No record created
    assert count_incidents() == initial_count


def test_real_world_shopkart_payment_api_scenario(client):
    """
    Verification of the exact Section 3 scenario:
    Payment API is failing for customers.
    Error rate is around 31%.
    Latency increased to 4.8 seconds.
    Database connections are exhausted.
    Payment-service v2.4 was deployed approximately
    20 minutes before the incident.
    """
    sre_report = (
        "Payment API is failing for customers.\n"
        "Error rate is around 31%.\n"
        "Latency increased to 4.8 seconds.\n"
        "Database connections are exhausted.\n"
        "Payment-service v2.4 was deployed approximately\n"
        "20 minutes before the incident."
    )

    response = client.post("/api/incidents", json={"symptom_description": sre_report})
    assert response.status_code == 201

    data = response.json()

    # Check ID and initial state
    assert data["id"].startswith("INC-")
    assert data["status"] == "created"

    # Check raw preservation
    assert data["raw_symptom_description"] == sre_report

    # Check normalized fields
    norm = data["normalized"]
    assert norm["service"] == "payment-api"
    assert norm["severity"] == "critical"

    # Check symptoms
    assert any("payment" in s for s in norm["symptoms"])
    assert any("latency" in s for s in norm["symptoms"])
    assert any("database" in s or "connection" in s for s in norm["symptoms"])

    # Check observations
    assert any("31%" in obs for obs in norm["observations"])
    assert any("4.8" in obs for obs in norm["observations"])

    # Check recent changes
    assert any("v2.4" in chg for chg in norm["recent_changes"])

    # Check affected components
    assert "payment-api" in data["affected_components"]
    assert "database" in data["affected_components"]

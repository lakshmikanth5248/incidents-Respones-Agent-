"""
API Integration Tests for Feature 3 — Current Incident Analysis (TL-001).
Conforms to PRD §12.2 (API-005, API-006), §8, D-02, ERR-04, and Feature 3 requirements.
Verifies:
1. Successful analysis produces structured interpretation conforming to schema
2. Critical architectural invariant: NO HYPOTHESIS BEFORE RECALL (hypotheses must be empty)
3. Provenance tracking: every fact/inference has source: 'current_incident'
4. Unknown handling: unknown values are preserved, no fabricated facts
5. Malformed model output -> 502 with MODEL_OUTPUT_INVALID
6. Model unavailable -> 502 with MODEL_UNAVAILABLE
7. Revisioning: subsequent analyses increment revision and prior revisions remain auditable
8. Deterministic output
9. Token and duration metrics logging
10. Retrieval via GET /api/incidents/{id}/analysis
"""

from unittest.mock import patch
from src.agent.provider import MockDeterministicProvider


def test_successful_current_incident_analysis(client):
    """
    Test successful execution of Stage 1 analysis (TL-001):
    - Generates structured interpretation
    - Transitions incident state to 'analyzed'
    - Populates scope, failure mode, facts, inferences, unknowns, and information gaps
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Payment API latency is 4.8s and database connections are exhausted.",
        "service": "payment-api",
        "environment": "production",
        "severity": "critical"
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    assert data["incident_id"] == inc_id
    assert data["analysis_id"].startswith(f"ANA-{inc_id}")
    assert data["revision"] == 1
    assert data["status"] == "ready_for_recall"

    # Symptom Analysis / Interpretation fields
    symptom_analysis = data["symptom_analysis"]
    assert symptom_analysis["affected_scope"]["service"] == "payment-api"
    assert symptom_analysis["affected_scope"]["environment"] == "production"
    assert "database" in symptom_analysis["affected_scope"]["affected_components"]
    assert "database_connection_exhaustion" in symptom_analysis["failure_mode"]

    # Facts & Inferences
    assert len(symptom_analysis["facts"]) > 0
    assert len(symptom_analysis["inferences"]) > 0

    # Model metadata & cost/duration tracking
    meta = data["model_metadata"]
    assert meta["prompt_tokens"] > 0
    assert meta["completion_tokens"] > 0
    assert meta["total_tokens"] > 0
    assert meta["duration_ms"] >= 0
    assert meta["prompt_version"] == "v1.0.0"

    # Incident state verification: parent incident status is now 'analyzed'
    inc_res = client.get(f"/api/incidents/{inc_id}")
    assert inc_res.json()["status"] == "analyzed"
    assert inc_res.json()["analysis_revision"] == 1
    assert inc_res.json()["analysis_id"] == data["analysis_id"]


def test_critical_rule_no_hypothesis_before_recall(client):
    """
    CRITICAL ARCHITECTURAL REQUIREMENT (D-02):
    The analysis order MUST be: INTERPRET -> RECALL -> COMPARE -> HYPOTHESIZE.
    The system must NOT generate hypotheses before Hindsight recall completes.
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Payment API connection pool saturated",
        "service": "payment-api"
    })
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    # Hypotheses list MUST be empty at this stage
    assert data["hypotheses"] == []
    assert data["comparisons"] == []
    assert data["recall_record"] is not None
    assert data["memory_status"] in ["ok", "empty", "degraded", "suppressed"]


def test_provenance_marking_on_every_statement(client):
    """
    Every statement must identify its provenance:
    {"source": "current_incident", "statement": "..."}
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Database connections are exhausted after payment-service v2.4 deployment",
        "service": "payment-api"
    })
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    interpretation = data["symptom_analysis"]

    for fact in interpretation["facts"]:
        assert fact["source"] == "current_incident"
        assert len(fact["statement"]) > 0

    for inference in interpretation["inferences"]:
        assert inference["source"] == "current_incident"
        assert len(inference["statement"]) > 0


def test_unknown_fields_handling(client):
    """
    Unknown handling: Unknown is a valid value. Never convert unknown into an invented fact.
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "System is experiencing unexpected latency",
        # environment and service omitted -> unknown
    })
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()
    interpretation = data["symptom_analysis"]

    assert interpretation["affected_scope"]["environment"] == "unknown"
    assert len(interpretation["unknowns"]) > 0
    assert any("environment" in u.lower() for u in interpretation["unknowns"])


def test_model_unavailable_error(client):
    """
    Provider unavailable / network error simulation:
    Returns 502 with MODEL_UNAVAILABLE. Incident data remains untouched.
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Auth service latency spike",
        "service": "auth-service"
    })
    inc_id = create_res.json()["id"]
    initial_status = create_res.json()["status"]

    with patch("src.services.analysis_service.get_model_provider", return_value=MockDeterministicProvider(simulate_failure="unavailable")):
        res = client.post(f"/api/incidents/{inc_id}/analyze")

    assert res.status_code == 502
    data = res.json()
    assert data["error"]["code"] == "MODEL_UNAVAILABLE"
    assert "could not be reached" in data["error"]["message"].lower()

    # Verify incident state was NOT modified
    inc = client.get(f"/api/incidents/{inc_id}").json()
    assert inc["status"] == initial_status
    assert inc["analysis_revision"] == 0


def test_malformed_model_output_error(client):
    """
    Model output invalid / schema failure simulation:
    Returns 502 with MODEL_OUTPUT_INVALID. Incident data remains untouched.
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Order service returning 500s",
        "service": "order-service"
    })
    inc_id = create_res.json()["id"]

    with patch("src.services.analysis_service.get_model_provider", return_value=MockDeterministicProvider(simulate_failure="malformed")):
        res = client.post(f"/api/incidents/{inc_id}/analyze")

    assert res.status_code == 502
    data = res.json()
    assert data["error"]["code"] == "MODEL_OUTPUT_INVALID"


def test_analysis_revisioning_and_auditability(client):
    """
    Subsequent analysis runs supersede prior artefacts with incremented revision,
    while prior revisions remain retrievable for audit (API-006, BE-019).
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Search API degraded",
        "service": "search-api"
    })
    inc_id = create_res.json()["id"]

    # Run 1: revision 1
    res1 = client.post(f"/api/incidents/{inc_id}/analyze")
    assert res1.status_code == 200
    assert res1.json()["revision"] == 1
    rev1_id = res1.json()["analysis_id"]

    # Run 2: re-analyze -> revision 2
    res2 = client.post(f"/api/incidents/{inc_id}/analyze")
    assert res2.status_code == 200
    assert res2.json()["revision"] == 2
    rev2_id = res2.json()["analysis_id"]
    assert rev1_id != rev2_id

    # Verify GET /api/incidents/{id}/analysis defaults to latest revision (revision 2)
    latest_res = client.get(f"/api/incidents/{inc_id}/analysis")
    assert latest_res.status_code == 200
    assert latest_res.json()["revision"] == 2

    # Verify GET with ?revision=1 retrieves the original revision 1 artefact
    r1_res = client.get(f"/api/incidents/{inc_id}/analysis?revision=1")
    assert r1_res.status_code == 200
    assert r1_res.json()["revision"] == 1
    assert r1_res.json()["analysis_id"] == rev1_id


def test_deterministic_output(client):
    """
    Deterministic provider generates identical outputs given identical incident input.
    """
    payload = {
        "symptom_description": "Kafka broker partition offline",
        "service": "kafka-cluster",
        "environment": "production"
    }

    res1 = client.post("/api/incidents", json=payload)
    res2 = client.post("/api/incidents", json=payload)

    id1 = res1.json()["id"]
    id2 = res2.json()["id"]

    ana1 = client.post(f"/api/incidents/{id1}/analyze").json()["symptom_analysis"]
    ana2 = client.post(f"/api/incidents/{id2}/analyze").json()["symptom_analysis"]

    assert ana1["affected_scope"] == ana2["affected_scope"]
    assert ana1["failure_mode"] == ana2["failure_mode"]
    assert ana1["facts"] == ana2["facts"]


def test_get_analysis_not_found(client):
    """
    Returns 404 if incident does not exist or has no analysis yet.
    """
    create_res = client.post("/api/incidents", json={"symptom_description": "Unanalyzed incident"})
    inc_id = create_res.json()["id"]

    # Incident exists but no analysis run yet -> 404
    res = client.get(f"/api/incidents/{inc_id}/analysis")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"

    # Nonexistent incident -> 404
    res_fake = client.get("/api/incidents/INC-1999-9999/analysis")
    assert res_fake.status_code == 404

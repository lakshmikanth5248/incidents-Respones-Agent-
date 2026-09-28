"""
Backend Feature 08 — Recommendation + Runbook Intelligence Tests.
Conforms strictly to PRD Part 1 §12.6 (FR-035–FR-044), Part 3 §0.2 (NG-02, NG-03), and Feature 08.

Test Matrix:
1. recommendation with runbook (precedent-ordered, successful labelled)
2. recommendation without runbook (explicit absence, no fabrication)
3. failed runbook (ineffective runbook not presented as proven, warning & safer alternative)
4. unknown runbook (404 on API-015 lookup)
5. runbook service unavailable (503 on catalog, fallback to evidence-based guidance in analysis)
6. provenance (every recommendation carries full provenance and evidence links)
7. no autonomous action (strictly advisory, prohibited tools blocked in tool registry)
8. recommendation schema (completeness across all 10 required fields)
9. runbook endpoints (GET /api/runbooks, GET /api/runbooks/{id}, filtering, search)
"""

import pytest
from fastapi.testclient import TestClient

from src.memory.test_double import HindsightTestDouble
from src.memory.schemas import EntryType, OutcomeLabel, ConfidenceLevel
from src.services.runbook_service import runbook_service
from src.agent.tools import (
    agent_tool_registry,
    AgentTool,
    AutonomousActionProhibitedError,
    PROHIBITED_TOOLS,
)


@pytest.fixture(autouse=True)
def clean_runbook_service():
    """Ensure runbook service is reset before and after every test."""
    runbook_service.reset()
    yield
    runbook_service.reset()


# --------------------------------------------------------------------------
# 1. Runbook Catalog Endpoints (API-015)
# --------------------------------------------------------------------------

def test_runbook_endpoints_list_and_search(client: TestClient):
    """
    Test GET /api/runbooks listing and filtering:
    - Lists default runbooks with track records
    - Filters by service
    - Filters by failure_mode_label
    - Search query across steps/symptoms
    """
    # 1. List all
    res = client.get("/api/runbooks")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 6
    assert len(data["runbooks"]) == data["total"]

    # Verify runbook fields conform to API-015
    first = data["runbooks"][0]
    assert "id" in first
    assert "title" in first
    assert "service" in first
    assert "failure_mode_label" in first
    assert "steps" in first
    assert isinstance(first["steps"], list)
    assert "applicable_symptoms" in first
    assert "risk_level" in first
    assert "is_destructive" in first
    assert "track_record" in first
    assert "times_applied" in first["track_record"]

    # 2. Filter by service
    svc_res = client.get("/api/runbooks?service=payment-api")
    assert svc_res.status_code == 200
    svc_data = svc_res.json()
    assert svc_data["total"] >= 2
    for rb in svc_data["runbooks"]:
        assert rb["service"] == "payment-api"

    # 3. Filter by failure mode
    fm_res = client.get("/api/runbooks?failure_mode_label=database_connection_exhaustion")
    assert fm_res.status_code == 200
    fm_data = fm_res.json()
    assert fm_data["total"] >= 2
    for rb in fm_data["runbooks"]:
        assert rb["failure_mode_label"] == "database_connection_exhaustion"

    # 4. Search query
    q_res = client.get("/api/runbooks?q=pg_stat_activity")
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["total"] >= 1
    assert any("pg_stat_activity" in step for rb in q_data["runbooks"] for step in rb["steps"])


def test_unknown_runbook_404(client: TestClient):
    """
    Test GET /api/runbooks/{id}:
    - 200 for existing runbook
    - 404 with RUNBOOK_NOT_FOUND for unknown runbook
    """
    # Known runbook
    res = client.get("/api/runbooks/RB-PAY-001")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "RB-PAY-001"
    assert data["service"] == "payment-api"
    assert data["risk_level"] == "medium"
    assert data["is_destructive"] is False

    # Unknown runbook
    bad_res = client.get("/api/runbooks/NONEXISTENT-999")
    assert bad_res.status_code == 404
    assert bad_res.json()["error"]["code"] == "RUNBOOK_NOT_FOUND"


# --------------------------------------------------------------------------
# 2. Runbook Service Unavailable (503 & Evidence-based Guidance)
# --------------------------------------------------------------------------

def test_runbook_service_unavailable(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test RUNBOOK_SET_UNAVAILABLE:
    - GET /api/runbooks returns 503 when service is unavailable.
    - Incident analysis provides evidence-based guidance, explicitly states absence,
      and never fabricates a runbook.
    """
    # 1. Simulate outage on catalog
    runbook_service.set_available(False)

    catalog_res = client.get("/api/runbooks")
    assert catalog_res.status_code == 503
    assert catalog_res.json()["error"]["code"] == "RUNBOOK_SET_UNAVAILABLE"

    single_res = client.get("/api/runbooks/RB-PAY-001")
    assert single_res.status_code == 503
    assert single_res.json()["error"]["code"] == "RUNBOOK_SET_UNAVAILABLE"

    # 2. Analyze incident during catalog outage
    create_res = client.post("/api/incidents", json={
        "service": "payment-api",
        "environment": "production",
        "symptom_description": "Payment API connection pool exhaustion with high latency.",
    })
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    recs = data["recommendations"]
    assert len(recs) >= 1

    # Check that outage is explicitly stated and no runbook is fabricated
    outage_rec = next((r for r in recs if r["runbook_outcome"] == "RUNBOOK_SET_UNAVAILABLE"), None)
    assert outage_rec is not None
    assert outage_rec["runbook_reference"] is None
    assert "RUNBOOK_SET_UNAVAILABLE" in outage_rec["reason"]
    assert "Never fabricating a runbook" in outage_rec["reason"]
    assert outage_rec["action_type"] == "diagnostic"
    assert outage_rec["is_destructive"] is False


# --------------------------------------------------------------------------
# 3. Recommendation with Runbook
# --------------------------------------------------------------------------

def test_recommendation_with_runbook(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test recommendation generation when matching runbook exists and has prior success in memory.
    - Diagnostic step is presented first (FR-039).
    - Remediation step links runbook, labels outcome as successful (FR-037).
    - Destructive procedure (rollback) is flagged with risk='high', is_destructive=True, safer_alternative (FR-042).
    """
    # Seed prior successful memory referencing RB-PAY-001
    reset_memory_double.seed_entry({
        "entry_type": EntryType.SUCCESSFUL_ACTION.value,
        "service": "payment-api",
        "body": "Executed RB-PAY-001 Payment API Connection Pool Recovery to clear idle leases.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-2024-PRIOR-01",
    })

    create_res = client.post("/api/incidents", json={
        "service": "payment-api",
        "environment": "production",
        "symptom_description": "Payment API connection pool exhausted following release v2.4 deployment.",
    })
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    recs = data["recommendations"]
    assert len(recs) >= 2

    # 1. First recommendation is Diagnostic (FR-039)
    diag = recs[0]
    assert diag["action_type"] == "diagnostic"
    assert diag["is_destructive"] is False
    assert "Compare payment-service" in diag["action"] or "Compare" in diag["action"]
    assert "v2.4" in diag["reason"] or "deployment" in diag["reason"]

    # 2. Remediation recommendation with runbook RB-PAY-001
    rb_rec = next((r for r in recs if r["runbook_reference"] == "RB-PAY-001"), None)
    assert rb_rec is not None
    assert rb_rec["runbook_outcome"] == "successful"
    assert "PREVIOUSLY SUCCESSFUL" in rb_rec["reason"] or "successful" in rb_rec["reason"].lower()
    assert rb_rec["action_type"] == "remediation"
    assert rb_rec["confidence"]["score"] >= 0.85

    # 3. High-risk rollback procedure RB-PAY-ROLLBACK-002
    rollback_rec = next((r for r in recs if r["runbook_reference"] == "RB-PAY-ROLLBACK-002"), None)
    if rollback_rec:
        assert rollback_rec["risk"] == "high"
        assert rollback_rec["is_destructive"] is True
        assert rollback_rec["safer_alternative"] is not None
        assert "Engineer may consider rollback" in rollback_rec["reason"]

    # 4. Verify GET /api/incidents/{id}/recommendations endpoint
    rec_res = client.get(f"/api/incidents/{inc_id}/recommendations")
    assert rec_res.status_code == 200
    rec_items = rec_res.json()
    assert len(rec_items) == len(recs)
    assert rec_items[0]["recommendation_id"] == recs[0]["recommendation_id"]


# --------------------------------------------------------------------------
# 4. Recommendation Without Runbook (Explicit Absence, No Fabrication)
# --------------------------------------------------------------------------

def test_recommendation_without_runbook(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test recommendation generation when no matching runbook exists in catalog.
    - Explicitly states that no matching runbook was found (FR-041).
    - Sets runbook_reference = None and runbook_outcome = "no_matching_runbook".
    - Never fabricates a runbook.
    - Provides evidence-based diagnostic troubleshooting.
    """
    create_res = client.post("/api/incidents", json={
        "service": "billing-generator",
        "environment": "production",
        "symptom_description": "Billing generator precision rounding error during quarterly invoice generation.",
    })
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    recs = data["recommendations"]
    assert len(recs) >= 1

    # Check for explicit absence of runbook
    no_rb = next((r for r in recs if r["runbook_outcome"] == "no_matching_runbook"), None)
    assert no_rb is not None
    assert no_rb["runbook_reference"] is None
    assert "No matching runbook" in no_rb["reason"]
    assert "Never fabricating a runbook" in no_rb["reason"]


# --------------------------------------------------------------------------
# 5. Failed Runbook Memory (Not Presented as Proven)
# --------------------------------------------------------------------------

def test_failed_runbook_memory(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test that a previously failed runbook:
    - Has runbook_outcome = "ineffective".
    - Is NOT presented as proven.
    - Surfaces prominent risk warning and safer diagnostic alternatives.
    - Is ranked behind successful procedures.
    """
    # Seed memory recording RB-PAY-001 as ineffective
    reset_memory_double.seed_entry({
        "entry_type": EntryType.FAILED_ACTION.value,
        "service": "payment-api",
        "body": "Attempted RB-PAY-001 Payment API Connection Pool Recovery but connection leases remained stuck.",
        "outcome_label": OutcomeLabel.INEFFECTIVE.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-2024-FAILED-02",
    })

    create_res = client.post("/api/incidents", json={
        "service": "payment-api",
        "environment": "production",
        "symptom_description": "Payment API connection pool exhaustion with high latency.",
    })
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    recs = data["recommendations"]
    failed_rb = next((r for r in recs if r["runbook_reference"] == "RB-PAY-001"), None)
    assert failed_rb is not None

    # Crucial assertion: marked ineffective, not proven
    assert failed_rb["runbook_outcome"] == "ineffective"
    assert "INEFFECTIVE" in failed_rb["reason"] or "Do NOT present as proven" in failed_rb["reason"]
    assert failed_rb["risk"] == "high"
    assert failed_rb["safer_alternative"] is not None
    assert failed_rb["confidence"]["score"] <= 0.50


# --------------------------------------------------------------------------
# 6. Recommendation Provenance
# --------------------------------------------------------------------------

def test_recommendation_provenance(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test that every recommendation carries complete provenance and evidence markers (FR-040, FR-045).
    """
    mem_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "payment-api",
        "body": "Stale connection pool leases.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "source_incident_ref": "INC-2024-PROV-01",
    })

    create_res = client.post("/api/incidents", json={
        "service": "payment-api",
        "environment": "production",
        "symptom_description": "Payment API connection exhaustion.",
    })
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    data = analyze_res.json()

    for rec in data["recommendations"]:
        assert len(rec["provenance"]) >= 1
        for p in rec["provenance"]:
            assert "source" in p
            assert "statement" in p
            assert len(p["statement"]) > 0

        assert isinstance(rec["supporting_evidence"], list)
        assert len(rec["supporting_evidence"]) >= 1

        assert isinstance(rec["confidence"], dict)
        assert "score" in rec["confidence"]
        assert "level" in rec["confidence"]
        assert "basis" in rec["confidence"]

        assert rec["expected_observation"] is not None
        assert len(rec["expected_observation"]) > 0
        assert rec["advisory"] is True
        assert "Advisory only" in rec["advisory_note"]


# --------------------------------------------------------------------------
# 7. No Autonomous Action / Tool Registry Prohibition (FR-043, NG-02, NG-03)
# --------------------------------------------------------------------------

def test_no_autonomous_action_prohibited_tools():
    """
    CRITICAL SAFETY REQUIREMENT:
    The agent recommends. The agent does NOT execute production actions.
    There must be NO:
    - kubectl
    - rollback API
    - delete production resource
    - restart production service
    - database mutation tool
    in the agent tool registry.
    """
    # 1. Verify global tool registry contains no prohibited tools
    assert agent_tool_registry.has_prohibited_tools() is False

    registered_names = [t["name"].lower() for t in agent_tool_registry.list_tools()]
    for prohibited in PROHIBITED_TOOLS:
        assert prohibited.lower() not in registered_names

    # 2. Verify all tools in registry are read-only
    for tool_dict in agent_tool_registry.list_tools():
        assert tool_dict["is_read_only"] is True

    # 3. Attempting to register prohibited tools must raise AutonomousActionProhibitedError
    for prohibited in ["kubectl", "rollback", "rollback_api", "delete_production_resource", "restart_production_service", "database_mutation_tool"]:
        with pytest.raises(AutonomousActionProhibitedError):
            AgentTool(name=prohibited, description="Prohibited production execution tool")

    # 4. Attempting to register non-read-only tool must raise AutonomousActionProhibitedError
    with pytest.raises(AutonomousActionProhibitedError):
        AgentTool(name="safe_reader", description="Write action", is_read_only=False)


# --------------------------------------------------------------------------
# 8. Recommendation Schema Completeness
# --------------------------------------------------------------------------

def test_recommendation_schema_completeness(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test that recommendations satisfy all 10 required fields from prompt:
    - recommendation_id
    - action/investigation
    - reason
    - supporting evidence
    - memory references
    - runbook reference
    - risk
    - expected observation
    - confidence
    - provenance
    """
    create_res = client.post("/api/incidents", json={
        "service": "payment-api",
        "environment": "production",
        "symptom_description": "Payment API connection pool exhaustion with 500 errors.",
    })
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    data = analyze_res.json()
    recs = data["recommendations"]
    assert len(recs) >= 1

    for rec in recs:
        # Check all 10 required fields
        assert rec["recommendation_id"].startswith(f"REC-{inc_id}")
        assert len(rec["action"]) > 0
        assert rec["investigation"] is not None
        assert len(rec["reason"]) > 0
        assert isinstance(rec["supporting_evidence"], list)
        assert isinstance(rec["memory_references"], list)
        assert "runbook_reference" in rec
        assert rec["risk"] in ["low", "medium", "high"]
        assert len(rec["expected_observation"]) > 0
        assert isinstance(rec["confidence"], dict)
        assert 0.0 <= rec["confidence"]["score"] <= 1.0
        assert isinstance(rec["provenance"], list)
        assert len(rec["provenance"]) >= 1

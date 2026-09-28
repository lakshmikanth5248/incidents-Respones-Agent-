"""
Feature 11 — Post-Mortem Generation Tests.

Test Matrix:
  F11-T01  successful draft                     — full draft generation with all 15 required sections
  F11-T02  unresolved incident (precondition)   — 409 INCIDENT_NOT_RESOLVED when incident not resolved
  F11-T03  model failure (integrity)            — 502 MODEL_UNAVAILABLE, incident/resolution data intact
  F11-T04  unknown root cause                   — root_cause="unknown", source="unknown", confidence="low", no fabrication
  F11-T05  historical reference                 — cites recalled entries, maintains provenance
  F11-T06  provenance tracking                  — all root cause & evidence items carry explicit source
  F11-T07  hallucinated historical fact guard   — unverified memory entries rejected and flagged
  F11-T08  inference root cause                 — unconfirmed agent hypothesis labelled as inference, not fact
  F11-T09  verification feeds effectiveness     — confirmed verification sets resolution_effectiveness="effective"
  F11-T10  verification failure effectiveness   — failed verification sets resolution_effectiveness="ineffective"
  F11-T11  GET postmortem record                — 200 after draft, 404 POSTMORTEM_NOT_FOUND before draft
  F11-T12  incident not found                   — 404 for nonexistent incident ID
"""

import pytest
from src.data.models.incident import Incident
from src.data.models.postmortem import PostMortem
from src.services.postmortem_service import PostMortemService


INCIDENT_PAYLOAD = {
    "symptom_description": (
        "Payment API connection pool exhaustion. "
        "HikariPool-1 – Connection is not available, request timed out after 30000ms."
    ),
    "service": "payment-api",
    "environment": "production",
    "severity": "critical",
}


def create_incident(client) -> str:
    r = client.post("/api/incidents", json=INCIDENT_PAYLOAD)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def resolve_incident(client, inc_id: str, root_cause: str = "Database connection pool misconfiguration") -> str:
    payload = {
        "actions": [
            "Rolled back payment service deployment to v2.4.0",
            "Terminated stale backend database connection sessions",
        ],
        "runbook_id": "rb-pay-001",
        "runbook_version": "1.2.0",
        "contributing_factors": ["Traffic spike during flash sale", "Pool limit set to default 10"],
        "root_cause": root_cause,
        "result": "Latency recovered to <120ms, error rate dropped to 0.01%",
        "outcome": "successful",
    }
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 200, r.text
    return r.json()["resolution_id"]


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_successful_draft(client):
    """
    F11-T01: Successful post-mortem draft generation.
    Checks all 15 PRD-required sections, status=draft, and lifecycle update.
    """
    inc_id = create_incident(client)
    resolve_incident(client, inc_id, root_cause="Database connection pool misconfiguration")

    # Verify outcome with telemetry
    client.post(f"/api/incidents/{inc_id}/verify", json={
        "before_metrics": {"error_rate": "31%", "latency": "4.8s"},
        "after_metrics": {"error_rate": "2%", "latency": "420ms"},
        "observations": ["Pool stabilized", "Error spike subsided"],
    })

    # Generate Post-Mortem
    resp = client.post(f"/api/incidents/{inc_id}/postmortem", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Verify draft status
    assert data["status"] == "draft"
    assert data["incident_id"] == inc_id

    # Verify all 15 PRD-required fields
    assert "summary" in data and len(data["summary"]) > 0
    assert "impact" in data and len(data["impact"]) > 0
    assert "timeline" in data and len(data["timeline"]) >= 3
    assert "symptom_description" in data and len(data["symptom_description"]) > 0
    assert data["root_cause"] == "Database connection pool misconfiguration"
    assert data["root_cause_source"] == "human"
    assert data["root_cause_confidence"] == "high"
    assert "Rolled back payment service" in data["resolution"]
    assert data["resolution_effectiveness"] == "effective"
    assert len(data["contributing_factors"]) >= 1
    assert len(data["what_went_well"]) >= 1
    assert len(data["what_did_not"]) >= 1
    assert len(data["lessons"]) >= 1
    assert len(data["preventive_actions"]) >= 1
    assert len(data["unknowns"]) >= 1

    # Verify incident lifecycle postmortem_status updated
    inc_resp = client.get(f"/api/incidents/{inc_id}")
    assert inc_resp.json()["postmortem_status"] == "draft"


def test_unresolved_incident_precondition(client):
    """
    F11-T02: Precondition: Incident must be resolved or mitigated.
    Attempting to generate a post-mortem for an unresolved incident returns 409 INCIDENT_NOT_RESOLVED.
    """
    inc_id = create_incident(client)

    # Incident is created, not resolved
    resp = client.post(f"/api/incidents/{inc_id}/postmortem", json={})
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "INCIDENT_NOT_RESOLVED"

    # Verify post-mortem was NOT created
    get_resp = client.get(f"/api/incidents/{inc_id}/postmortem")
    assert get_resp.status_code == 404


def test_model_failure_integrity(client):
    """
    F11-T03: Model failure handling.
    If the model fails, returns 502 MODEL_UNAVAILABLE.
    Incident and resolution data remain intact. No fake post-mortem is created.
    """
    inc_id = create_incident(client)
    resolve_incident(client, inc_id)

    # Request with simulate_failure="unavailable"
    resp = client.post(f"/api/incidents/{inc_id}/postmortem", json={
        "simulate_failure": "unavailable"
    })
    assert resp.status_code == 502, resp.text
    assert resp.json()["error"]["code"] == "MODEL_UNAVAILABLE"

    # Incident & resolution data must remain intact
    inc_resp = client.get(f"/api/incidents/{inc_id}")
    assert inc_resp.status_code == 200
    assert inc_resp.json()["status"] == "resolved"
    assert inc_resp.json()["resolution_status"] == "resolved"

    res_resp = client.get(f"/api/incidents/{inc_id}/resolution")
    assert res_resp.status_code == 200
    assert res_resp.json()["outcome"] == "successful"

    # No fake post-mortem persisted
    pm_resp = client.get(f"/api/incidents/{inc_id}/postmortem")
    assert pm_resp.status_code == 404
    assert pm_resp.json()["error"]["code"] == "POSTMORTEM_NOT_FOUND"


def test_unknown_root_cause(client):
    """
    F11-T04: Unknown root cause handling.
    When root cause is unknown, root_cause="unknown", root_cause_source="unknown",
    confidence="low". The system does NOT invent a root cause fact.
    """
    inc_id = create_incident(client)
    resolve_incident(client, inc_id, root_cause="unknown")

    resp = client.post(f"/api/incidents/{inc_id}/postmortem", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["root_cause"] == "unknown"
    assert data["root_cause_source"] == "unknown"
    assert data["root_cause_confidence"] == "low"
    assert any("root cause" in u.lower() for u in data["unknowns"])


def test_historical_reference_and_provenance(client, db_session):
    """
    F11-T05 & F11-T06: Historical memory reference and provenance.
    Cites only recalled entries and maintains exact provenance.
    """
    inc_id = create_incident(client)
    resolve_incident(client, inc_id)

    # Attach verified recall record to incident
    inc = db_session.query(Incident).filter(Incident.id == inc_id).first()
    inc.recall_record = {
        "entries": [
            {
                "entry_id": "mem-pay-001",
                "incident_id": "INC-2025-0891",
                "summary": "Hikari connection pool leak under high concurrency resolved by v1.2 rollback.",
                "provenance": {"source": "historical_memory", "confidence": "high"},
            }
        ]
    }
    db_session.commit()

    resp = client.post(f"/api/incidents/{inc_id}/postmortem", json={"include_memory_reference": True})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Memory reference present
    assert len(data["memory_references"]) == 1
    ref = data["memory_references"][0]
    assert ref["memory_entry_id"] == "mem-pay-001"
    assert ref["incident_id"] == "INC-2025-0891"

    # Provenance tracked
    sources = [p["source"] for p in data["provenance"]]
    assert "human" in sources
    assert "historical_memory" in sources


def test_hallucinated_historical_fact_detection():
    """
    F11-T07: Anti-hallucination guard.
    Verifies that ungrounded / unverified historical memory references are detected and rejected.
    """
    verified_ids = {"mem-verified-101", "mem-verified-102"}
    recalled_entries = [
        {"entry_id": "mem-verified-101", "incident_id": "INC-1", "summary": "Valid memory"},
        {"entry_id": "mem-hallucinated-999", "incident_id": "INC-FAKE", "summary": "Hallucinated memory"},
    ]
    unknowns = []

    refs, prov = PostMortemService._build_memory_references(
        recalled_entries=recalled_entries,
        verified_memory_ids=verified_ids,
        include_memory_reference=True,
        unknowns=unknowns,
    )

    # Hallucinated entry was filtered out
    assert len(refs) == 1
    assert refs[0]["memory_entry_id"] == "mem-verified-101"

    # Hallucination was flagged in unknowns
    assert any("mem-hallucinated-999" in u for u in unknowns)
    assert any("prevent hallucination" in u for u in unknowns)


def test_inference_as_root_cause(client):
    """
    F11-T08: When engineer does not provide a root cause, agent hypothesis is used
    with root_cause_source="inference" and explicitly labelled as hypothesis.
    """
    inc_id = create_incident(client)

    # Analyze first to generate hypothesis
    client.post(f"/api/incidents/{inc_id}/analyze")

    # Resolve without a specific root cause
    payload = {
        "actions": ["Restarted worker pods"],
        "outcome": "successful",
    }
    client.post(f"/api/incidents/{inc_id}/resolve", json=payload)

    resp = client.post(f"/api/incidents/{inc_id}/postmortem", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Identified as inference, never confirmed fact
    assert data["root_cause_source"] == "inference"
    assert "Hypothesized" in data["root_cause"]


def test_verification_feeds_effectiveness(client):
    """
    F11-T09: Verification outcome feeds post-mortem resolution_effectiveness.
    Confirmed verification -> resolution_effectiveness = "effective".
    """
    inc_id = create_incident(client)
    resolve_incident(client, inc_id)

    client.post(f"/api/incidents/{inc_id}/verify", json={
        "before_metrics": {"error_rate": "31%"},
        "after_metrics": {"error_rate": "2%"},
    })

    resp = client.post(f"/api/incidents/{inc_id}/postmortem", json={})
    assert resp.status_code == 200
    assert resp.json()["resolution_effectiveness"] == "effective"


def test_verification_failure_effectiveness(client):
    """
    F11-T10: Failed verification -> resolution_effectiveness = "ineffective".
    """
    inc_id = create_incident(client)
    resolve_incident(client, inc_id)

    client.post(f"/api/incidents/{inc_id}/verify", json={
        "before_metrics": {"error_rate": "31%"},
        "after_metrics": {"error_rate": "45%"},
    })

    resp = client.post(f"/api/incidents/{inc_id}/postmortem", json={})
    assert resp.status_code == 200
    assert resp.json()["resolution_effectiveness"] == "ineffective"


def test_get_postmortem_record(client):
    """
    F11-T11: GET /api/incidents/{id}/postmortem.
    404 before draft; 200 after draft.
    """
    inc_id = create_incident(client)
    resolve_incident(client, inc_id)

    # 404 before draft
    r_before = client.get(f"/api/incidents/{inc_id}/postmortem")
    assert r_before.status_code == 404
    assert r_before.json()["error"]["code"] == "POSTMORTEM_NOT_FOUND"

    # Generate draft
    client.post(f"/api/incidents/{inc_id}/postmortem", json={})

    # 200 after draft
    r_after = client.get(f"/api/incidents/{inc_id}/postmortem")
    assert r_after.status_code == 200
    assert r_after.json()["status"] == "draft"
    assert r_after.json()["incident_id"] == inc_id


def test_postmortem_incident_not_found(client):
    """
    F11-T12: 404 for nonexistent incident ID.
    """
    r_post = client.post("/api/incidents/inc-nonexistent-9999/postmortem", json={})
    assert r_post.status_code == 404
    assert r_post.json()["error"]["code"] == "INCIDENT_NOT_FOUND"

    r_get = client.get("/api/incidents/inc-nonexistent-9999/postmortem")
    assert r_get.status_code == 404
    assert r_get.json()["error"]["code"] == "INCIDENT_NOT_FOUND"

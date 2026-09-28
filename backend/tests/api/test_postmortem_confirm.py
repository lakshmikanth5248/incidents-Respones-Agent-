"""
Feature 12 — Post-Mortem Confirmation & Memory Candidate Tests.

Test Matrix:
  F12-T01  valid confirmation                   — status -> confirmed, reviewed_by set, memory candidates composed
  F12-T02  confirmation with corrections        — allowed fields corrected, original preserved, candidates reflect update
  F12-T03  non-correctable fields ignored       — unrecognized fields ignored, valid corrections applied
  F12-T04  confirmation without draft           — 404 POSTMORTEM_NOT_FOUND
  F12-T05  unresolved incident precondition     — 409 INCIDENT_NOT_RESOLVED
  F12-T06  idempotent confirmation              — duplicate confirm returns 200 with original attestation
  F12-T07  memory candidate composition types   — generates root_cause, resolution, lesson, prevention, runbook_outcome
  F12-T08  unknown root cause exclusion         — root_cause="unknown" does not produce candidate entry
  F12-T09  candidate provenance verification    — every candidate contains provenance tracing back to post-mortem
  F12-T10  GET after confirmation               — returns confirmed status, corrections, and memory candidates
  F12-T11  review notes persisted               — review_notes stored on post-mortem and returned in response
  F12-T12  incident not found                   — 404 INCIDENT_NOT_FOUND for non-existent incident
"""

import pytest
from src.data.models.incident import Incident
from src.data.models.postmortem import PostMortem
from src.services.postmortem_service import PostMortemService


INCIDENT_PAYLOAD = {
    "symptom_description": (
        "Cart checkout service 504 Gateway Timeout. "
        "Redis connection pool exhausted after marketing email campaign."
    ),
    "service": "cart-checkout",
    "environment": "production",
    "severity": "critical",
}


def create_and_resolve_incident(
    client,
    root_cause: str = "Redis connection pool limit exceeded",
    runbook_id: str = "rb-redis-002",
) -> str:
    """Helper to create, resolve, and verify an incident ready for post-mortem."""
    r = client.post("/api/incidents", json=INCIDENT_PAYLOAD)
    assert r.status_code == 201, r.text
    inc_id = r.json()["id"]

    res_payload = {
        "actions": [
            "Increased max Redis pool size from 50 to 200",
            "Restarted cart worker pods gracefully",
        ],
        "runbook_id": runbook_id,
        "runbook_version": "2.1.0",
        "contributing_factors": ["Marketing email sent without cache pre-warming"],
        "root_cause": root_cause,
        "result": "Latency recovered to <50ms, error rate 0%",
        "outcome": "successful",
    }
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=res_payload)
    assert r.status_code == 200, r.text

    client.post(f"/api/incidents/{inc_id}/verify", json={
        "before_metrics": {"error_rate": "42%", "latency": "5200ms"},
        "after_metrics": {"error_rate": "0%", "latency": "48ms"},
        "observations": ["Pool capacity healthy"],
    })
    return inc_id


def create_resolved_and_drafted(client, root_cause: str = "Redis connection pool limit exceeded") -> str:
    inc_id = create_and_resolve_incident(client, root_cause=root_cause)
    r = client.post(f"/api/incidents/{inc_id}/postmortem", json={})
    assert r.status_code == 200, r.text
    return inc_id


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_valid_confirmation(client):
    """
    F12-T01: Valid post-mortem confirmation.
    Transitions status to 'confirmed', sets reviewed_by, generates candidates.
    """
    inc_id = create_resolved_and_drafted(client)

    resp = client.post(
        f"/api/incidents/{inc_id}/postmortem/confirm",
        json={"reviewer": "sre-lead@company.com", "review_notes": "Reviewed and approved without changes"},
        headers={"X-Operator": "sre-lead"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["status"] == "confirmed"
    assert data["incident_id"] == inc_id
    assert data["reviewed_by"] == "sre-lead@company.com"
    assert data["review_notes"] == "Reviewed and approved without changes"
    assert data["confirmed_at"] is not None

    # Memory candidates should be composed
    candidates = data["memory_candidates"]
    assert isinstance(candidates, list)
    assert len(candidates) > 0

    candidate_types = {c["entry_type"] for c in candidates}
    assert "root_cause" in candidate_types
    assert "resolution" in candidate_types


def test_confirmation_with_corrections(client):
    """
    F12-T02: Post-mortem confirmation with engineer corrections.
    Applies overrides, preserves original in audit trail, updates candidates.
    """
    inc_id = create_resolved_and_drafted(client, root_cause="Initial AI draft guess")

    confirm_payload = {
        "reviewer": "staff-sre@company.com",
        "review_notes": "Corrected root cause based on thread dump analysis",
        "corrections": [
            {
                "field": "root_cause",
                "corrected": "Thread leak in connection pool client library v1.0.4",
                "rationale": "Thread dump confirmed leaked pool worker threads",
            },
            {
                "field": "root_cause_confidence",
                "corrected": "confirmed",
                "rationale": "Verified with reproducible heap analysis",
            },
        ],
    }

    resp = client.post(f"/api/incidents/{inc_id}/postmortem/confirm", json=confirm_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["status"] == "confirmed"
    assert data["root_cause"] == "Thread leak in connection pool client library v1.0.4"
    assert data["root_cause_confidence"] == "confirmed"
    assert data["root_cause_source"] == "human"

    # Verify audit corrections list
    assert len(data["corrections"]) == 2
    rc_corr = next(c for c in data["corrections"] if c["field"] == "root_cause")
    assert rc_corr["corrected"] == "Thread leak in connection pool client library v1.0.4"
    assert rc_corr["rationale"] == "Thread dump confirmed leaked pool worker threads"

    # Memory candidate should reflect the corrected root cause
    rc_candidate = next(c for c in data["memory_candidates"] if c["entry_type"] == "root_cause")
    assert rc_candidate["body"] == "Thread leak in connection pool client library v1.0.4"
    assert rc_candidate["confidence"] == "confirmed"


def test_non_correctable_fields_ignored(client):
    """
    F12-T03: Non-correctable fields in corrections list are safely ignored.
    """
    inc_id = create_resolved_and_drafted(client)

    confirm_payload = {
        "reviewer": "sre@company.com",
        "corrections": [
            {
                "field": "id",
                "corrected": "pm-hacked",
                "rationale": "Attempt to change primary key",
            },
            {
                "field": "incident_id",
                "corrected": "INC-OTHER",
                "rationale": "Attempt to change incident ref",
            },
            {
                "field": "summary",
                "corrected": "Updated executive summary of cart-checkout outage",
                "rationale": "Clearer executive framing",
            },
        ],
    }

    resp = client.post(f"/api/incidents/{inc_id}/postmortem/confirm", json=confirm_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # ID and incident_id are unchanged
    assert data["incident_id"] == inc_id
    assert data["summary"] == "Updated executive summary of cart-checkout outage"

    # Only summary correction was accepted
    applied_fields = [c["field"] for c in data["corrections"]]
    assert "summary" in applied_fields
    assert "id" not in applied_fields
    assert "incident_id" not in applied_fields


def test_confirmation_without_draft(client):
    """
    F12-T04: Confirming when no draft exists returns 404 POSTMORTEM_NOT_FOUND.
    """
    inc_id = create_and_resolve_incident(client)
    # Note: no draft created via POST /postmortem

    resp = client.post(f"/api/incidents/{inc_id}/postmortem/confirm", json={})
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["code"] == "POSTMORTEM_NOT_FOUND"


def test_unresolved_incident_precondition(client):
    """
    F12-T05: Confirming an unresolved incident returns 409 INCIDENT_NOT_RESOLVED.
    """
    # Create incident but do not resolve it
    r = client.post("/api/incidents", json=INCIDENT_PAYLOAD)
    assert r.status_code == 201
    inc_id = r.json()["id"]

    resp = client.post(f"/api/incidents/{inc_id}/postmortem/confirm", json={})
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "INCIDENT_NOT_RESOLVED"


def test_idempotent_confirmation(client):
    """
    F12-T06: Calling confirm on an already-confirmed post-mortem is idempotent.
    Returns 200 and retains the original reviewer and confirmation timestamp.
    """
    inc_id = create_resolved_and_drafted(client)

    # First confirm
    r1 = client.post(
        f"/api/incidents/{inc_id}/postmortem/confirm",
        json={"reviewer": "first-reviewer", "review_notes": "First pass"},
    )
    assert r1.status_code == 200
    first_data = r1.json()
    first_timestamp = first_data["confirmed_at"]
    first_reviewer = first_data["reviewed_by"]

    # Second confirm with different reviewer
    r2 = client.post(
        f"/api/incidents/{inc_id}/postmortem/confirm",
        json={"reviewer": "second-reviewer", "review_notes": "Second pass attempt"},
    )
    assert r2.status_code == 200
    second_data = r2.json()

    # Original confirmation attestation must be preserved
    assert second_data["confirmed_at"] == first_timestamp
    assert second_data["reviewed_by"] == first_reviewer
    assert second_data["review_notes"] == "First pass"


def test_candidate_composition_types(client):
    """
    F12-T07: Memory candidates composition produces expected candidate types.
    Checks root_cause, resolution, lesson, prevention, and runbook_outcome.
    """
    inc_id = create_resolved_and_drafted(client)

    resp = client.post(f"/api/incidents/{inc_id}/postmortem/confirm", json={})
    assert resp.status_code == 200
    data = resp.json()

    candidates = data["memory_candidates"]
    types = [c["entry_type"] for c in candidates]

    assert "root_cause" in types
    assert "resolution" in types
    assert "lesson" in types
    assert "prevention" in types
    assert "runbook_outcome" in types


def test_unknown_root_cause_exclusion(client):
    """
    F12-T08: Unknown root cause is excluded from memory candidates.
    If root_cause='unknown', no candidate with entry_type='root_cause' is emitted.
    """
    # Create and resolve incident with unknown root cause
    r = client.post("/api/incidents", json=INCIDENT_PAYLOAD)
    inc_id = r.json()["id"]

    client.post(f"/api/incidents/{inc_id}/resolve", json={
        "actions": ["Rebooted host instance"],
        "root_cause": "unknown",
        "result": "Service recovered on new host",
        "outcome": "successful",
    })
    client.post(f"/api/incidents/{inc_id}/verify", json={
        "before_metrics": {"error_rate": "15%"},
        "after_metrics": {"error_rate": "0%"},
    })

    # Generate draft
    client.post(f"/api/incidents/{inc_id}/postmortem", json={})

    # Confirm
    resp = client.post(f"/api/incidents/{inc_id}/postmortem/confirm", json={})
    assert resp.status_code == 200
    data = resp.json()

    candidate_types = [c["entry_type"] for c in data["memory_candidates"]]
    assert "root_cause" not in candidate_types


def test_candidate_provenance_verification(client):
    """
    F12-T09: Every memory candidate carries complete provenance tracing.
    """
    inc_id = create_resolved_and_drafted(client)

    resp = client.post(f"/api/incidents/{inc_id}/postmortem/confirm", json={})
    assert resp.status_code == 200
    data = resp.json()

    for candidate in data["memory_candidates"]:
        prov = candidate.get("provenance")
        assert prov is not None, f"Missing provenance in candidate: {candidate}"
        assert "postmortem_id" in prov
        assert "source" in prov
        assert candidate["source_incident_ref"] == inc_id
        assert candidate["service"] == "cart-checkout"


def test_get_after_confirmation(client):
    """
    F12-T10: GET /postmortem after confirmation returns confirmed record
    with corrections and memory candidates intact.
    """
    inc_id = create_resolved_and_drafted(client)

    client.post(
        f"/api/incidents/{inc_id}/postmortem/confirm",
        json={
            "reviewer": "lead-sre",
            "review_notes": "All checks passed",
            "corrections": [
                {"field": "impact", "corrected": "120 customers affected, $1,400 revenue delayed"}
            ],
        },
    )

    get_resp = client.get(f"/api/incidents/{inc_id}/postmortem")
    assert get_resp.status_code == 200
    data = get_resp.json()

    assert data["status"] == "confirmed"
    assert data["impact"] == "120 customers affected, $1,400 revenue delayed"
    assert len(data["corrections"]) == 1
    assert len(data["memory_candidates"]) > 0


def test_review_notes_persisted(client):
    """
    F12-T11: Engineer review notes are persisted and returned.
    """
    inc_id = create_resolved_and_drafted(client)

    notes = "Confirmed with database admin that connection pool was undersized for peak hour."
    resp = client.post(
        f"/api/incidents/{inc_id}/postmortem/confirm",
        json={"review_notes": notes, "reviewer": "oncall-lead"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["review_notes"] == notes


def test_incident_not_found(client):
    """
    F12-T12: Confirm on non-existent incident returns 404 INCIDENT_NOT_FOUND.
    """
    resp = client.post("/api/incidents/INC-DOES-NOT-EXIST/postmortem/confirm", json={})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "INCIDENT_NOT_FOUND"

"""
Feature 09 — Human Decision and Resolution Tests.

Conforms to PRD §12.8 (FR-049–FR-052, FR-044), UC-07, W-11, W-12.

Test matrix:
  F09-T01  accepted recommendation            — followed status, outcome=successful
  F09-T02  rejected recommendation            — skipped status
  F09-T03  alternative action                 — actions differ from recommendations
  F09-T04  attempted-failed recommendation    — attempted_failed status
  F09-T05  successful resolution              — outcome=successful, state=resolved
  F09-T06  ineffective resolution             — outcome=ineffective
  F09-T07  inconclusive resolution            — outcome=inconclusive, low-confidence
  F09-T08  unknown resolution (FR-051)        — outcome=unknown, low-confidence marker
  F09-T09  close without resolution (FR-052)  — explicit flag + reason
  F09-T10  duplicate resolve (idempotency)    — second POST returns existing record
  F09-T11  invalid state (already closed)     — 409 ALREADY_CLOSED
  F09-T12  missing actions without flag       — 422 validation error
  F09-T13  missing outcome without flag       — 422 validation error
  F09-T14  invalid outcome value              — 422 validation error
  F09-T15  close_without_resolution without reason — 422 validation error
  F09-T16  incident not found                 — 404 INCIDENT_NOT_FOUND
  F09-T17  GET /resolution — returns record   — 200
  F09-T18  GET /resolution — not found yet    — 404 RESOLUTION_NOT_FOUND
  F09-T19  recommendation outcomes captured   — all three categories stored (FR-050)
  F09-T20  root_cause 'unknown' valid (FR-051) — no 422
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INCIDENT_PAYLOAD = {
    "symptom_description": (
        "Payment API is throwing connection pool exhausted errors. "
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


def minimal_resolve_payload(actions=None, outcome="successful", **kwargs):
    payload = {
        "actions": actions or ["Identified stale connections and terminated them."],
        "outcome": outcome,
    }
    payload.update(kwargs)
    return payload


# ===========================================================================
# F09-T01 — Accepted recommendation
# ===========================================================================

def test_accepted_recommendation(client):
    """Engineer followed a recommendation; it worked (FR-050)."""
    inc_id = create_incident(client)
    payload = minimal_resolve_payload(
        actions=["Followed REC-INC-2026-0001-002: terminated stale connections."],
        outcome="successful",
        recommendation_outcomes=[
            {
                "recommendation_id": "REC-INC-2026-0001-002",
                "status": "followed",
                "note": "Procedure worked as expected.",
            }
        ],
        root_cause="database_connection_exhaustion",
        operator_notes="Resolved in 8 minutes.",
    )
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["outcome"] == "successful"
    assert data["incident_id"] == inc_id
    assert data["incident_status"] == "resolved"
    assert data["resolution_status"] == "resolved"
    assert data["root_cause"] == "database_connection_exhaustion"

    rec_outcomes = data["recommendation_outcomes"]
    assert len(rec_outcomes) == 1
    assert rec_outcomes[0]["status"] == "followed"
    assert rec_outcomes[0]["recommendation_id"] == "REC-INC-2026-0001-002"


# ===========================================================================
# F09-T02 — Rejected recommendation (skipped)
# ===========================================================================

def test_rejected_recommendation(client):
    """Engineer skipped a recommendation (FR-050)."""
    inc_id = create_incident(client)
    payload = minimal_resolve_payload(
        actions=["Scaled up connection pool instead."],
        outcome="successful",
        recommendation_outcomes=[
            {
                "recommendation_id": "REC-INC-2026-0001-001",
                "status": "skipped",
                "note": "Opted for faster pool scale-up instead.",
            }
        ],
    )
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["outcome"] == "successful"
    rec_outcomes = data["recommendation_outcomes"]
    assert rec_outcomes[0]["status"] == "skipped"


# ===========================================================================
# F09-T03 — Alternative action (different from any recommendation)
# ===========================================================================

def test_alternative_action(client):
    """Engineer applied an action not in the recommendation set (FR-049)."""
    inc_id = create_incident(client)
    payload = minimal_resolve_payload(
        actions=["Emergency restart of payment-api pods via ops team."],
        outcome="successful",
        root_cause="memory_leak_in_connection_handler",
    )
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "Emergency restart" in data["actions_taken"][0]
    assert data["root_cause"] == "memory_leak_in_connection_handler"
    assert data["outcome"] == "successful"


# ===========================================================================
# F09-T04 — Attempted and failed recommendation
# ===========================================================================

def test_attempted_failed_recommendation(client):
    """Engineer attempted a recommendation but it did not work (FR-050)."""
    inc_id = create_incident(client)
    payload = minimal_resolve_payload(
        actions=[
            "Attempted REC-INC-2026-0001-002: did not resolve.",
            "Escalated to DBA team.",
        ],
        outcome="successful",
        recommendation_outcomes=[
            {
                "recommendation_id": "REC-INC-2026-0001-002",
                "status": "attempted_failed",
                "note": "Connection pool termination did not reduce active count.",
            }
        ],
    )
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    rec_outcomes = data["recommendation_outcomes"]
    assert rec_outcomes[0]["status"] == "attempted_failed"
    assert "did not reduce active count" in rec_outcomes[0]["note"]


# ===========================================================================
# F09-T05 — Successful resolution
# ===========================================================================

def test_successful_resolution(client):
    """Outcome=successful moves incident to resolved state (FR-049)."""
    inc_id = create_incident(client)
    r = client.post(
        f"/api/incidents/{inc_id}/resolve",
        json=minimal_resolve_payload(outcome="successful"),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["outcome"] == "successful"
    assert data["outcome_confidence"] == "high"
    assert data["incident_status"] == "resolved"

    # Verify incident GET reflects resolved state
    inc_r = client.get(f"/api/incidents/{inc_id}")
    assert inc_r.json()["status"] == "resolved"


# ===========================================================================
# F09-T06 — Ineffective resolution
# ===========================================================================

def test_ineffective_resolution(client):
    """Outcome=ineffective is a valid resolution outcome."""
    inc_id = create_incident(client)
    r = client.post(
        f"/api/incidents/{inc_id}/resolve",
        json=minimal_resolve_payload(outcome="ineffective"),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["outcome"] == "ineffective"
    assert data["incident_status"] == "resolved"


# ===========================================================================
# F09-T07 — Inconclusive resolution
# ===========================================================================

def test_inconclusive_resolution(client):
    """Outcome=inconclusive carries low-confidence marker (FR-051)."""
    inc_id = create_incident(client)
    r = client.post(
        f"/api/incidents/{inc_id}/resolve",
        json=minimal_resolve_payload(outcome="inconclusive"),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["outcome"] == "inconclusive"
    assert data["outcome_confidence"] == "low"


# ===========================================================================
# F09-T08 — Unknown resolution outcome (FR-051)
# ===========================================================================

def test_unknown_outcome(client):
    """Outcome=unknown is explicitly valid; carries low-confidence marker (FR-051)."""
    inc_id = create_incident(client)
    r = client.post(
        f"/api/incidents/{inc_id}/resolve",
        json=minimal_resolve_payload(outcome="unknown"),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["outcome"] == "unknown"
    assert data["outcome_confidence"] == "low"
    assert data["incident_status"] == "resolved"


# ===========================================================================
# F09-T09 — Close without resolution (FR-052)
# ===========================================================================

def test_close_without_resolution(client):
    """FR-052: incident can be closed without resolution if explicit flag + reason."""
    inc_id = create_incident(client)
    payload = {
        "actions": [],
        "close_without_resolution": True,
        "close_without_resolution_reason": (
            "Incident auto-recovered before investigation began. "
            "No root cause identified."
        ),
    }
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["close_without_resolution"] is True
    assert "auto-recovered" in data["close_without_resolution_reason"]
    assert data["incident_status"] == "resolved"


# ===========================================================================
# F09-T10 — Idempotency: duplicate resolve
# ===========================================================================

def test_duplicate_resolve_is_idempotent(client):
    """Repeated POST /resolve does not create a duplicate record."""
    inc_id = create_incident(client)
    payload = minimal_resolve_payload(outcome="successful")

    r1 = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r1.status_code == 200, r1.text
    r1_id = r1.json()["resolution_id"]

    r2 = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r2.status_code == 200, r2.text
    r2_id = r2.json()["resolution_id"]

    assert r1_id == r2_id, "Second POST must return the same resolution record"


# ===========================================================================
# F09-T11 — Invalid state: already closed (409)
# ===========================================================================

def test_already_closed_returns_409(client):
    """
    Cannot resolve an incident that is already closed.
    The incident must be in 'resolved' first, then we manually close it via transition.
    """
    inc_id = create_incident(client)

    # Resolve it first
    client.post(
        f"/api/incidents/{inc_id}/resolve",
        json=minimal_resolve_payload(outcome="successful"),
    )

    # Transition to closed via the state machine
    client.post(
        f"/api/incidents/{inc_id}/transition",
        json={"new_status": "closed", "actor": "sre-operator"},
    )

    # Second resolve attempt should fail
    r = client.post(
        f"/api/incidents/{inc_id}/resolve",
        json=minimal_resolve_payload(outcome="successful"),
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "ALREADY_CLOSED"


# ===========================================================================
# F09-T12 — Missing actions without close flag (422)
# ===========================================================================

def test_missing_actions_requires_422(client):
    """Without close_without_resolution, actions list must be non-empty."""
    inc_id = create_incident(client)
    payload = {
        "actions": [],
        "outcome": "successful",
    }
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 422, r.text


# ===========================================================================
# F09-T13 — Missing outcome without close flag (422)
# ===========================================================================

def test_missing_outcome_requires_422(client):
    """Without close_without_resolution, outcome is required."""
    inc_id = create_incident(client)
    payload = {
        "actions": ["Did something"],
        # outcome is missing
    }
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 422, r.text


# ===========================================================================
# F09-T14 — Invalid outcome value (422)
# ===========================================================================

def test_invalid_outcome_value(client):
    """An unrecognized outcome string must be rejected with 422."""
    inc_id = create_incident(client)
    payload = minimal_resolve_payload(outcome="fixed_it_lol")
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 422, r.text


# ===========================================================================
# F09-T15 — close_without_resolution without reason (422)
# ===========================================================================

def test_close_without_resolution_requires_reason(client):
    """FR-052: close_without_resolution=True requires close_without_resolution_reason."""
    inc_id = create_incident(client)
    payload = {
        "actions": [],
        "close_without_resolution": True,
        # close_without_resolution_reason is missing
    }
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 422, r.text


# ===========================================================================
# F09-T16 — Incident not found (404)
# ===========================================================================

def test_incident_not_found(client):
    """POST /resolve on non-existent incident returns 404 INCIDENT_NOT_FOUND."""
    r = client.post(
        "/api/incidents/INC-9999-9999/resolve",
        json=minimal_resolve_payload(),
    )
    assert r.status_code == 404, r.text
    assert r.json()["error"]["code"] == "INCIDENT_NOT_FOUND"


# ===========================================================================
# F09-T17 — GET /resolution returns resolution record
# ===========================================================================

def test_get_resolution_returns_record(client):
    """GET /api/incidents/{id}/resolution returns the persisted record."""
    inc_id = create_incident(client)
    payload = minimal_resolve_payload(
        outcome="successful",
        root_cause="connection_pool_exhaustion",
        operator_notes="Fixed in 5 minutes.",
    )
    client.post(f"/api/incidents/{inc_id}/resolve", json=payload)

    r = client.get(f"/api/incidents/{inc_id}/resolution")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["incident_id"] == inc_id
    assert data["outcome"] == "successful"
    assert data["root_cause"] == "connection_pool_exhaustion"
    assert data["operator_notes"] == "Fixed in 5 minutes."
    assert data["incident_status"] == "resolved"


# ===========================================================================
# F09-T18 — GET /resolution — not resolved yet (404)
# ===========================================================================

def test_get_resolution_not_found(client):
    """GET /resolution before any resolve call returns 404 RESOLUTION_NOT_FOUND."""
    inc_id = create_incident(client)
    r = client.get(f"/api/incidents/{inc_id}/resolution")
    assert r.status_code == 404, r.text
    assert r.json()["error"]["code"] == "RESOLUTION_NOT_FOUND"


# ===========================================================================
# F09-T19 — All three recommendation outcome categories captured (FR-050)
# ===========================================================================

def test_all_recommendation_outcome_categories_captured(client):
    """followed, skipped, and attempted_failed all persist correctly (FR-050)."""
    inc_id = create_incident(client)
    payload = minimal_resolve_payload(
        actions=["Applied runbook step 1."],
        outcome="successful",
        recommendation_outcomes=[
            {"recommendation_id": "REC-001", "status": "followed"},
            {"recommendation_id": "REC-002", "status": "skipped"},
            {"recommendation_id": "REC-003", "status": "attempted_failed",
             "note": "Did not reduce error rate."},
        ],
    )
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    statuses = {ro["recommendation_id"]: ro["status"] for ro in data["recommendation_outcomes"]}
    assert statuses["REC-001"] == "followed"
    assert statuses["REC-002"] == "skipped"
    assert statuses["REC-003"] == "attempted_failed"


# ===========================================================================
# F09-T20 — root_cause 'unknown' is valid (FR-051)
# ===========================================================================

def test_root_cause_unknown_is_valid(client):
    """FR-051: 'unknown' is a valid root_cause value — must not be converted."""
    inc_id = create_incident(client)
    payload = minimal_resolve_payload(
        outcome="inconclusive",
        root_cause="unknown",
    )
    r = client.post(f"/api/incidents/{inc_id}/resolve", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["root_cause"] == "unknown"
    assert data["outcome_confidence"] == "low"

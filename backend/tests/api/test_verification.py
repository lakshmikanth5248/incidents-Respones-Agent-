"""
Feature 10 — Resolution Outcome Verification Tests.

Test Matrix:
  F10-T01  successful recovery                — all metrics improved, status=confirmed
  F10-T02  failed recovery (measurements worse) — operator claimed success, metrics degraded, status=failed
  F10-T03  failed recovery (stagnant metrics) — metrics unchanged at failure level, status=failed
  F10-T04  failed recovery (operator ineffective) — operator declared ineffective, verified status=failed
  F10-T05  incomplete evidence (missing after)  — before given but after empty, status=inconclusive
  F10-T06  incomplete evidence (missing before) — after given but before empty, status=inconclusive
  F10-T07  incomplete evidence (disjoint keys)  — no metric key overlap, status=inconclusive
  F10-T08  conflicting metrics                  — some improved, some degraded, status=inconclusive
  F10-T09  unknown outcome                      — operator declared unknown & no telemetry, status=unknown
  F10-T10  no fabricated metric                 — only provided metrics stored, zero hallucinations
  F10-T11  resolution feeds verification        — inherits resolution outcome & links resolution_id
  F10-T12  verification feeds postmortem/memory — to_postmortem_context & to_memory_candidate_context
  F10-T13  GET verification record              — 200 after verify, 404 before verify
  F10-T14  verification idempotency             — repeated calls update existing record smoothly
  F10-T15  verification alias route             — POST /verification works identically to POST /verify
  F10-T16  incident not found                   — 404 for nonexistent incident ID
"""

import pytest
from src.data.models.verification import VerificationRecord


INCIDENT_PAYLOAD = {
    "symptom_description": (
        "Payment API is experiencing high latency and connection pool exhaustion. "
        "Active database connections saturated at 100/100, error rate spiking."
    ),
    "service": "payment-api",
    "environment": "production",
    "severity": "critical",
}


def create_test_incident(client) -> str:
    r = client.post("/api/incidents", json=INCIDENT_PAYLOAD)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Core Scenario Tests
# ---------------------------------------------------------------------------

def test_successful_recovery(client):
    """
    F10-T01: Successful recovery verification.
    Before: error_rate=31%, latency=4.8s, db_connections=100/100
    After: error_rate=2%, latency=420ms, db_connections=38/100
    Expected: verification_status = confirmed, all metrics improved.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {
            "error_rate": "31%",
            "latency": "4.8s",
            "db_connections": "100/100",
        },
        "after_metrics": {
            "error_rate": "2%",
            "latency": "420ms",
            "db_connections": "38/100",
        },
        "observations": ["Worker pool stabilized", "Error spike subsided"],
        "operator_result": "successful",
        "verification_notes": "Telemetry confirms all metrics returned to nominal baselines.",
    }

    resp = client.post(f"/api/incidents/{inc_id}/verify", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["verification_status"] == "confirmed"
    assert data["incident_id"] == inc_id
    assert len(data["observed_changes"]) == 3

    # Verify all metrics marked improved
    directions = {c["metric"]: c["direction"] for c in data["observed_changes"]}
    assert directions["error_rate"] == "improved"
    assert directions["latency"] == "improved"
    assert directions["db_connections"] == "improved"

    # Verify deltas calculated
    deltas = {c["metric"]: c["delta"] for c in data["observed_changes"]}
    assert "-29.0%" in deltas["error_rate"]
    assert "-4380ms" in deltas["latency"]
    assert "-62/100" in deltas["db_connections"]

    # Verify incident verification_status was updated
    inc_resp = client.get(f"/api/incidents/{inc_id}")
    assert inc_resp.json()["verification_status"] == "confirmed"


def test_failed_recovery_measurements_worsened(client):
    """
    F10-T02: Invariant: Do not assume an action worked because engineer marked it successful.
    Engineer claims successful, but measurements show degradation.
    Expected: verification_status = failed.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {
            "error_rate": "31%",
            "latency": "4.8s",
        },
        "after_metrics": {
            "error_rate": "45%",
            "latency": "6.2s",
        },
        "observations": ["Errors still escalating"],
        "operator_result": "successful",  # Contradicts evidence!
    }

    resp = client.post(f"/api/incidents/{inc_id}/verify", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Core invariant enforced
    assert data["verification_status"] == "failed"

    # Observed changes show degradation
    directions = {c["metric"]: c["direction"] for c in data["observed_changes"]}
    assert directions["error_rate"] == "degraded"
    assert directions["latency"] == "degraded"


def test_failed_recovery_stagnant_metrics(client):
    """
    F10-T03: Stagnant failure metrics: values remained unchanged at failure levels.
    Expected: verification_status = failed.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {
            "error_rate": "31%",
            "latency": "4.8s",
        },
        "after_metrics": {
            "error_rate": "31%",
            "latency": "4.8s",
        },
        "operator_result": "inconclusive",
    }

    resp = client.post(f"/api/incidents/{inc_id}/verify", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == "failed"


def test_failed_recovery_operator_ineffective(client):
    """
    F10-T04: Operator declared ineffective and metrics corroborate.
    Expected: verification_status = failed.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {"error_rate": "31%"},
        "after_metrics": {"error_rate": "30.5%"},
        "operator_result": "ineffective",
    }

    resp = client.post(f"/api/incidents/{inc_id}/verify", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == "failed"


def test_incomplete_evidence_missing_after_metrics(client):
    """
    F10-T05: Incomplete evidence: after_metrics omitted.
    Expected: verification_status = inconclusive.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {"error_rate": "31%", "latency": "4.8s"},
        "after_metrics": {},
        "operator_result": "successful",
    }

    resp = client.post(f"/api/incidents/{inc_id}/verify", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == "inconclusive"


def test_incomplete_evidence_missing_before_metrics(client):
    """
    F10-T06: Incomplete evidence: before_metrics omitted.
    Expected: verification_status = inconclusive.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {},
        "after_metrics": {"error_rate": "2%"},
        "operator_result": "successful",
    }

    resp = client.post(f"/api/incidents/{inc_id}/verify", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == "inconclusive"


def test_incomplete_evidence_disjoint_metrics(client):
    """
    F10-T07: Incomplete evidence: disjoint metric keys between before and after.
    Expected: verification_status = inconclusive.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {"cpu_utilization": "95%"},
        "after_metrics": {"disk_io": "20ms"},
        "operator_result": "successful",
    }

    resp = client.post(f"/api/incidents/{inc_id}/verify", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == "inconclusive"


def test_conflicting_metrics(client):
    """
    F10-T08: Conflicting metrics: error rate improved, but latency and CPU severely degraded.
    Expected: verification_status = inconclusive, conflicting assessment documented.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {
            "error_rate": "31%",
            "latency": "420ms",
            "cpu_utilization": "40%",
        },
        "after_metrics": {
            "error_rate": "2%",          # Improved
            "latency": "8.5s",           # Degraded
            "cpu_utilization": "98%",    # Degraded
        },
        "operator_result": "successful",
    }

    resp = client.post(f"/api/incidents/{inc_id}/verify", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["verification_status"] == "inconclusive"

    # Conflicting evidence item exists
    conflict_ev = [e for e in data["evidence"] if e["assessment"] == "conflicting"]
    assert len(conflict_ev) > 0
    assert "improved" in conflict_ev[0]["details"]
    assert "degraded" in conflict_ev[0]["details"]


def test_unknown_outcome(client):
    """
    F10-T09: Unknown outcome: operator stated unknown and no metrics provided.
    Expected: verification_status = unknown.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {},
        "after_metrics": {},
        "operator_result": "unknown",
        "verification_notes": "Unable to verify at this time due to monitoring agent restart.",
    }

    resp = client.post(f"/api/incidents/{inc_id}/verify", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == "unknown"


def test_no_fabricated_metrics(client):
    """
    F10-T10: Invariant: Do not manufacture measurements.
    Only provided metrics are recorded in before_state and after_state.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {"error_rate": "31%"},
        "after_metrics": {"error_rate": "2%"},
    }

    resp = client.post(f"/api/incidents/{inc_id}/verify", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Verify no manufactured metrics
    assert set(data["before_state"].keys()) == {"error_rate"}
    assert set(data["after_state"].keys()) == {"error_rate"}
    assert len(data["observed_changes"]) == 1
    assert data["observed_changes"][0]["metric"] == "error_rate"

    # Ensure other typical metrics were NOT injected
    for forbidden in ("latency", "cpu", "memory", "db_connections", "availability"):
        assert forbidden not in data["before_state"]
        assert forbidden not in data["after_state"]


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

def test_resolution_feeds_verification(client):
    """
    F10-T11: Integration: Resolution feeds verification.
    When an incident has an existing resolution record, verification automatically:
      1. Links resolution_id
      2. Uses resolution.outcome if operator_result is not passed
      3. References resolution actions in evidence
    """
    inc_id = create_test_incident(client)

    # 1. Resolve incident via Feature 9 endpoint
    res_payload = {
        "actions": ["Rolled back connection pool configuration to v1.2", "Cleared hung connections"],
        "outcome": "successful",
        "root_cause": "Pool size exhaustion",
    }
    res_resp = client.post(f"/api/incidents/{inc_id}/resolve", json=res_payload)
    assert res_resp.status_code == 200, res_resp.text
    resolution_id = res_resp.json()["resolution_id"]

    # 2. Verify outcome WITHOUT explicitly passing operator_result
    verify_payload = {
        "before_metrics": {"error_rate": "31%", "latency": "4.8s"},
        "after_metrics": {"error_rate": "2%", "latency": "420ms"},
    }
    verify_resp = client.post(f"/api/incidents/{inc_id}/verify", json=verify_payload)
    assert verify_resp.status_code == 200, verify_resp.text
    data = verify_resp.json()

    # Verified feeds from resolution
    assert data["resolution_id"] == resolution_id
    assert data["operator_result"] == "successful"
    assert data["verification_status"] == "confirmed"

    # Resolution evidence captured
    res_ev = [e for e in data["evidence"] if e["source"] == "resolution_record"]
    assert len(res_ev) == 1
    assert "Rolled back connection pool" in res_ev[0]["details"]


def test_verification_feeds_postmortem_and_memory():
    """
    F10-T12: Integration: Verification feeds post-mortem and memory candidate.
    Tests model serialization helpers.
    """
    rec_confirmed = VerificationRecord(
        id="ver-001",
        incident_id="inc-001",
        verification_status="confirmed",
        operator_result="successful",
        before_state={"error_rate": "31%"},
        after_state={"error_rate": "2%"},
        observed_changes=[{"metric": "error_rate", "details": "dropped 29%"}],
        evidence=[{"source": "metric", "details": "error_rate improved"}],
    )

    pm_context = rec_confirmed.to_postmortem_context()
    assert pm_context["verification_status"] == "confirmed"
    assert pm_context["before_state"] == {"error_rate": "31%"}
    assert pm_context["after_state"] == {"error_rate": "2%"}

    mem_context = rec_confirmed.to_memory_candidate_context()
    assert mem_context["verified_outcome"] == "effective"
    assert mem_context["outcome_confidence"] == "high"

    rec_failed = VerificationRecord(
        id="ver-002",
        incident_id="inc-002",
        verification_status="failed",
        operator_result="ineffective",
    )
    mem_failed = rec_failed.to_memory_candidate_context()
    assert mem_failed["verified_outcome"] == "ineffective"

    rec_inconclusive = VerificationRecord(
        id="ver-003",
        incident_id="inc-003",
        verification_status="inconclusive",
    )
    mem_inconclusive = rec_inconclusive.to_memory_candidate_context()
    assert mem_inconclusive["outcome_confidence"] == "low"


def test_get_verification_record(client):
    """
    F10-T13: GET /api/incidents/{id}/verification endpoint.
    Returns 404 before verification; returns 200 after verification.
    """
    inc_id = create_test_incident(client)

    # 404 before verification
    r_before = client.get(f"/api/incidents/{inc_id}/verification")
    assert r_before.status_code == 404, r_before.text
    assert r_before.json()["error"]["code"] == "VERIFICATION_NOT_FOUND"

    # Verify
    client.post(f"/api/incidents/{inc_id}/verify", json={
        "before_metrics": {"error_rate": "20%"},
        "after_metrics": {"error_rate": "1%"},
    })

    # 200 after verification
    r_after = client.get(f"/api/incidents/{inc_id}/verification")
    assert r_after.status_code == 200, r_after.text
    assert r_after.json()["verification_status"] == "confirmed"


def test_verification_idempotency(client):
    """
    F10-T14: Verification idempotency.
    Subsequent verification calls on the same incident update the existing record cleanly.
    """
    inc_id = create_test_incident(client)

    payload_1 = {
        "before_metrics": {"error_rate": "31%"},
        "after_metrics": {"error_rate": "40%"},
    }
    r1 = client.post(f"/api/incidents/{inc_id}/verify", json=payload_1)
    assert r1.status_code == 200
    assert r1.json()["verification_status"] == "failed"
    ver_id = r1.json()["id"]

    # Re-verify with updated telemetry showing eventual recovery
    payload_2 = {
        "before_metrics": {"error_rate": "31%"},
        "after_metrics": {"error_rate": "1%"},
    }
    r2 = client.post(f"/api/incidents/{inc_id}/verify", json=payload_2)
    assert r2.status_code == 200
    assert r2.json()["verification_status"] == "confirmed"
    assert r2.json()["id"] == ver_id  # Reused same record


def test_verification_alias_route(client):
    """
    F10-T15: Verification route alias.
    POST /api/incidents/{id}/verification works identically to POST /api/incidents/{id}/verify.
    """
    inc_id = create_test_incident(client)

    payload = {
        "before_metrics": {"latency": "4.8s"},
        "after_metrics": {"latency": "420ms"},
    }
    resp = client.post(f"/api/incidents/{inc_id}/verification", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["verification_status"] == "confirmed"


def test_verification_incident_not_found(client):
    """
    F10-T16: Incident not found error handling (404).
    """
    resp = client.post("/api/incidents/inc-nonexistent-1234/verify", json={})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "INCIDENT_NOT_FOUND"

    resp_get = client.get("/api/incidents/inc-nonexistent-1234/verification")
    assert resp_get.status_code == 404
    assert resp_get.json()["error"]["code"] == "INCIDENT_NOT_FOUND"


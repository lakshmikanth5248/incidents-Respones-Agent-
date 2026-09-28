"""
Feature 14 — Memory Experience Browsing, Provenance, and Flagging Tests.

Test Matrix:
  F14-T01  browse by service             — filters experience correctly by service name
  F14-T02  browse by failure mode        — filters experience by failure mode query
  F14-T03  browse by outcome             — filters experience by outcome label (successful, ineffective, etc.)
  F14-T04  browse by entry type          — filters experience by entry_type
  F14-T05  include/exclude flagged       — include_flagged=false excludes flagged entries, true retains them
  F14-T06  unknown entry flag            — 404 NOT_FOUND when flagging nonexistent entry
  F14-T07  hindsight unavailable         — 503 HINDSIGHT_UNAVAILABLE when memory service is down
  F14-T08  provenance completeness       — returned entries carry entry_id, source incident, timestamp, outcome, confidence, flag state
  F14-T09  flag persistence              — flag status survives subsequent queries
  F14-T10  flag deprioritization         — flagged entries receive score penalty in recall ranking
  F14-T11  invalid flag type             — 400 INVALID_FLAG_TYPE for disallowed flag categories
"""

import pytest
from src.memory.test_double import HindsightTestDouble


def seed_test_memories(double: HindsightTestDouble):
    """Seed diverse memory entries for filtering tests."""
    double.seed_entries([
        {
            "entry_type": "root_cause",
            "service": "cart-checkout",
            "component": "redis-pool",
            "body": "Redis pool exhausted due to unclosed connection leak in cart checkout.",
            "outcome_label": "successful",
            "confidence": "confirmed",
            "source_incident_ref": "INC-CART-001",
        },
        {
            "entry_type": "resolution_procedure",
            "service": "cart-checkout",
            "component": "redis-pool",
            "body": "Restarted cart worker pods and expanded pool size to 200.",
            "outcome_label": "successful",
            "confidence": "confirmed",
            "source_incident_ref": "INC-CART-001",
        },
        {
            "entry_type": "failed_action",
            "service": "cart-checkout",
            "body": "Increased timeout without expanding pool size — ineffective.",
            "outcome_label": "ineffective",
            "confidence": "confirmed",
            "source_incident_ref": "INC-CART-001",
        },
        {
            "entry_type": "root_cause",
            "service": "payment-api",
            "component": "postgres",
            "body": "Postgres connection deadlock on transaction ledger rows.",
            "outcome_label": "successful",
            "confidence": "confirmed",
            "source_incident_ref": "INC-PAY-002",
        },
        {
            "entry_type": "lesson",
            "service": "payment-api",
            "body": "Ensure deadlock retry logic uses exponential backoff.",
            "outcome_label": None,
            "confidence": "probable",
            "source_incident_ref": "INC-PAY-002",
        },
    ])


def test_browse_by_service(client, reset_memory_double):
    """F14-T01: Browse experience filtered by service."""
    seed_test_memories(reset_memory_double)

    resp = client.get("/api/memory/experience?service=cart-checkout")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert all(e["service"] == "cart-checkout" for e in data["entries"])


def test_browse_by_failure_mode(client, reset_memory_double):
    """F14-T02: Browse experience filtered by failure mode / query."""
    seed_test_memories(reset_memory_double)

    resp = client.get("/api/memory/experience?failure_mode_label=deadlock")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any("deadlock" in e["body"].lower() for e in data["entries"])


def test_browse_by_outcome(client, reset_memory_double):
    """F14-T03: Browse experience filtered by outcome label."""
    seed_test_memories(reset_memory_double)

    resp = client.get("/api/memory/experience?outcome_label=ineffective")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["entries"][0]["outcome_label"] == "ineffective"


def test_browse_by_entry_type(client, reset_memory_double):
    """F14-T04: Browse experience filtered by entry type."""
    seed_test_memories(reset_memory_double)

    resp = client.get("/api/memory/experience?entry_type=lesson")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["entries"][0]["entry_type"] == "lesson"


def test_include_and_exclude_flagged(client, reset_memory_double):
    """F14-T05: include_flagged=false excludes flagged entries."""
    mem_id = reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "billing",
        "body": "Outdated tax calculation API returned 500 error",
        "source_incident_ref": "INC-BILL-001",
    })

    # Flag the entry
    flag_resp = client.post(
        f"/api/memory/experience/{mem_id}/flag",
        json={
            "flag_type": "outdated",
            "reason": "Tax service was replaced by Avalara integration",
            "note": "Legacy vendor decommissioned",
        },
    )
    assert flag_resp.status_code == 200

    # Browse with include_flagged=true (default)
    r1 = client.get("/api/memory/experience?service=billing&include_flagged=true")
    assert r1.status_code == 200
    assert r1.json()["total"] == 1

    # Browse with include_flagged=false
    r2 = client.get("/api/memory/experience?service=billing&include_flagged=false")
    assert r2.status_code == 200
    assert r2.json()["total"] == 0


def test_flag_unknown_entry(client, reset_memory_double):
    """F14-T06: Flagging nonexistent entry returns 404 NOT_FOUND."""
    resp = client.post(
        "/api/memory/experience/MEM-NONEXISTENT-999/flag",
        json={
            "flag_type": "incorrect",
            "reason": "This memory should not exist",
        },
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_hindsight_unavailable_on_browse_and_flag(client, reset_memory_double):
    """F14-T07: 503 HINDSIGHT_UNAVAILABLE when memory service is down."""
    mem_id = reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "search",
        "body": "Search cluster node OOM",
        "source_incident_ref": "INC-SEARCH-001",
    })

    reset_memory_double.set_mode("unavailable")

    # Browse under outage
    browse_resp = client.get("/api/memory/experience?service=search")
    assert browse_resp.status_code == 503
    assert browse_resp.json()["error"]["code"] == "HINDSIGHT_UNAVAILABLE"

    # Flag under outage
    flag_resp = client.post(
        f"/api/memory/experience/{mem_id}/flag",
        json={"flag_type": "incorrect", "reason": "Test under outage"},
    )
    assert flag_resp.status_code == 503
    assert flag_resp.json()["error"]["code"] == "HINDSIGHT_UNAVAILABLE"


def test_provenance_completeness(client, reset_memory_double):
    """F14-T08: Every displayed memory entry carries complete provenance metadata."""
    mem_id = reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "orders-api",
        "component": "order-processor",
        "body": "Kafka partition rebalance stall triggered order processing lag.",
        "outcome_label": "successful",
        "confidence": "confirmed",
        "source_incident_ref": "INC-ORD-777",
    })

    resp = client.get("/api/memory/experience?service=orders-api")
    assert resp.status_code == 200
    entry = resp.json()["entries"][0]

    assert entry["entry_id"] == mem_id
    assert entry["source_incident_ref"] == "INC-ORD-777"
    assert entry["service"] == "orders-api"
    assert entry["component"] == "order-processor"
    assert entry["confidence"] == "confirmed"
    assert entry["outcome_label"] == "successful"
    assert "retained_at" in entry
    assert "flagged" in entry


def test_flag_persistence(client, reset_memory_double):
    """F14-T09: Flag state persists on the entry across subsequent calls."""
    mem_id = reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "auth-service",
        "body": "JWKS signing key mismatch",
        "source_incident_ref": "INC-AUTH-001",
    })

    # Flag as incorrect
    client.post(
        f"/api/memory/experience/{mem_id}/flag",
        json={
            "flag_type": "incorrect",
            "reason": "Root cause was clock skew, not key mismatch",
            "note": "Verified by NTP audit",
        },
    )

    # Fetch and verify flag persisted
    resp = client.get("/api/memory/experience?service=auth-service")
    assert resp.status_code == 200
    entry = resp.json()["entries"][0]
    assert entry["flagged"] is not None
    assert entry["flagged"]["flag_type"] == "incorrect"
    assert entry["flagged"]["reason"] == "Root cause was clock skew, not key mismatch"
    assert entry["flagged"]["note"] == "Verified by NTP audit"


def test_flag_deprioritization_in_ranking(client, reset_memory_double):
    """
    F14-T10: Flagged memory is deprioritized in recall ranking rather than silently deleted.
    """
    # Seed two identical relevance memories
    id1 = reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "gateway",
        "body": "TLS handshake timeout on edge router due to cipher mismatch",
        "outcome_label": "successful",
        "confidence": "confirmed",
        "source_incident_ref": "INC-GW-01",
    })
    id2 = reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "gateway",
        "body": "TLS handshake failure on edge router due to upstream certificate expiry",
        "outcome_label": "successful",
        "confidence": "confirmed",
        "source_incident_ref": "INC-GW-02",
    })

    # Flag id1 as outdated
    client.post(
        f"/api/memory/experience/{id1}/flag",
        json={
            "flag_type": "outdated",
            "reason": "Cipher suite was deprecated in 2024",
        },
    )

    # Recall for gateway TLS
    recall_resp = client.post("/api/memory/recall", json={
        "service": "gateway",
        "query": "TLS handshake timeout edge router",
        "limit": 5,
    })
    assert recall_resp.status_code == 200
    data = recall_resp.json()
    entries = data["entries"]

    # Both are returned (not deleted)
    returned_ids = [e["entry_id"] for e in entries]
    assert id1 in returned_ids
    assert id2 in returned_ids

    # But unflagged entry ranks higher than the flagged entry
    entry1 = next(e for e in entries if e["entry_id"] == id1)
    entry2 = next(e for e in entries if e["entry_id"] == id2)
    assert entry2["relevance_score"] > entry1["relevance_score"]
    assert "Flagged as outdated" in entry1["relevance_basis"]


def test_invalid_flag_type(client, reset_memory_double):
    """F14-T11: Invalid flag type is rejected with 422 or 400."""
    mem_id = reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "api",
        "body": "Test memory",
        "source_incident_ref": "INC-01",
    })

    resp = client.post(
        f"/api/memory/experience/{mem_id}/flag",
        json={"flag_type": "bogus_type", "reason": "Bad flag"},
    )
    assert resp.status_code in [400, 422]

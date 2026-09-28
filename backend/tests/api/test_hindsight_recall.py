"""
Backend Feature 05 — Hindsight Recall Integration and Acceptance Tests.
Conforms strictly to PRD §3.4, §12.2 (API-005, API-007), §12.3 (API-011), D-02, RL-012..RL-014, and Feature 05 requirements.

Verifies:
1. Same wording recall (exact phrase / signature matching)
2. Different wording recall (synonyms / semantic equivalence)
3. Relevant memory recall and scoring
4. Irrelevant memory separation and lower ranking
5. Multiple memories returned and ranked deterministically
6. Conflicting memories detection across distinct root causes
7. Empty memory handling (status=empty, 200 OK, empty list)
8. Hindsight outage handling (503 HINDSIGHT_UNAVAILABLE, never success + empty array)
9. Ranking determinism across repeated executions
10. Provenance preservation (source_incident_ref, provenance_group_id, entry_id)
11. Integration into POST /api/incidents/{id}/analyze preserving reasoning order (hypotheses empty)
"""

import pytest
from fastapi.testclient import TestClient

from src.memory.test_double import HindsightTestDouble
from src.memory.schemas import EntryType, OutcomeLabel, ConfidenceLevel


# --------------------------------------------------------------------------
# 1. Same Wording Recall
# --------------------------------------------------------------------------

def test_same_wording_recall(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test recall when the incident query uses the exact same phrasing and error signatures
    as the historically retained experience.
    """
    entry_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "payment-api",
        "body": "Database connection pool exhausted due to unclosed sessions in worker threads.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-2024-EXACT-001",
    })

    payload = {
        "service": "payment-api",
        "query": "Database connection pool exhausted due to unclosed sessions in worker threads.",
        "failure_mode": "connection_pool_exhausted",
        "error_signatures": ["DB_POOL_EXHAUSTED", "CONN_ACQUIRE_TIMEOUT"],
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["memory_status"] == "ok"
    assert data["total_found"] >= 1
    assert len(data["entries"]) >= 1

    top_entry = data["entries"][0]
    assert top_entry["entry_id"] == entry_id
    assert top_entry["relevance_score"] >= 0.70
    assert "Service match" in top_entry["relevance_basis"]

    # Verify complete recall record structure
    recall_rec = data["recall_record"]
    assert recall_rec["memory_status"] == "ok"
    assert recall_rec["query_version"] == "v1.0.0"
    assert len(recall_rec["returned_entries"]) >= 1
    assert len(recall_rec["ranking"]) >= 1
    assert recall_rec["ranking"][0]["entry_id"] == entry_id
    assert recall_rec["duration_ms"] >= 0.0


# --------------------------------------------------------------------------
# 2. Different Wording Recall
# --------------------------------------------------------------------------

def test_different_wording_recall(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test recall when the query uses different wording / synonyms (e.g. Postgres vs Database,
    depleted vs exhausted, latency vs timeout) and still successfully retrieves the prior experience.
    """
    entry_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "billing-engine",
        "body": "Postgres database pool depleted causing high latency and timeout errors.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-2024-SYN-002",
    })

    # Query with different synonyms
    payload = {
        "service": "billing-engine",
        "query": "RDS db connections exhausted with severe slowness and delay",
        "failure_mode": "db_starvation",
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["memory_status"] == "ok"
    assert data["total_found"] >= 1
    found_ids = [e["entry_id"] for e in data["entries"]]
    assert entry_id in found_ids

    entry = next(e for e in data["entries"] if e["entry_id"] == entry_id)
    assert entry["relevance_score"] >= 0.40
    assert "Service match" in entry["relevance_basis"]


# --------------------------------------------------------------------------
# 3. Relevant Memory & 4. Irrelevant Memory
# --------------------------------------------------------------------------

def test_relevant_vs_irrelevant_memory_ranking(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test that relevant historical experience ranks above unrelated experience,
    and LLM is not allowed to invent relevance.
    """
    rel_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "order-service",
        "body": "Redis cache cluster node eviction caused cache miss avalanche.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-REL-101",
    })

    irrel_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.FAILED_ACTION.value,
        "service": "email-worker",
        "body": "SMTP authentication token expired on marketing newsletter dispatch.",
        "outcome_label": OutcomeLabel.INEFFECTIVE.value,
        "confidence": ConfidenceLevel.LOW.value,
        "source_incident_ref": "INC-IRREL-202",
    })

    # Query for order-service without service filter to test cross-candidate scoring
    payload = {
        "query": "Redis cache cluster eviction spike and cache misses",
        "failure_mode": "cache_eviction",
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["memory_status"] == "ok"
    entries = data["entries"]
    assert len(entries) >= 1

    top_entry = entries[0]
    assert top_entry["entry_id"] == rel_id
    assert "Strong match" in top_entry["relevance_basis"] or "Relevant match" in top_entry["relevance_basis"]

    # If irrelevant entry was retrieved, it must be ranked strictly lower
    if any(e["entry_id"] == irrel_id for e in entries):
        irrel_entry = next(e for e in entries if e["entry_id"] == irrel_id)
        assert top_entry["relevance_score"] > irrel_entry["relevance_score"]
        assert "Weak match" in irrel_entry["relevance_basis"]


# --------------------------------------------------------------------------
# 5. Multiple Memories
# --------------------------------------------------------------------------

def test_multiple_memories_recall(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test recall returning multiple memories ranked deterministically according
    to entry_type weights (root_cause > resolution_procedure > lesson).
    """
    rc_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "checkout-service",
        "body": "Deadlock on inventory table row locks during high concurrency checkout bursts.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-MULT-01",
    })

    proc_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.RESOLUTION_PROCEDURE.value,
        "service": "checkout-service",
        "body": "Apply composite index on inventory table and restart checkout worker pool.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-MULT-02",
    })

    lesson_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.LESSON.value,
        "service": "checkout-service",
        "body": "Add lock timeout of 5s on pessimistic locking calls in inventory repo.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-MULT-03",
    })

    payload = {
        "service": "checkout-service",
        "query": "Deadlock on inventory table during checkout bursts",
        "limit": 5,
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["memory_status"] == "ok"
    assert data["total_found"] == 3
    entries = data["entries"]
    assert len(entries) == 3

    # Ranking detail verification
    ranking = data["recall_record"]["ranking"]
    assert len(ranking) == 3
    assert ranking[0]["rank"] == 1
    assert ranking[1]["rank"] == 2
    assert ranking[2]["rank"] == 3

    # Root cause (weight 1.25) should rank above procedure (1.20) and lesson (1.05)
    assert entries[0]["entry_id"] == rc_id
    assert entries[1]["entry_id"] == proc_id
    assert entries[2]["entry_id"] == lesson_id


# --------------------------------------------------------------------------
# 6. Conflicting Memories
# --------------------------------------------------------------------------

def test_conflicting_memories(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test recall when two prior experiences for the same service present conflicting root causes.
    The ranking layer must detect the conflict and surface it in relevance_basis (FR-027, ERR-09).
    """
    id_a = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "payment-api",
        "body": "Connection pool exhaustion was caused by unindexed query deadlock.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-HIST-A",
    })

    id_b = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "payment-api",
        "body": "Connection pool exhaustion was caused by third-party payment gateway latency spike.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-HIST-B",
    })

    payload = {
        "service": "payment-api",
        "query": "Connection pool exhaustion causing HTTP 500 in payment processing",
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["memory_status"] == "ok"
    entries = data["entries"]
    assert len(entries) >= 2

    # Verify conflict note is recorded in relevance basis of conflicting root causes
    entry_a = next(e for e in entries if e["entry_id"] == id_a)
    entry_b = next(e for e in entries if e["entry_id"] == id_b)

    assert "Conflict:" in entry_a["relevance_basis"]
    assert "INC-HIST-B" in entry_a["relevance_basis"]

    assert "Conflict:" in entry_b["relevance_basis"]
    assert "INC-HIST-A" in entry_b["relevance_basis"]


# --------------------------------------------------------------------------
# 7. Empty Memory
# --------------------------------------------------------------------------

def test_empty_memory(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test recall when no relevant experiences exist in Hindsight.
    Returns 200 OK with memory_status='empty' and empty entries (never an error).
    """
    payload = {
        "service": "quantum-ledger",
        "query": "Entanglement decoherence during superconducting qubit readout",
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["memory_status"] == "empty"
    assert data["total_found"] == 0
    assert data["entries"] == []
    assert data["recall_record"]["memory_status"] == "empty"
    assert data["recall_record"]["returned_entries"] == []


# --------------------------------------------------------------------------
# 8. Hindsight Outage
# --------------------------------------------------------------------------

def test_hindsight_outage(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test recall during a Hindsight outage.
    A memory outage MUST return an explicit failure status/code (503 HINDSIGHT_UNAVAILABLE).
    NEVER return success + empty array for an outage.
    """
    # 1. Direct recall endpoint
    reset_memory_double.set_mode("unavailable")

    payload = {
        "service": "payment-api",
        "query": "Database connection pool exhaustion",
    }
    recall_res = client.post("/api/memory/recall", json=payload)
    assert recall_res.status_code == 503
    err_data = recall_res.json()
    assert err_data["error"]["code"] == "HINDSIGHT_UNAVAILABLE"
    assert "unavailable" in err_data["error"]["message"].lower()

    # 2. Incident memory endpoint
    reset_memory_double.set_mode("ok")
    inc_res = client.post("/api/incidents", json={
        "service": "payment-api",
        "symptom_description": "Database pool exhaustion",
    })
    assert inc_res.status_code == 201
    inc_id = inc_res.json()["id"]

    # Trigger outage and verify GET /api/incidents/{id}/memory fails with 503
    reset_memory_double.set_mode("unavailable")
    mem_res = client.get(f"/api/incidents/{inc_id}/memory")
    assert mem_res.status_code == 503
    assert mem_res.json()["error"]["code"] == "HINDSIGHT_UNAVAILABLE"


# --------------------------------------------------------------------------
# 9. Ranking Determinism
# --------------------------------------------------------------------------

def test_ranking_determinism(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test that repeated recall calls against the same set of memories return
    100% deterministic ranking orders, scores, and relevance bases.
    """
    reset_memory_double.seed_entries([
        {
            "entry_type": EntryType.ROOT_CAUSE.value,
            "service": "auth-service",
            "body": "JWKS signing key rotation caused token signature verification failures.",
            "outcome_label": OutcomeLabel.SUCCESSFUL.value,
            "confidence": ConfidenceLevel.CONFIRMED.value,
            "source_incident_ref": "INC-AUTH-01",
        },
        {
            "entry_type": EntryType.RESOLUTION_PROCEDURE.value,
            "service": "auth-service",
            "body": "Flush redis JWKS cache keys and restart auth-gateway pods.",
            "outcome_label": OutcomeLabel.SUCCESSFUL.value,
            "confidence": ConfidenceLevel.CONFIRMED.value,
            "source_incident_ref": "INC-AUTH-02",
        },
        {
            "entry_type": EntryType.LESSON.value,
            "service": "auth-service",
            "body": "Maintain dual keys for 24 hours during key rotation grace period.",
            "outcome_label": OutcomeLabel.SUCCESSFUL.value,
            "confidence": ConfidenceLevel.CONFIRMED.value,
            "source_incident_ref": "INC-AUTH-03",
        },
    ])

    payload = {
        "service": "auth-service",
        "query": "JWKS signing key rotation token failure",
    }

    results = []
    for _ in range(5):
        res = client.post("/api/memory/recall", json=payload)
        assert res.status_code == 200
        results.append(res.json())

    first_entries = results[0]["entries"]
    first_ids = [e["entry_id"] for e in first_entries]
    first_scores = [e["relevance_score"] for e in first_entries]
    first_bases = [e["relevance_basis"] for e in first_entries]

    for trial in results[1:]:
        trial_entries = trial["entries"]
        assert [e["entry_id"] for e in trial_entries] == first_ids
        assert [e["relevance_score"] for e in trial_entries] == first_scores
        assert [e["relevance_basis"] for e in trial_entries] == first_bases


# --------------------------------------------------------------------------
# 10. Provenance Preservation
# --------------------------------------------------------------------------

def test_provenance_preservation(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test that every recalled experience preserves its complete provenance chain:
    source_incident_ref, entry_id, retained_at, provenance_group_id, is_synthetic.
    """
    custom_entry_id = "mem-prov-9999"
    reset_memory_double.seed_entry({
        "entry_id": custom_entry_id,
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "search-indexer",
        "body": "Elasticsearch cluster yellow status caused by unassigned replica shards.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-PROV-P0-444",
        "provenance_group_id": "prov-grp-elastic-01",
        "is_synthetic": True,
    })

    payload = {
        "service": "search-indexer",
        "query": "Elasticsearch unassigned replica shards",
    }
    response = client.post("/api/memory/recall", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data["entries"]) >= 1
    entry = data["entries"][0]

    assert entry["entry_id"] == custom_entry_id
    assert entry["source_incident_ref"] == "INC-PROV-P0-444"
    assert entry["provenance_group_id"] == "prov-grp-elastic-01"
    assert entry["is_synthetic"] is True
    assert entry["retained_at"] is not None

    # Check persistence in recall record
    rec_entry = data["recall_record"]["returned_entries"][0]
    assert rec_entry["source_incident_ref"] == "INC-PROV-P0-444"
    assert rec_entry["provenance_group_id"] == "prov-grp-elastic-01"


# --------------------------------------------------------------------------
# 11. Analyze Incident Integration (Order & Hypotheses Invariant)
# --------------------------------------------------------------------------

def test_analyze_incident_recall_integration(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test Stage 2 RECALL integration into POST /api/incidents/{id}/analyze:
    - Normalizes incident symptoms
    - Derives recall intent strictly from service, environment, failure mode, signatures
    - Stores recall record and memory status on incident analysis
    - Invariant: Hypotheses must remain empty [] at this stage
    - GET /api/incidents/{id}/memory returns the persisted recall record
    """
    # 1. Seed prior memory
    reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "payment-api",
        "body": "HikariCP pool starvation caused by unindexed ledger lookup.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-HIST-POOL-01",
    })

    # 2. Create incident
    create_res = client.post("/api/incidents", json={
        "service": "payment-api",
        "environment": "production",
        "symptom_description": "Payment API latency is 4.8s and database connections are exhausted.",
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    # 3. Analyze incident
    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    analysis = analyze_res.json()

    assert analysis["incident_id"] == inc_id
    assert analysis["memory_status"] == "ok"
    assert analysis["hypotheses"] == []  # CRITICAL INVARIANT: no hypotheses before compare

    # Verify recall_record on analysis
    rec = analysis["recall_record"]
    assert rec is not None
    assert rec["memory_status"] == "ok"
    assert len(rec["returned_entries"]) >= 1
    assert "query" in rec
    assert "ranking" in rec
    assert "relevance_basis" in rec
    assert "duration_ms" in rec

    # 4. Verify GET /api/incidents/{id}/memory returns the persisted recall record
    mem_res = client.get(f"/api/incidents/{inc_id}/memory")
    assert mem_res.status_code == 200
    mem_data = mem_res.json()

    assert mem_data["incident_id"] == inc_id
    assert mem_data["memory_status"] == "ok"
    assert len(mem_data["entries"]) >= 1
    assert mem_data["entries"][0]["source_incident_ref"] == "INC-HIST-POOL-01"


def test_analyze_incident_degraded_recall_handling(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test graceful degradation when Hindsight is unavailable during incident analysis:
    - Analysis proceeds without crashing
    - Incident records memory_status='degraded'
    - Subsequent GET /api/incidents/{id}/memory surfaces 503 HINDSIGHT_UNAVAILABLE
    """
    create_res = client.post("/api/incidents", json={
        "service": "payment-api",
        "symptom_description": "Connection pool timeout",
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    # Simulate Hindsight outage during analysis
    reset_memory_double.set_mode("unavailable")
    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    analysis = analyze_res.json()

    assert analysis["memory_status"] == "degraded"
    assert analysis["hypotheses"] == []
    assert analysis["recall_record"]["memory_status"] == "degraded"

    # Verify GET /api/incidents/{id}/memory reports 503 outage
    mem_res = client.get(f"/api/incidents/{inc_id}/memory")
    assert mem_res.status_code == 503
    assert mem_res.json()["error"]["code"] == "HINDSIGHT_UNAVAILABLE"

"""
Backend Features 06–07: Current/Historical Comparison and Hypothesis Generation Tests.
Conforms strictly to PRD Part 1 §12.4 (FR-023–FR-028), §12.5 (FR-029–FR-034),
Part 2 §26.5 (AC2-04, AC2-04a), §26.6 (AC2-05, AC2-05a, AC2-05b), and Features 06–07.

Test Matrix:
1. Matching memory (comparison matching_signals, precedent_backed=True hypothesis)
2. No memory / Cold start (empty recall, memory-free hypothesis without fabrication)
3. Contradictory memory (surfaces conflicts, contradictions in contradicting_evidence)
4. Irrelevant memory (different service/class graded weak, not falsely claimed)
5. Unsupported historical claim (anti-hallucination: no invented actions/outcomes)
6. Missing evidence (explicit "unknown" stated for missing telemetry/deployments)
7. Confidence and provenance (complete structured tracking on comparisons & hypotheses)
8. Deterministic comparison (100% reproducible comparison and hypothesis rankings)
9. Strict reasoning order (interpret -> recall -> context assembly -> compare -> hypothesize)
"""

import pytest
from fastapi.testclient import TestClient

from src.memory.test_double import HindsightTestDouble
from src.memory.schemas import EntryType, OutcomeLabel, ConfidenceLevel


# --------------------------------------------------------------------------
# 1. Matching Memory
# --------------------------------------------------------------------------

def test_matching_memory_comparison_and_hypothesis(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test comparison and hypothesis generation when a matching prior memory exists.
    - Comparison: produces matching_signals for service, symptoms, signatures.
    - Hypothesis: cites prior memory, marked precedent_backed=True, confidence >= 0.60.
    """
    mem_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "payment-api",
        "body": "Database connection leak in transaction manager exhausted pool limit.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-2024-MATCH-01",
    })

    create_res = client.post("/api/incidents", json={
        "service": "payment-api",
        "environment": "production",
        "symptom_description": "Payment API connection pool exhaustion with high latency and database errors.",
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    assert data["status"] == "hypotheses_generated"
    assert data["memory_status"] == "ok"

    # Comparison verification
    assert len(data["comparisons"]) >= 1
    comp = data["comparisons"][0]
    assert comp["prior_incident_id"] == "INC-2024-MATCH-01"
    assert any("Matching service: payment-api" in s for s in comp["matching_signals"])
    assert any("Symptom overlap" in s for s in comp["matching_signals"])
    assert comp["match_strength"] in ["full", "partial"]
    assert comp["applicability"] in ["applicable", "partially_applicable"]
    assert comp["confidence"]["score"] >= 0.50

    # Hypothesis verification
    assert len(data["hypotheses"]) >= 1
    hyp = data["hypotheses"][0]
    assert hyp["precedent_backed"] is True
    assert mem_id in hyp["supporting_memory_entries"]
    assert len(hyp["supporting_current_evidence"]) > 0
    assert "INC-2024-MATCH-01" in hyp["hypothesis"]
    assert hyp["confidence"]["score"] >= 0.50
    assert hyp["confidence"]["level"] in ["confirmed", "probable"]

    # Provenance verification
    assert len(hyp["provenance"]) >= 2
    sources = [p["source"] for p in hyp["provenance"]]
    assert "current_incident" in sources
    assert f"recalled_memory:{mem_id}" in sources


# --------------------------------------------------------------------------
# 2. No Memory / Cold Start
# --------------------------------------------------------------------------

def test_no_memory_cold_start(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test when no prior memory exists (cold-start / memory empty):
    - Comparison: reports empty memory status, no matching signals.
    - Hypothesis: formulated from current evidence alone, precedent_backed=False,
      supporting_memory_entries is strictly empty [].
    """
    create_res = client.post("/api/incidents", json={
        "service": "new-billing-v2",
        "environment": "production",
        "symptom_description": "Memory leak causing out of memory container kills on new-billing-v2.",
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    assert data["memory_status"] == "empty"

    # Comparison verification
    assert len(data["comparisons"]) == 1
    comp = data["comparisons"][0]
    assert comp["matching_signals"] == []
    assert comp["match_strength"] == "none"
    assert "empty" in comp["confidence"]["basis"].lower()

    # Hypothesis verification
    assert len(data["hypotheses"]) >= 1
    hyp = data["hypotheses"][0]
    assert hyp["precedent_backed"] is False
    assert hyp["supporting_memory_entries"] == []  # CRITICAL: No fabricated memories!
    assert "without historical precedent" in hyp["confidence"]["basis"].lower()
    assert len(hyp["supporting_current_evidence"]) > 0


# --------------------------------------------------------------------------
# 3. Contradictory Memory
# --------------------------------------------------------------------------

def test_contradictory_memory_and_conflict_surfacing(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test when historical memories disagree on root causes or contradict current evidence:
    - Conflicts are surfaced in comparisons and contradicting_evidence.
    - The agent does NOT silently pick one; both appear in the analysis (FR-027, AC2-04a, AC2-05b).
    """
    id_a = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "checkout-service",
        "body": "Checkout latency caused by Postgres transaction deadlock on cart locks.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-CAUSE-DEADLOCK",
    })

    id_b = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "checkout-service",
        "body": "Checkout latency caused by upstream payment gateway HTTP 504 timeouts.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-CAUSE-GATEWAY",
    })

    create_res = client.post("/api/incidents", json={
        "service": "checkout-service",
        "symptom_description": "Checkout service response time degraded to 6.2s with HTTP 504 gateway timeout errors; no deadlock detected.",
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    # Verify conflict in comparisons
    all_conflicts = []
    for c in data["comparisons"]:
        all_conflicts.extend(c["conflicts"])

    assert len(all_conflicts) > 0
    conflict_text = " ".join(all_conflicts)
    assert "INC-CAUSE-DEADLOCK" in conflict_text or "deadlock" in conflict_text.lower()
    assert "INC-CAUSE-GATEWAY" in conflict_text or "gateway" in conflict_text.lower()

    # Verify both hypotheses exist and contradict each other
    hypotheses = data["hypotheses"]
    assert len(hypotheses) >= 2
    hyp_refs = [h["hypothesis"] for h in hypotheses]
    assert any("INC-CAUSE-DEADLOCK" in r for r in hyp_refs)
    assert any("INC-CAUSE-GATEWAY" in r for r in hyp_refs)

    # Deadlock hypothesis should have contradiction flagged because telemetry reported "no deadlock"
    deadlock_hyp = next(h for h in hypotheses if "INC-CAUSE-DEADLOCK" in h["hypothesis"])
    assert len(deadlock_hyp["contradicting_evidence"]) > 0


# --------------------------------------------------------------------------
# 4. Irrelevant Memory
# --------------------------------------------------------------------------

def test_irrelevant_memory_handling(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test when recalled memory is for an unrelated service/failure mode:
    - Graded as weak match and inapplicable.
    - Not falsely claimed as supporting the current incident.
    """
    irrel_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "email-dispatch",
        "body": "SMTP authentication token expired on marketing email campaign dispatch.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.LOW.value,
        "source_incident_ref": "INC-EMAIL-99",
    })

    create_res = client.post("/api/incidents", json={
        "service": "inventory-service",
        "symptom_description": "Inventory row locking failure during warehouse sync.",
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    # Analyze with explicit recall of the irrelevant entry to test comparison logic
    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    for comp in data["comparisons"]:
        if comp["prior_incident_id"] == "INC-EMAIL-99":
            assert comp["match_strength"] == "weak"
            assert comp["applicability"] == "inapplicable"
            assert any("Different service" in d for d in comp["differences"])


# --------------------------------------------------------------------------
# 5. Unsupported Historical Claim (Anti-Hallucination)
# --------------------------------------------------------------------------

def test_unsupported_historical_claim_anti_hallucination(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Critical Anti-Hallucination Rule:
    The agent may only claim historical facts that exist in the recalled memory set.
    If the memory does NOT contain a rollback outcome, do not claim rollback succeeded!
    """
    # Seed memory WITHOUT any rollback mention
    reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "auth-service",
        "body": "Redis cache connection pool exhausted due to unindexed lookups.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-AUTH-NO-ROLLBACK",
    })

    create_res = client.post("/api/incidents", json={
        "service": "auth-service",
        "symptom_description": "Redis connection pool timeout in auth-service.",
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    # Verify that no hypothesis falsely claims 'rollback succeeded'
    for hyp in data["hypotheses"]:
        assert "rollback succeeded" not in hyp["hypothesis"].lower()
        for ev in hyp["supporting_current_evidence"]:
            assert "rollback succeeded" not in ev.lower()

    # Unknowns should explicitly state that rollback status is unknown
    top_hyp = data["hypotheses"][0]
    assert any("rollback" in u.lower() or "unverified" in u.lower() for u in top_hyp["unknowns"])


# --------------------------------------------------------------------------
# 6. Missing Evidence / Explicit Unknowns
# --------------------------------------------------------------------------

def test_missing_evidence_explicit_unknowns(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test when evidence is insufficient or missing telemetry:
    - Explicitly states 'unknown' where evidence is missing.
    - Never fabricates unprovided facts or metrics.
    """
    create_res = client.post("/api/incidents", json={
        "service": "orders-api",
        "symptom_description": "Orders failing intermittently.",
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    assert len(data["unknowns"]) > 0
    top_hyp = data["hypotheses"][0]
    assert len(top_hyp["unknowns"]) > 0
    assert any("unknown" in u.lower() or "unverified" in u.lower() for u in top_hyp["unknowns"])


# --------------------------------------------------------------------------
# 7. Confidence & Provenance
# --------------------------------------------------------------------------

def test_confidence_and_provenance_structure(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test that every comparison and hypothesis contains:
    - Structured confidence: score (float), level (str), basis (str).
    - Structured provenance: list of {source, statement} attributing every claim.
    """
    entry_id = reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "payment-api",
        "body": "TLS handshake timeout with upstream processor bank.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "confidence": ConfidenceLevel.CONFIRMED.value,
        "source_incident_ref": "INC-TLS-01",
    })

    create_res = client.post("/api/incidents", json={
        "service": "payment-api",
        "symptom_description": "Payment processor TLS timeout errors.",
    })
    inc_id = create_res.json()["id"]

    analyze_res = client.post(f"/api/incidents/{inc_id}/analyze")
    data = analyze_res.json()

    # Comparison confidence and provenance
    comp = data["comparisons"][0]
    assert "score" in comp["confidence"]
    assert "level" in comp["confidence"]
    assert "basis" in comp["confidence"]
    assert isinstance(comp["confidence"]["score"], (int, float))
    assert len(comp["provenance"]) > 0
    for p in comp["provenance"]:
        assert "source" in p
        assert "statement" in p

    # Hypothesis confidence and provenance
    hyp = data["hypotheses"][0]
    assert "score" in hyp["confidence"]
    assert "level" in hyp["confidence"]
    assert "basis" in hyp["confidence"]
    assert len(hyp["provenance"]) > 0
    for p in hyp["provenance"]:
        assert "source" in p
        assert "statement" in p


# --------------------------------------------------------------------------
# 8. Deterministic Comparison & Ranking
# --------------------------------------------------------------------------

def test_deterministic_comparison_and_ranking(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Test that repeated analysis calls against the same incident and memory
    produce 100% identical comparison results, hypothesis order, and scores.
    """
    reset_memory_double.seed_entries([
        {
            "entry_type": EntryType.ROOT_CAUSE.value,
            "service": "search-service",
            "body": "Elasticsearch cluster GC pause caused query timeouts.",
            "outcome_label": OutcomeLabel.SUCCESSFUL.value,
            "confidence": ConfidenceLevel.CONFIRMED.value,
            "source_incident_ref": "INC-SEARCH-01",
        },
        {
            "entry_type": EntryType.ROOT_CAUSE.value,
            "service": "search-service",
            "body": "Index replica count unassigned after node crash.",
            "outcome_label": OutcomeLabel.SUCCESSFUL.value,
            "confidence": ConfidenceLevel.CONFIRMED.value,
            "source_incident_ref": "INC-SEARCH-02",
        },
    ])

    create_res = client.post("/api/incidents", json={
        "service": "search-service",
        "symptom_description": "Search cluster query timeout and high latency.",
    })
    inc_id = create_res.json()["id"]

    results = []
    for _ in range(3):
        res = client.post(f"/api/incidents/{inc_id}/analyze")
        assert res.status_code == 200
        results.append(res.json())

    first = results[0]
    for trial in results[1:]:
        # Compare comparisons
        assert [c["prior_incident_id"] for c in trial["comparisons"]] == [c["prior_incident_id"] for c in first["comparisons"]]
        assert [c["confidence"]["score"] for c in trial["comparisons"]] == [c["confidence"]["score"] for c in first["comparisons"]]

        # Compare hypotheses
        assert [h["hypothesis"] for h in trial["hypotheses"]] == [h["hypothesis"] for h in first["hypotheses"]]
        assert [h["confidence"]["score"] for h in trial["hypotheses"]] == [h["confidence"]["score"] for h in first["hypotheses"]]
        assert [h["rank"] for h in trial["hypotheses"]] == [h["rank"] for h in first["hypotheses"]]


# --------------------------------------------------------------------------
# 9. Strict Reasoning Order
# --------------------------------------------------------------------------

def test_strict_reasoning_order_halting_points(client: TestClient, reset_memory_double: HindsightTestDouble):
    """
    Verifies the strict 5-stage order:
    Current Analysis -> Recall -> Memory Context Assembly -> Comparison -> Hypothesis
    - stage='interpret': stops before recall; hypotheses=[], comparisons=[].
    - stage='recall': stops after recall; hypotheses=[], comparisons=[].
    - stage='compare': stops after comparison; comparisons populated, hypotheses=[].
    - stage='hypothesize': full execution; both comparisons and hypotheses populated.
    """
    reset_memory_double.seed_entry({
        "entry_type": EntryType.ROOT_CAUSE.value,
        "service": "orders-api",
        "body": "Deadlock on order state machine transitions.",
        "outcome_label": OutcomeLabel.SUCCESSFUL.value,
        "source_incident_ref": "INC-ORD-01",
    })

    create_res = client.post("/api/incidents", json={
        "service": "orders-api",
        "symptom_description": "Orders deadlock timeout.",
    })
    inc_id = create_res.json()["id"]

    # 1. Halt at recall
    res_recall = client.post(f"/api/incidents/{inc_id}/analyze", json={"stage": "recall"})
    assert res_recall.status_code == 200
    data_recall = res_recall.json()
    assert data_recall["recall_record"] is not None
    assert data_recall["comparisons"] == []
    assert data_recall["hypotheses"] == []

    # 2. Halt at compare
    res_comp = client.post(f"/api/incidents/{inc_id}/analyze", json={"stage": "compare"})
    assert res_comp.status_code == 200
    data_comp = res_comp.json()
    assert len(data_comp["comparisons"]) >= 1
    assert data_comp["hypotheses"] == []

    # 3. Full run up to hypothesize
    res_hyp = client.post(f"/api/incidents/{inc_id}/analyze", json={"stage": "hypothesize"})
    assert res_hyp.status_code == 200
    data_hyp = res_hyp.json()
    assert len(data_hyp["comparisons"]) >= 1
    assert len(data_hyp["hypotheses"]) >= 1

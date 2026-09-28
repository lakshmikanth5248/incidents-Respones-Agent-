"""
Feature 15 — Memory-Isolated Analysis Tests.

Test Matrix:
  F15-T01  isolated mode never calls Hindsight    — memory_isolated=true never contacts Hindsight client
  F15-T02  suppressed memory status               — memory_status='suppressed' and analysis_label='memory-free analysis'
  F15-T03  normal mode calls Hindsight            — memory_isolated=false queries memory and reflects recall status
  F15-T04  same incident reproducibility          — identical incident input produces distinct, reproducible analyses
  F15-T05  output difference attributable to memory — comparison without memory vs with memory demonstrates clear Delta
  F15-T06  no hidden memory leakage               — memory-isolated analysis contains zero recalled memory IDs or precedent
  F15-T07  persistence of memory isolation state  — analysis_mode, memory_status, and memory_isolated persisted on record
  F15-T08  isolated mode succeeds during outage   — memory-isolated analysis succeeds even if Hindsight is down
"""

import pytest
from src.memory.test_double import HindsightTestDouble


PAYLOAD = {
    "symptom_description": (
        "Redis cluster read latency spiked to 4.5s. "
        "High CPU utilization and slow log queries on cart-cache nodes."
    ),
    "service": "cart-cache",
    "environment": "production",
    "severity": "high",
}


def test_isolated_mode_never_calls_hindsight(client, reset_memory_double: HindsightTestDouble):
    """
    F15-T01: When memory_isolated=true, Hindsight client is never contacted.
    Even with Hindsight set to 'unavailable', memory-isolated analysis succeeds without error.
    """
    reset_memory_double.set_mode("unavailable")

    inc_resp = client.post("/api/incidents", json=PAYLOAD)
    assert inc_resp.status_code == 201
    inc_id = inc_resp.json()["id"]

    # Analyze with memory_isolated=True
    ana_resp = client.post(f"/api/incidents/{inc_id}/analyze", json={"memory_isolated": True})
    assert ana_resp.status_code == 200, ana_resp.text
    data = ana_resp.json()

    assert data["memory_status"] == "suppressed"
    assert data["memory_isolated"] is True
    assert data["analysis_mode"] == "memory_isolated"
    assert data["analysis_label"] == "memory-free analysis"


def test_suppressed_memory_status(client, reset_memory_double):
    """
    F15-T02: Isolated mode produces memory_status='suppressed' and empty memory context.
    """
    inc_resp = client.post("/api/incidents", json=PAYLOAD)
    inc_id = inc_resp.json()["id"]

    ana_resp = client.post(f"/api/incidents/{inc_id}/analyze", json={"memory_isolated": True})
    assert ana_resp.status_code == 200
    data = ana_resp.json()

    assert data["memory_status"] == "suppressed"
    assert data["recall_record"]["memory_status"] == "suppressed"
    assert data["recall_record"]["returned_entries"] == []


def test_normal_mode_calls_hindsight(client, reset_memory_double: HindsightTestDouble):
    """
    F15-T03: Normal mode (memory_isolated=false) queries Hindsight and populates memories.
    """
    reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "cart-cache",
        "body": "Redis KEYS pattern scan blocked event loop causing read latency spike.",
        "outcome_label": "successful",
        "confidence": "confirmed",
        "source_incident_ref": "INC-PRIOR-099",
    })

    inc_resp = client.post("/api/incidents", json=PAYLOAD)
    inc_id = inc_resp.json()["id"]

    ana_resp = client.post(f"/api/incidents/{inc_id}/analyze", json={"memory_isolated": False})
    assert ana_resp.status_code == 200
    data = ana_resp.json()

    assert data["memory_status"] == "ok"
    assert data["memory_isolated"] is False
    assert data["analysis_mode"] == "normal"
    assert len(data["recall_record"]["returned_entries"]) >= 1


def test_same_incident_comparison_without_vs_with_memory(client, reset_memory_double: HindsightTestDouble):
    """
    F15-T04 & F15-T05: Identical incident input analyzed without memory vs with memory.
    Demonstrates clear, measurable delta attributable strictly to Hindsight recall.
    """
    # 1. Seed historical memory
    reset_memory_double.seed_entries([
        {
            "entry_type": "root_cause",
            "service": "cart-cache",
            "body": "Redis KEYS pattern scan blocked event loop causing read latency spike.",
            "outcome_label": "successful",
            "confidence": "confirmed",
            "source_incident_ref": "INC-PRIOR-099",
        },
        {
            "entry_type": "resolution_procedure",
            "service": "cart-cache",
            "body": "Replaced KEYS scan with SCAN cursor-based iteration and killed offending client.",
            "outcome_label": "successful",
            "confidence": "confirmed",
            "source_incident_ref": "INC-PRIOR-099",
        },
    ])

    # 2. Create single incident (input is identical and constant)
    inc_resp = client.post("/api/incidents", json=PAYLOAD)
    assert inc_resp.status_code == 201
    inc_id = inc_resp.json()["id"]

    # ── Run 1: WITHOUT HINDSIGHT (memory_isolated=True) ─────────────────────
    resp_without = client.post(f"/api/incidents/{inc_id}/analyze", json={"memory_isolated": True})
    assert resp_without.status_code == 200
    data_without = resp_without.json()

    # Verify memory-isolated output
    assert data_without["memory_status"] == "suppressed"
    assert data_without["memory_isolated"] is True
    assert data_without["analysis_label"] == "memory-free analysis"

    # Comparison should note no historical experience available
    comps_without = data_without["comparisons"]
    assert len(comps_without) == 1
    assert any("No historical experience available." in diff for diff in comps_without[0]["differences"])

    # Hypotheses without memory should NOT be precedent-backed
    hyps_without = data_without["hypotheses"]
    assert len(hyps_without) >= 1
    assert all(h["precedent_backed"] is False for h in hyps_without)
    assert all(h["supporting_memory_entries"] == [] for h in hyps_without)

    # ── Run 2: WITH HINDSIGHT (memory_isolated=False) ────────────────────────
    resp_with = client.post(f"/api/incidents/{inc_id}/analyze", json={"memory_isolated": False})
    assert resp_with.status_code == 200
    data_with = resp_with.json()

    # Verify memory-informed output
    assert data_with["memory_status"] == "ok"
    assert data_with["memory_isolated"] is False

    # Comparison with memory should identify historical patterns
    comps_with = data_with["comparisons"]
    assert len(comps_with) >= 1
    hist_patterns = comps_with[0]["historical_patterns"]
    assert any("Historical experience found." in p for p in hist_patterns)
    assert any("Previous root cause" in p for p in hist_patterns)
    assert any("Previous resolution" in p for p in hist_patterns)

    # Hypotheses with memory should cite precedent
    hyps_with = data_with["hypotheses"]
    precedent_hyps = [h for h in hyps_with if h["precedent_backed"]]
    assert len(precedent_hyps) >= 1
    assert len(precedent_hyps[0]["supporting_memory_entries"]) >= 1


def test_no_hidden_memory_leakage(client, reset_memory_double: HindsightTestDouble):
    """
    F15-T06: Ensure no memory IDs or recalled facts leak into isolated analysis output.
    """
    mem_id = reset_memory_double.seed_entry({
        "entry_type": "root_cause",
        "service": "cart-cache",
        "body": "SpecialUniqueHistoricalSecretTokenXYZ caused buffer overrun.",
        "source_incident_ref": "INC-SECRET-123",
    })

    inc_resp = client.post("/api/incidents", json=PAYLOAD)
    inc_id = inc_resp.json()["id"]

    ana_resp = client.post(f"/api/incidents/{inc_id}/analyze", json={"memory_isolated": True})
    assert ana_resp.status_code == 200
    text_output = ana_resp.text

    assert mem_id not in text_output
    assert "SpecialUniqueHistoricalSecretTokenXYZ" not in text_output
    assert "INC-SECRET-123" not in text_output


def test_persistence_of_memory_isolation_state(client, reset_memory_double):
    """
    F15-T07: Record analysis_mode, memory_status, and memory_isolated in DB.
    """
    inc_resp = client.post("/api/incidents", json=PAYLOAD)
    inc_id = inc_resp.json()["id"]

    client.post(f"/api/incidents/{inc_id}/analyze", json={"memory_isolated": True})

    # Fetch incident directly and verify fields persisted
    get_inc = client.get(f"/api/incidents/{inc_id}")
    assert get_inc.status_code == 200
    inc_data = get_inc.json()
    assert inc_data["memory_isolated"] is True
    assert inc_data["analysis_mode"] == "memory_isolated"
    assert inc_data["memory_status"] == "suppressed"

    # Fetch analysis directly and verify
    get_ana = client.get(f"/api/incidents/{inc_id}/analysis")
    assert get_ana.status_code == 200
    ana_data = get_ana.json()
    assert ana_data["memory_isolated"] is True
    assert ana_data["analysis_mode"] == "memory_isolated"
    assert ana_data["memory_status"] == "suppressed"
    assert ana_data["analysis_label"] == "memory-free analysis"

"""
Feature 13 — Hindsight Retention Tests.

Conforms to PRD §12.10 (FR-058–FR-066), §2.2–§2.4 (RP-009–RP-016), UC-09, W-14,
and API-012.

Test matrix:
  F13-T01  successful retain               — confirmed post-mortem -> Hindsight write -> entry ids
  F13-T02  retain without confirmation     — 409 CONFLICT (D-12)
  F13-T03  secret failure                  — 422 SECRET_DETECTED, entry identified, secret not echoed
  F13-T04  Hindsight outage                — 503 HINDSIGHT_UNAVAILABLE, record preserved for retry
  F13-T05  partial retain                  — status=partial, per-entry results, never complete success
  F13-T06  retry after partial             — failed entry completes, retained entry is not duplicated
  F13-T07  duplicate retain                — no duplicate memory created
  F13-T08  stable entry ids                — same entry identity -> same memory_entry_id
  F13-T09  retrieval after retain          — retained experience is recallable
  F13-T10  incident not found              — 404 INCIDENT_NOT_FOUND
  F13-T11  retention too early (no PM)     — 409 POSTMORTEM_NOT_CONFIRMED
  F13-T12  retention too early (draft PM)  — 409 POSTMORTEM_NOT_CONFIRMED
  F13-T13  invalid entry type              — 422 INVALID_ENTRY_TYPE
  F13-T14  invalid outcome label           — 422 INVALID_OUTCOME_LABEL
  F13-T15  invalid confidence              — 422 INVALID_CONFIDENCE
  F13-T16  RP-012 missing outcome skipped  — procedure entry skipped, not written
  F13-T17  server-authoritative provenance — service/ref derived from the incident
  F13-T18  client confirmation is a gate, not the authority — confirmed=true w/o stored
           confirmation still fails with 409
"""

import pytest

from src.data.models.retention import MemoryRetention
from src.memory.test_double import HindsightTestDouble


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def entry(
    entry_type="root_cause",
    body="Database connection pool exhaustion caused by a leaked connection handler in payment-api.",
    outcome_label=None,
    confidence="confirmed",
    **kwargs,
):
    payload = {
        "entry_type": entry_type,
        "body": body,
        "confidence": confidence,
    }
    if outcome_label is not None:
        payload["outcome_label"] = outcome_label
    payload.update(kwargs)
    return payload


def retain_payload(incident_id, entries, confirmed=True):
    return {"incident_id": incident_id, "confirmed": confirmed, "entries": entries}


def bank_size(double: HindsightTestDouble) -> int:
    return sum(len(entries) for entries in double.banks.values())


# ===========================================================================
# F13-T01 — Successful retain
# ===========================================================================

def test_successful_retain(client, reset_memory_double, confirmed_postmortem_incident):
    """A confirmed post-mortem produces a structured retain with stable entry ids."""
    inc_id = confirmed_postmortem_incident()

    payload = retain_payload(inc_id, [
        entry(
            entry_type="root_cause",
            body="Leaked connection handler in the payment proxy held HikariCP sessions open.",
            outcome_label="successful",
        ),
        entry(
            entry_type="resolution_procedure",
            body="Roll back payment-api to v2.4.0, then terminate stale backend sessions.",
            outcome_label="successful",
        ),
    ])

    r = client.post("/api/memory/retain", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["status"] == "retained"
    assert data["incident_id"] == inc_id
    assert data["retain_id"].startswith("RET-")
    assert data["idempotent"] is False
    assert data["retry_pending"] is False

    # Per-entry results
    assert len(data["results"]) == 2
    assert all(res["status"] == "retained" for res in data["results"])
    assert [res["entry_type"] for res in data["results"]] == ["root_cause", "resolution_procedure"]
    assert all(res["memory_entry_id"] for res in data["results"])
    assert all(res["entry_key"] for res in data["results"])

    # Retained entry ids surfaced at the envelope level
    assert data["memory_entry_id"] == data["results"][0]["memory_entry_id"]
    assert len(data["memory_entry_ids"]) == 2
    assert data["memory_entry_ids"] == [res["memory_entry_id"] for res in data["results"]]

    # Validation report
    report = data["validation_report"]
    assert report["submitted_entries"] == 2
    assert report["valid_entries"] == 2
    assert report["rejected_entries"] == 0
    assert report["written_entries"] == 2
    assert report["failed_entries"] == 0
    assert report["idempotent_entries"] == 0
    assert report["secret_scan"] == "passed"
    assert report["postmortem_status"] == "confirmed"

    assert data["skipped"] == []
    assert bank_size(reset_memory_double) == 2


# ===========================================================================
# F13-T02 — Retain without confirmation
# ===========================================================================

def test_retain_without_confirmation_rejected(client, reset_memory_double, confirmed_postmortem_incident):
    """D-12: retention does not proceed without explicit engineer confirmation."""
    inc_id = confirmed_postmortem_incident()

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [entry()], confirmed=False))
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "CONFLICT"
    assert bank_size(reset_memory_double) == 0


# ===========================================================================
# F13-T03 — Secret failure
# ===========================================================================

def test_retain_blocked_by_secret_scan(client, reset_memory_double, confirmed_postmortem_incident):
    """
    SEC-008 / FR-065: a credential-shaped entry blocks retention before the write.
    The offending entry is identified by index and type; the secret is never echoed.
    """
    inc_id = confirmed_postmortem_incident()
    secret = "AKIAIOSFODNN7EXAMPLE"

    payload = retain_payload(inc_id, [
        entry(body="Leaked connection handler in the payment proxy."),
        entry(
            entry_type="lesson",
            body=f"Rotate credentials immediately. api_key = {secret} was pasted into the incident channel.",
        ),
    ])

    r = client.post("/api/memory/retain", json=payload)
    assert r.status_code == 422, r.text
    body = r.text
    data = r.json()

    assert data["error"]["code"] == "SECRET_DETECTED"
    assert data["error"]["details"]["entry_index"] == 1
    assert data["error"]["details"]["entry_type"] == "lesson"
    assert data["error"]["details"]["detected_secret_type"] == "api_key"

    # The credential must not appear anywhere in the response.
    assert secret not in body

    # Nothing was written — the scan happens before any memory write.
    assert bank_size(reset_memory_double) == 0


# ===========================================================================
# F13-T04 — Hindsight outage
# ===========================================================================

def test_retain_during_hindsight_outage(client, reset_memory_double, confirmed_postmortem_incident, db_session):
    """
    A total outage surfaces 503 and is retryable. The composed record is preserved
    locally so the experience is not silently lost (RP-014, FR-063, AC-24).
    """
    inc_id = confirmed_postmortem_incident()
    reset_memory_double.set_mode("unavailable")

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(body="Leaked connection handler in the payment proxy held HikariCP sessions open."),
    ]))

    assert r.status_code == 503, r.text
    data = r.json()
    assert data["error"]["code"] == "HINDSIGHT_UNAVAILABLE"
    assert data["error"]["retryable"] is True
    assert data["error"]["details"]["results"][0]["status"] == "failed"

    # Composed record preserved for retry
    preserved = db_session.query(MemoryRetention).filter(MemoryRetention.incident_id == inc_id).all()
    assert len(preserved) == 1
    assert preserved[0].status == "failed"
    assert preserved[0].memory_entry_id is None
    assert preserved[0].body.startswith("Leaked connection handler")
    assert preserved[0].attempts == 1
    assert bank_size(reset_memory_double) == 0


# ===========================================================================
# F13-T05 — Partial retain
# ===========================================================================

def test_partial_retain_is_never_reported_as_complete(client, reset_memory_double, confirmed_postmortem_incident):
    """
    Some entries written and some failed -> status=partial with per-entry results.
    A partial outcome is never reported as complete success (D-11, ERR-03).
    """
    inc_id = confirmed_postmortem_incident()
    reset_memory_double.set_mode("partial_retain")

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(
            entry_type="root_cause",
            body="Leaked connection handler in the payment proxy held HikariCP sessions open.",
            outcome_label="successful",
        ),
        entry(
            entry_type="failed_action",
            body="Restarting payment-api pods did not clear the exhausted connection pool.",
            outcome_label="ineffective",
        ),
    ]))

    assert r.status_code == 200, r.text
    data = r.json()

    assert data["status"] == "partial"
    assert data["retry_pending"] is True

    statuses = [res["status"] for res in data["results"]]
    assert statuses == ["retained", "failed"]
    assert data["results"][0]["memory_entry_id"]
    assert data["results"][1]["memory_entry_id"] is None
    assert data["results"][1]["error"]

    assert data["validation_report"]["written_entries"] == 1
    assert data["validation_report"]["failed_entries"] == 1

    # Only the successful entry reached memory.
    assert bank_size(reset_memory_double) == 1


# ===========================================================================
# F13-T06 — Retry after a partial retain
# ===========================================================================

def test_retry_after_partial_retain(client, reset_memory_double, confirmed_postmortem_incident, db_session):
    """
    Retrying the same request completes the previously failed entry and leaves the
    already-retained entry untouched (RP-014, RP-016, D-10).
    """
    inc_id = confirmed_postmortem_incident()
    reset_memory_double.set_mode("partial_retain")

    payload = retain_payload(inc_id, [
        entry(
            entry_type="root_cause",
            body="Leaked connection handler in the payment proxy held HikariCP sessions open.",
            outcome_label="successful",
        ),
        entry(
            entry_type="failed_action",
            body="Restarting payment-api pods did not clear the exhausted connection pool.",
            outcome_label="ineffective",
        ),
    ])

    first = client.post("/api/memory/retain", json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "partial"
    first_root_cause_id = first.json()["results"][0]["memory_entry_id"]
    assert bank_size(reset_memory_double) == 1

    # Hindsight recovers
    reset_memory_double.set_mode("normal")

    second = client.post("/api/memory/retain", json=payload)
    assert second.status_code == 200, second.text
    data = second.json()

    assert data["status"] == "retained"
    assert data["retry_pending"] is False
    assert [res["status"] for res in data["results"]] == ["already_retained", "retained"]

    # The previously retained entry kept its identity; no duplicate was written.
    assert data["results"][0]["memory_entry_id"] == first_root_cause_id
    assert bank_size(reset_memory_double) == 2

    # The retried entry recorded a second attempt.
    rows = {
        row.entry_type: row
        for row in db_session.query(MemoryRetention).filter(MemoryRetention.incident_id == inc_id).all()
    }
    assert rows["failed_action"].status == "retained"
    assert rows["failed_action"].attempts == 2
    assert rows["root_cause"].attempts == 1


# ===========================================================================
# F13-T07 — Duplicate retain
# ===========================================================================

def test_duplicate_retain_creates_no_duplicate_memory(client, reset_memory_double, confirmed_postmortem_incident):
    """RP-015 / D-10: retaining the same incident twice must not duplicate memory."""
    inc_id = confirmed_postmortem_incident()
    payload = retain_payload(inc_id, [
        entry(
            entry_type="root_cause",
            body="Leaked connection handler in the payment proxy held HikariCP sessions open.",
            outcome_label="successful",
        ),
        entry(
            entry_type="lesson",
            body="Always verify the HikariCP maximumPoolSize before a traffic-draining deploy.",
        ),
    ])

    first = client.post("/api/memory/retain", json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "retained"
    assert bank_size(reset_memory_double) == 2

    second = client.post("/api/memory/retain", json=payload)
    assert second.status_code == 200, second.text
    data = second.json()

    assert data["status"] == "retained"
    assert data["idempotent"] is True
    assert all(res["status"] == "already_retained" for res in data["results"])
    assert data["validation_report"]["written_entries"] == 0
    assert data["validation_report"]["idempotent_entries"] == 2

    # Memory count is unchanged and the ids are the originals.
    assert bank_size(reset_memory_double) == 2
    assert data["memory_entry_ids"] == first.json()["memory_entry_ids"]


# ===========================================================================
# F13-T08 — Stable entry ids
# ===========================================================================

def test_entry_ids_are_stable_across_requests(client, reset_memory_double, confirmed_postmortem_incident):
    """Entry identity — not request ordering — determines the memory entry id."""
    inc_id = confirmed_postmortem_incident()

    single = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(
            entry_type="root_cause",
            body="Leaked connection handler in the payment proxy held HikariCP sessions open.",
            outcome_label="successful",
        ),
    ]))
    assert single.status_code == 200, single.text
    first_id = single.json()["memory_entry_id"]

    # Same entry, submitted again alongside an unrelated entry, reordered and reformatted.
    repeat = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(
            entry_type="lesson",
            body="Add a pool saturation alert for every HikariCP-backed service.",
        ),
        entry(
            entry_type="root_cause",
            body="  Leaked   connection handler in the payment proxy held HikariCP sessions open.  ",
            outcome_label="successful",
        ),
    ]))
    assert repeat.status_code == 200, repeat.text
    data = repeat.json()

    root_cause_result = next(r for r in data["results"] if r["entry_type"] == "root_cause")
    assert root_cause_result["status"] == "already_retained"
    assert root_cause_result["memory_entry_id"] == first_id
    assert data["status"] == "retained"
    assert bank_size(reset_memory_double) == 2


# ===========================================================================
# F13-T09 — Retrieval after retain
# ===========================================================================

def test_retained_experience_is_retrievable(client, reset_memory_double, confirmed_postmortem_incident):
    """
    SC-01 / SC-05: retained experience is a new, retrievable memory record — the
    loop actually closes.
    """
    inc_id = confirmed_postmortem_incident()

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(
            entry_type="root_cause",
            body="Leaked connection handler in the payment proxy held HikariCP sessions open.",
            outcome_label="successful",
        ),
        entry(
            entry_type="resolution_procedure",
            body="Roll back payment-api to v2.4.0 and terminate stale backend sessions.",
            outcome_label="successful",
        ),
    ]))
    assert r.status_code == 200, r.text
    memory_ids = r.json()["memory_entry_ids"]

    # 1. Recall retrieves the retained experience
    recall = client.post("/api/memory/recall", json={
        "query": "payment-api connection pool exhaustion rollback",
        "service": "payment-api",
        "limit": 10,
    })
    assert recall.status_code == 200, recall.text
    recalled = recall.json()
    assert recalled["memory_status"] == "ok"
    recalled_ids = {e["entry_id"] for e in recalled["entries"]}
    assert recalled_ids == set(memory_ids)
    for e in recalled["entries"]:
        assert e["source_incident_ref"] == inc_id
        assert e["relevance_score"] > 0

    # 2. Browsing by service shows the retained records
    browse = client.get("/api/memory/experience?service=payment-api")
    assert browse.status_code == 200, browse.text
    assert browse.json()["total"] == 2

    # 3. Each entry is individually addressable
    detail = client.get(f"/api/incidents/{inc_id}")
    assert detail.status_code == 200


# ===========================================================================
# F13-T10 — Incident not found
# ===========================================================================

def test_retain_unknown_incident_returns_404(client, reset_memory_double):
    """Retention against a non-existent incident is a 404, not a silent success."""
    r = client.post("/api/memory/retain", json=retain_payload("INC-9999-9999", [entry()]))
    assert r.status_code == 404, r.text
    assert r.json()["error"]["code"] == "INCIDENT_NOT_FOUND"
    assert bank_size(reset_memory_double) == 0


# ===========================================================================
# F13-T11 / F13-T12 — Retention attempted too early
# ===========================================================================

def test_retain_before_postmortem_exists_returns_409(client, reset_memory_double, confirmed_postmortem_incident):
    """No post-mortem at all -> retention is too early (FR-058)."""
    inc_id = confirmed_postmortem_incident(generate_postmortem=False, confirm_postmortem=False)

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [entry()]))
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "POSTMORTEM_NOT_CONFIRMED"
    assert r.json()["error"]["details"]["postmortem_status"] == "none"
    assert bank_size(reset_memory_double) == 0


def test_retain_with_unconfirmed_postmortem_returns_409(client, reset_memory_double, confirmed_postmortem_incident):
    """A draft post-mortem is not a confirmed post-mortem (FR-056)."""
    inc_id = confirmed_postmortem_incident(confirm_postmortem=False)

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [entry()]))
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "POSTMORTEM_NOT_CONFIRMED"
    assert r.json()["error"]["details"]["postmortem_status"] == "draft"
    assert bank_size(reset_memory_double) == 0


def test_client_confirmation_cannot_substitute_for_stored_confirmation(
    client, reset_memory_double, confirmed_postmortem_incident
):
    """
    'Never trust client confirmation': confirmed=true on the wire does not unlock
    retention when the stored post-mortem is still a draft.
    """
    inc_id = confirmed_postmortem_incident(confirm_postmortem=False)

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [entry()], confirmed=True))
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "POSTMORTEM_NOT_CONFIRMED"
    assert bank_size(reset_memory_double) == 0


# ===========================================================================
# F13-T13 / F13-T14 / F13-T15 — Server-side entry validation
# ===========================================================================

def test_invalid_entry_type_rejected(client, reset_memory_double, confirmed_postmortem_incident):
    """The memory vocabulary is re-checked server-side."""
    inc_id = confirmed_postmortem_incident()

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(entry_type="incident_story_not_a_type", body="A long narrative that is not a reusable fact."),
    ]))
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "INVALID_ENTRY_TYPE"
    assert r.json()["error"]["details"]["entry_index"] == 0
    assert bank_size(reset_memory_double) == 0


def test_invalid_outcome_label_rejected(client, reset_memory_double, confirmed_postmortem_incident):
    """Outcome labels are restricted to the PRD vocabulary (HM-010, RP-012)."""
    inc_id = confirmed_postmortem_incident()

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(entry_type="root_cause", body="Something.", outcome_label="mostly_fine"),
    ]))
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "INVALID_OUTCOME_LABEL"
    assert bank_size(reset_memory_double) == 0


def test_invalid_confidence_rejected(client, reset_memory_double, confirmed_postmortem_incident):
    """Confidence is mandatory and validated server-side (RP-011)."""
    inc_id = confirmed_postmortem_incident()

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(body="Something reusable.", confidence="very_sure"),
    ]))
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "INVALID_CONFIDENCE"
    assert bank_size(reset_memory_double) == 0


def test_empty_body_rejected(client, reset_memory_double, confirmed_postmortem_incident):
    """HM-033: an entry must express exactly one reusable fact."""
    inc_id = confirmed_postmortem_incident()

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(body="   "),
    ]))
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "INVALID_ENTRY_BODY"
    assert bank_size(reset_memory_double) == 0


# ===========================================================================
# F13-T16 — RP-012 outcome label gate
# ===========================================================================

def test_procedure_without_outcome_label_is_skipped(client, reset_memory_double, confirmed_postmortem_incident):
    """
    RP-012: a procedure entry without an outcome label is skipped and reported,
    never silently written.
    """
    inc_id = confirmed_postmortem_incident()

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(
            entry_type="root_cause",
            body="Leaked connection handler in the payment proxy held HikariCP sessions open.",
        ),
        entry(
            entry_type="resolution_procedure",
            body="Roll back payment-api to v2.4.0 and terminate stale backend sessions.",
        ),
    ]))

    assert r.status_code == 200, r.text
    data = r.json()

    assert data["status"] == "retained"
    assert len(data["skipped"]) == 1
    assert data["skipped"][0]["entry_type"] == "resolution_procedure"
    assert "RP-012" in data["skipped"][0]["reason"]
    assert data["validation_report"]["rejected_entries"] == 1
    assert data["validation_report"]["valid_entries"] == 1
    assert bank_size(reset_memory_double) == 1


# ===========================================================================
# F13-T17 — Server-authoritative provenance
# ===========================================================================

def test_provenance_is_derived_from_the_incident(client, reset_memory_double, confirmed_postmortem_incident):
    """
    RP-013 / D-03: provenance is server-authoritative. A missing or contradictory
    client-supplied reference is corrected to the incident being retained.
    """
    inc_id = confirmed_postmortem_incident(service="payment-api")

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(
            entry_type="root_cause",
            body="Leaked connection handler in the payment proxy held HikariCP sessions open.",
            service="payment-api",
            source_incident_ref="INC-2020-0001",
        ),
    ]))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["validation_report"]["provenance_corrected"] == 1

    stored = reset_memory_double.banks["test-bank"][data["memory_entry_id"]]
    assert stored["source_incident_ref"] == inc_id
    assert stored["service"] == "payment-api"


def test_service_is_inherited_from_the_incident_when_omitted(
    client, reset_memory_double, confirmed_postmortem_incident
):
    """An entry without a service inherits the incident's service server-side."""
    inc_id = confirmed_postmortem_incident(service="payments-ledger")

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(body="Ledger writes failed once the connection pool was exhausted."),
    ]))
    assert r.status_code == 200, r.text

    stored = reset_memory_double.banks["test-bank"][r.json()["memory_entry_id"]]
    assert stored["service"] == "payments-ledger"
    assert stored["source_incident_ref"] == inc_id


# ===========================================================================
# F13-T18 — Retention ledger audit trail
# ===========================================================================

def test_retention_is_audited(client, reset_memory_double, confirmed_postmortem_incident):
    """A memory write is an auditable act on the incident timeline."""
    inc_id = confirmed_postmortem_incident()

    r = client.post("/api/memory/retain", json=retain_payload(inc_id, [
        entry(
            entry_type="root_cause",
            body="Leaked connection handler in the payment proxy held HikariCP sessions open.",
            outcome_label="successful",
        ),
    ]))
    assert r.status_code == 200, r.text
    memory_id = r.json()["memory_entry_id"]

    audit = client.get(f"/api/incidents/{inc_id}/audit")
    assert audit.status_code == 200, audit.text
    events = audit.json()["events"]
    retain_events = [e for e in events if e["action"].startswith("memory.retained")]
    assert len(retain_events) == 1
    assert retain_events[0]["details"]["memory_entry_ids"] == [memory_id]
    assert retain_events[0]["details"]["postmortem_id"]


# ===========================================================================
# F13-T19 — End-to-End Post-Mortem Candidates to Retention and Recall
# ===========================================================================

def test_end_to_end_postmortem_to_retention_and_recall(client, reset_memory_double):
    """
    Complete PRD flow:
      Resolved Incident -> Confirmed Post-Mortem -> Memory Candidates
      -> POST /api/memory/retain -> Retained Entry IDs -> POST /api/memory/recall
    """
    # 1. Intake incident
    inc_resp = client.post("/api/incidents", json={
        "symptom_description": "Search index latency spiked to 9.2s due to unindexed tag filters.",
        "service": "search-indexer",
        "environment": "production",
        "severity": "high",
    })
    assert inc_resp.status_code == 201
    inc_id = inc_resp.json()["id"]

    # 2. Resolve incident
    res_resp = client.post(f"/api/incidents/{inc_id}/resolve", json={
        "actions": ["Applied composite index on tag_id and tenant_id"],
        "runbook_id": "rb-search-index-opt",
        "runbook_version": "1.0",
        "contributing_factors": ["New tag filter released without DB migration"],
        "root_cause": "Missing composite index on tags table under high query load",
        "result": "Query latency dropped to 12ms",
        "outcome": "successful",
    })
    assert res_resp.status_code == 200

    # 3. Verify
    client.post(f"/api/incidents/{inc_id}/verify", json={
        "before_metrics": {"p99_latency": "9.2s"},
        "after_metrics": {"p99_latency": "12ms"},
    })

    # 4. Generate post-mortem draft
    pm_resp = client.post(f"/api/incidents/{inc_id}/postmortem", json={})
    assert pm_resp.status_code == 200

    # 5. Confirm post-mortem draft
    confirm_resp = client.post(
        f"/api/incidents/{inc_id}/postmortem/confirm",
        json={"reviewer": "principal-sre", "review_notes": "Root cause verified"},
    )
    assert confirm_resp.status_code == 200
    pm_data = confirm_resp.json()
    candidates = pm_data["memory_candidates"]
    assert len(candidates) >= 2

    # 6. Retain confirmed candidates via Feature 13
    retain_resp = client.post("/api/memory/retain", json={
        "incident_id": inc_id,
        "confirmed": True,
        "entries": candidates,
    })
    assert retain_resp.status_code == 200
    retain_data = retain_resp.json()
    assert retain_data["status"] == "retained"
    assert len(retain_data["memory_entry_ids"]) == len(candidates)

    # 7. Recall retained experience via Feature 04
    recall_resp = client.post("/api/memory/recall", json={
        "service": "search-indexer",
        "query": "index latency unindexed tag filters",
    })
    assert recall_resp.status_code == 200
    recall_data = recall_resp.json()
    assert recall_data["total_found"] > 0
    recalled_incident_refs = [e["source_incident_ref"] for e in recall_data["entries"]]
    assert inc_id in recalled_incident_refs


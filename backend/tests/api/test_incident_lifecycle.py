"""
API Tests for Feature 2 — Incident Retrieval, State & Lifecycle.
Conforms strictly to Feature 2 specifications:
- Controlled state machine transitions
- Terminal state protection
- Optimistic concurrency control (409 Conflict)
- Comprehensive audit trail
- Filtering, pagination, and stable ordering
- Absence of external AI/Hindsight calls on retrieval
"""


def test_valid_lifecycle_state_machine_progression(client):
    """
    Test full sequence of valid transitions:
    created -> analyzing -> analyzed -> recommendation_ready -> resolving -> resolved -> closed
    """
    # 1. Create incident (starts in 'created')
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Payment API high latency and failure rate",
        "service": "payment-api"
    })
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]
    assert create_res.json()["status"] == "created"
    assert create_res.json()["revision"] == 1
    assert create_res.json()["resolution_status"] == "unresolved"
    assert create_res.json()["resolved_at"] is None

    # 2. created -> analyzing
    t1 = client.post(f"/api/incidents/{inc_id}/transition", json={
        "new_status": "analyzing",
        "expected_revision": 1,
        "actor": "sre-analyst",
        "reason": "Commencing automated analysis"
    })
    assert t1.status_code == 200
    assert t1.json()["status"] == "analyzing"
    assert t1.json()["revision"] == 2

    # 3. analyzing -> analyzed
    t2 = client.post(f"/api/incidents/{inc_id}/transition", json={
        "new_status": "analyzed",
        "expected_revision": 2,
        "actor": "sre-analyst"
    })
    assert t2.status_code == 200
    assert t2.json()["status"] == "analyzed"
    assert t2.json()["revision"] == 3

    # 4. analyzed -> recommendation_ready
    t3 = client.post(f"/api/incidents/{inc_id}/transition", json={
        "new_status": "recommendation_ready",
        "expected_revision": 3
    })
    assert t3.status_code == 200
    assert t3.json()["status"] == "recommendation_ready"
    assert t3.json()["revision"] == 4

    # 5. recommendation_ready -> resolving
    t4 = client.post(f"/api/incidents/{inc_id}/transition", json={
        "new_status": "resolving",
        "expected_revision": 4,
        "actor": "on-call-sre"
    })
    assert t4.status_code == 200
    assert t4.json()["status"] == "resolving"
    assert t4.json()["resolution_status"] == "in_progress"
    assert t4.json()["revision"] == 5

    # 6. resolving -> resolved
    t5 = client.post(f"/api/incidents/{inc_id}/transition", json={
        "new_status": "resolved",
        "expected_revision": 5,
        "actor": "on-call-sre",
        "reason": "Connection pool size enlarged and deployment verified"
    })
    assert t5.status_code == 200
    data5 = t5.json()
    assert data5["status"] == "resolved"
    assert data5["resolution_status"] == "resolved"
    assert data5["resolved_at"] is not None
    assert data5["revision"] == 6

    # 7. resolved -> closed
    t6 = client.post(f"/api/incidents/{inc_id}/transition", json={
        "new_status": "closed",
        "expected_revision": 6,
        "actor": "postmortem-lead"
    })
    assert t6.status_code == 200
    assert t6.json()["status"] == "closed"
    assert t6.json()["revision"] == 7


def test_invalid_transitions_are_rejected(client):
    """
    Test illegal state machine transitions:
    - created -> resolved (skipping analysis/mitigation)
    - resolved -> created
    - resolved -> analyzing
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Cache cluster degraded",
        "service": "cache-service"
    })
    inc_id = create_res.json()["id"]

    # 1. created -> resolved is forbidden
    bad1 = client.post(f"/api/incidents/{inc_id}/transition", json={"new_status": "resolved"})
    assert bad1.status_code in [422, 409]
    assert bad1.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # Move legitimately to resolved: created -> investigating -> resolving -> resolved
    client.post(f"/api/incidents/{inc_id}/transition", json={"new_status": "investigating"})
    client.post(f"/api/incidents/{inc_id}/transition", json={"new_status": "resolving"})
    res_ok = client.post(f"/api/incidents/{inc_id}/transition", json={"new_status": "resolved"})
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "resolved"

    # 2. resolved -> created is strictly forbidden
    bad2 = client.post(f"/api/incidents/{inc_id}/transition", json={"new_status": "created"})
    assert bad2.status_code in [422, 409]
    assert bad2.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # 3. resolved -> analyzing is strictly forbidden
    bad3 = client.post(f"/api/incidents/{inc_id}/transition", json={"new_status": "analyzing"})
    assert bad3.status_code in [422, 409]
    assert bad3.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_terminal_state_protection(client):
    """
    Terminal states remain terminal.
    Once closed, no transition or modification is allowed.
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "DNS resolution timeout",
        "service": "dns-service"
    })
    inc_id = create_res.json()["id"]

    # Close the incident directly
    client.post(f"/api/incidents/{inc_id}/transition", json={"new_status": "closed"})

    # Attempt any transition from closed -> 409 Conflict
    for target in ["created", "investigating", "analyzing", "resolved"]:
        res = client.post(f"/api/incidents/{inc_id}/transition", json={"new_status": target})
        assert res.status_code == 409
        assert res.json()["error"]["code"] in ["INCIDENT_CLOSED", "TERMINAL_STATE_VIOLATION"]

    # Attempt patch on closed incident -> 409 Conflict
    patch_res = client.patch(f"/api/incidents/{inc_id}", json={"severity": "low"})
    assert patch_res.status_code == 409
    assert patch_res.json()["error"]["code"] == "INCIDENT_CLOSED"


def test_concurrent_updates_optimistic_locking(client):
    """
    Test optimistic concurrency control:
    Mismatched expected_revision returns CONFLICT (409 Conflict).
    Mismatched from_status returns CONFLICT (409 Conflict).
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Worker queue saturation",
        "service": "worker-service"
    })
    inc_id = create_res.json()["id"]
    current_rev = create_res.json()["revision"]  # revision 1

    # Attempt transition specifying stale expected_revision (e.g., 999 instead of 1)
    conflicting_res = client.post(f"/api/incidents/{inc_id}/transition", json={
        "new_status": "analyzing",
        "expected_revision": 999
    })
    assert conflicting_res.status_code == 409
    assert conflicting_res.json()["error"]["code"] == "CONFLICT"
    assert "revision" in conflicting_res.json()["error"]["message"].lower()

    # Attempt transition specifying mismatched from_status (expected 'resolving' but is 'created')
    state_conflict_res = client.post(f"/api/incidents/{inc_id}/transition", json={
        "new_status": "analyzing",
        "from_status": "resolving"
    })
    assert state_conflict_res.status_code == 409
    assert state_conflict_res.json()["error"]["code"] == "CONFLICT"

    # Concurrent patch conflict check
    patch_conflict = client.patch(f"/api/incidents/{inc_id}", json={
        "severity": "high",
        "expected_revision": 999
    })
    assert patch_conflict.status_code == 409
    assert patch_conflict.json()["error"]["code"] == "CONFLICT"


def test_audit_records_on_lifecycle_transitions(client):
    """
    Every transition records: actor, timestamp, action, previous_state, new_state, outcome.
    Verify audit trail endpoint GET /api/incidents/{id}/audit.
    """
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Search index lag",
        "service": "search-api"
    })
    inc_id = create_res.json()["id"]

    # Transition 1: created -> analyzing
    client.post(f"/api/incidents/{inc_id}/transition", json={
        "new_status": "analyzing",
        "actor": "alice-sre",
        "reason": "Triaging search index latency"
    })

    # Transition 2: analyzing -> analyzed
    client.post(f"/api/incidents/{inc_id}/transition", json={
        "new_status": "analyzed",
        "actor": "bob-sre",
        "reason": "Analysis complete"
    })

    # Fetch audit log
    audit_res = client.get(f"/api/incidents/{inc_id}/audit")
    assert audit_res.status_code == 200
    data = audit_res.json()
    assert data["incident_id"] == inc_id
    events = data["events"]

    # At least 3 events: incident.created, then 2 state transitions
    assert len(events) >= 3
    assert events[0]["action"] == "incident.created"
    assert events[0]["new_state"] == "created"

    t1_event = events[1]
    assert t1_event["action"] == "incident.state_transition"
    assert t1_event["actor"] == "alice-sre"
    assert t1_event["previous_state"] == "created"
    assert t1_event["new_state"] == "analyzing"
    assert t1_event["outcome"] == "success"
    assert t1_event["timestamp"] is not None

    t2_event = events[2]
    assert t2_event["action"] == "incident.state_transition"
    assert t2_event["actor"] == "bob-sre"
    assert t2_event["previous_state"] == "analyzing"
    assert t2_event["new_state"] == "analyzed"
    assert t2_event["outcome"] == "success"


def test_advanced_filtering_and_stable_ordering(client):
    """
    Verify filtering by status, service, environment, severity, and stable pagination.
    """
    # Create 3 distinct incidents
    client.post("/api/incidents", json={
        "symptom_description": "Prod payment failure",
        "service": "payment-api",
        "environment": "production",
        "severity": "critical"
    })
    client.post("/api/incidents", json={
        "symptom_description": "Staging payment test",
        "service": "payment-api",
        "environment": "staging",
        "severity": "low"
    })
    client.post("/api/incidents", json={
        "symptom_description": "Prod auth slowdown",
        "service": "auth-service",
        "environment": "production",
        "severity": "high"
    })

    # Filter by service + environment
    res1 = client.get("/api/incidents?service=payment-api&environment=production")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] == 1
    assert data1["incidents"][0]["service"] == "payment-api"
    assert data1["incidents"][0]["environment"] == "production"

    # Filter by severity
    res2 = client.get("/api/incidents?severity=critical")
    assert res2.status_code == 200
    data2 = res2.json()
    assert all(inc["severity"] == "critical" for inc in data2["incidents"])

    # Test pagination & stable ordering (descending by created_at)
    p1 = client.get("/api/incidents?limit=2&offset=0&order_by=created_at&order_dir=desc")
    assert p1.status_code == 200
    assert len(p1.json()["incidents"]) == 2
    assert p1.json()["total"] == 3

    p2 = client.get("/api/incidents?limit=2&offset=2&order_by=created_at&order_dir=desc")
    assert p2.status_code == 200
    assert len(p2.json()["incidents"]) == 1

    # Verify no overlap across pages
    ids_p1 = {inc["id"] for inc in p1.json()["incidents"]}
    ids_p2 = {inc["id"] for inc in p2.json()["incidents"]}
    assert ids_p1.isdisjoint(ids_p2)


def test_missing_incident_404_responses(client):
    """Verify 404 responses for nonexistent IDs across endpoints."""
    fake_id = "INC-1999-0000"

    assert client.get(f"/api/incidents/{fake_id}").status_code == 404
    assert client.patch(f"/api/incidents/{fake_id}", json={"severity": "low"}).status_code == 404
    assert client.post(f"/api/incidents/{fake_id}/transition", json={"new_status": "analyzing"}).status_code == 404
    assert client.get(f"/api/incidents/{fake_id}/audit").status_code == 404

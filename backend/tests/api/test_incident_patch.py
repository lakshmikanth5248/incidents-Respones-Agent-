"""
API Tests for Incident Patch and State Transitions.
Conforms to PRD §12.2 (API-004), FR-007, FR-009, D-13.
"""


def test_patch_incident_success(client):
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Initial reported symptom in billing",
        "service": "billing-service"
    })
    incident_id = create_res.json()["id"]
    assert create_res.json()["revision"] == 1

    patch_payload = {
        "status": "investigating",
        "severity": "high",
        "environment": "production",
        "recent_changes": ["config-v2-applied"]
    }

    patch_res = client.patch(f"/api/incidents/{incident_id}", json=patch_payload)
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["status"] == "investigating"
    assert data["severity"] == "high"
    assert data["environment"] == "production"
    assert "config-v2-applied" in data["recent_changes"]
    assert data["revision"] == 2


def test_patch_symptom_correction_updates_normalized_fields(client):
    create_res = client.post("/api/incidents", json={
        "symptom_description": "General system slowdown",
    })
    incident_id = create_res.json()["id"]
    original_raw = create_res.json()["raw_symptom_description"]

    # Provide a corrected symptom description
    correction = "Payment API is failing with database connection exhaustion."
    patch_res = client.patch(
        f"/api/incidents/{incident_id}",
        json={"symptom_description_correction": correction}
    )
    assert patch_res.status_code == 200
    data = patch_res.json()

    # Raw description MUST remain the original raw submission!
    assert data["raw_symptom_description"] == original_raw
    assert data["symptoms_raw"] == original_raw

    # But normalized fields must now reflect the correction
    assert any("payment" in s for s in data["normalized"]["symptoms"])
    assert any("database" in s or "connection" in s for s in data["normalized"]["symptoms"])
    assert "database_connection_exhaustion" in data["failure_mode_label"]


def test_patch_invalid_state_transition(client):
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Network timeout in worker",
    })
    incident_id = create_res.json()["id"]

    # Attempt illegal transition: created -> resolved (skipping investigating)
    patch_res = client.patch(f"/api/incidents/{incident_id}", json={"status": "resolved"})
    assert patch_res.status_code == 422
    assert patch_res.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_patch_closed_incident_conflict(client):
    create_res = client.post("/api/incidents", json={
        "symptom_description": "Network issue resolved quickly",
    })
    incident_id = create_res.json()["id"]

    # Close the incident directly
    client.patch(f"/api/incidents/{incident_id}", json={"status": "closed"})

    # Attempt to modify the closed incident -> 409 Conflict
    patch_res = client.patch(f"/api/incidents/{incident_id}", json={"severity": "low"})
    assert patch_res.status_code == 409
    assert patch_res.json()["error"]["code"] == "INCIDENT_CLOSED"


def test_patch_incident_not_found(client):
    res = client.patch("/api/incidents/INC-9999-9999", json={"severity": "low"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "INCIDENT_NOT_FOUND"

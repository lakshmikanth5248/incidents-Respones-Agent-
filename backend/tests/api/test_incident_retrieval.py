"""
API Tests for Incident Retrieval and Health.
Conforms to PRD §12.2 (API-002, API-003, API-016).
"""


def test_list_incidents_empty(client):
    response = client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert data["incidents"] == []
    assert data["total"] == 0


def test_list_incidents_with_filter_and_pagination(client):
    # Seed 3 incidents
    client.post("/api/incidents", json={"symptom_description": "First issue", "service": "auth-service"})
    client.post("/api/incidents", json={"symptom_description": "Second issue", "service": "payment-api"})
    client.post("/api/incidents", json={"symptom_description": "Third issue", "service": "payment-api"})

    # Test list all
    all_res = client.get("/api/incidents")
    assert all_res.status_code == 200
    assert all_res.json()["total"] == 3

    # Test filter by service
    filtered_res = client.get("/api/incidents?service=payment-api")
    assert filtered_res.status_code == 200
    assert filtered_res.json()["total"] == 2
    for inc in filtered_res.json()["incidents"]:
        assert inc["service"] == "payment-api"

    # Test pagination
    paginated_res = client.get("/api/incidents?limit=1&offset=0")
    assert paginated_res.status_code == 200
    assert len(paginated_res.json()["incidents"]) == 1
    assert paginated_res.json()["total"] == 3


def test_get_incident_by_id(client):
    created_res = client.post("/api/incidents", json={
        "symptom_description": "Latency in gateway",
        "service": "api-gateway"
    })
    incident_id = created_res.json()["id"]

    get_res = client.get(f"/api/incidents/{incident_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == incident_id
    assert get_res.json()["service"] == "api-gateway"


def test_get_incident_not_found(client):
    res = client.get("/api/incidents/INC-9999-9999")
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "INCIDENT_NOT_FOUND"


def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["dependencies"]["database"] == "connected"

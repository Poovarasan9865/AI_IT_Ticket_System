
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_ticket():
    response = client.post(
        "/api/tickets",
        json={
            "title": "VPN is not connecting",
            "description": "VPN stopped working after password change",
            "requester": "Test User",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["id"] > 0
    assert body["category"]
    assert body["assigned_team"]
    assert body["priority"]
    assert body["suggested_resolution"]
    assert body["status"] == "Open"
    assert "similar_tickets" in body
    assert "ai_method" in body


def test_list_tickets():
    response = client.get("/api/tickets")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_ticket():
    created = client.post(
        "/api/tickets",
        json={
            "title": "Monitor is not working",
            "description": "The monitor screen stays black",
            "requester": "Test User",
        },
    )

    assert created.status_code == 200
    ticket_id = created.json()["id"]

    response = client.get(f"/api/tickets/{ticket_id}")

    assert response.status_code == 200
    assert response.json()["id"] == ticket_id
    assert "similar_tickets" in response.json()


def test_get_missing_ticket():
    response = client.get("/api/tickets/99999999")
    assert response.status_code == 404


def test_update_ticket_status():
    created = client.post(
        "/api/tickets",
        json={
            "title": "Email is not working",
            "description": "Unable to send emails from Outlook",
            "requester": "Test User",
        },
    )

    ticket_id = created.json()["id"]

    response = client.patch(
        f"/api/tickets/{ticket_id}/status",
        params={"status": "In Progress"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"


def test_invalid_ticket_status():
    created = client.post(
        "/api/tickets",
        json={
            "title": "Keyboard is not working",
            "description": "Keyboard keys are not responding",
            "requester": "Test User",
        },
    )

    ticket_id = created.json()["id"]

    response = client.patch(
        f"/api/tickets/{ticket_id}/status",
        params={"status": "Unknown"},
    )

    assert response.status_code == 400


def test_update_missing_ticket():
    response = client.patch(
        "/api/tickets/99999999/status",
        params={"status": "Resolved"},
    )

    assert response.status_code == 404


def test_metrics():
    response = client.get("/api/metrics")
    assert response.status_code == 200

    body = response.json()
    assert "total" in body
    assert "statuses" in body
    assert "categories" in body
    assert "priorities" in body
    assert body["total"] >= 0


def test_demo_data():
    response = client.get("/api/demo-data")
    assert response.status_code == 200
    assert isinstance(response.json(), (list, dict))

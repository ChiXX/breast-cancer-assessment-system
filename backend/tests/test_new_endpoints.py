import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_contact_request(client):
    payload = {
        "assessment_id": 1,
        "session_id": "session_123"
    }
    response = client.post("/api/v1/contact-requests", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["assessment_id"] == 1
    assert data["session_id"] == "session_123"
    assert data["status"] == "pending"

def test_create_event(client):
    payload = {
        "event_name": "test_event",
        "session_id": "session_123",
        "payload": {"key": "value"}
    }
    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["event_name"] == "test_event"
    assert data["payload"]["key"] == "value"

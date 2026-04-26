import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
import os

@pytest.fixture
def client():
    # Set DEBUG to True for testing debug endpoints
    os.environ["DEBUG"] = "True"
    return TestClient(app)

def test_db_dump(client):
    response = client.get("/api/v1/debug/db/dump")
    assert response.status_code == 200
    data = response.json()
    assert "assessments" in data
    assert "contact_requests" in data
    assert "event_logs" in data

def test_db_reset(client):
    # First, maybe add something to DB? 
    # For now just check if it works.
    response = client.post("/api/v1/debug/db/reset")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Database reset successful"}
    
    # After reset, dump should be empty
    dump_response = client.get("/api/v1/debug/db/dump")
    dump_data = dump_response.json()
    assert len(dump_data["assessments"]) == 0
    assert len(dump_data["contact_requests"]) == 0
    assert len(dump_data["event_logs"]) == 0

def test_get_individual_tables(client):
    # Check assessments
    response = client.get("/api/v1/debug/db/assessments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Check contact requests
    response = client.get("/api/v1/debug/db/contact-requests")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Check events
    response = client.get("/api/v1/debug/db/events")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_debug_disabled(client):
    # If DEBUG is False, these should return 404
    os.environ["DEBUG"] = "False"
    response = client.get("/api/v1/debug/db/dump")
    assert response.status_code == 404

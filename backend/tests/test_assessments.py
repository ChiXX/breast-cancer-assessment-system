import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# We'll import the app once it's created
# from app.main import app 

from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_assessment_success(client):
    """
    Test successful assessment creation:
    1. Send user input to /api/v1/assessments
    2. Mock MCP response
    3. Verify DB record (mocked or real test db)
    4. Verify response structure
    """
    mock_mcp_response = {
        "risk_level": "中风险",
        "advice": "建议观察",
        "contact_team": False,
        "evidence": "参考依据内容",
        "rule_id": "QA-M-005"
    }

    payload = {
        "user_input": "我感觉手麻",
        "session_id": "session_123"
    }

    with patch("backend.app.services.assessment_service.evaluate_symptoms", return_value=mock_mcp_response):
        response = client.post("/api/v1/assessments", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["risk_level"] == "中风险"
    assert data["session_id"] == "session_123"
    assert "id" in data

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from mcp.server import app

client = TestClient(app)

def test_evaluate_endpoint():
    """测试 /v1/evaluate 接口的解析逻辑"""
    mock_response = """
根据您的描述，评估如下：
```json
{
  "type": "evaluation",
  "data": {
    "risk_level": "HIGH",
    "action_required": "立即线下就医",
    "ctcae_grade": "Grade 1",
    "advice": "请立即前往急诊。",
    "contact_team": true,
    "evidence": "符合危急值标准",
    "rule_id": "QA-M-001"
  }
}
```
"""
    with patch("mcp.server.master_agent.chat", return_value=mock_response):
        response = client.post("/v1/evaluate", json={
            "user_input": "我发烧 39 度",
            "session_id": "test_session_123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] == "HIGH"
        assert data["contact_team"] is True
        assert "请立即前往急诊" in data["advice"]
        assert data["rule_id"] == "QA-M-001"

def test_sessions_endpoint():
    """测试 /v1/sessions/{session_id} 接口"""
    # Mocking ReadMemoryList and ReadMemoryDetail
    mock_memories = [
        {"title": "发热 - 39度 - 建议急诊", "timestamp": "2024-01-01T10:00:00", "session_id": "test_session_123", "learned": False}
    ]
    
    with patch("mcp.server.ReadMemoryList.call", return_value={"status": "success", "memories": mock_memories}):
        with patch("mcp.server.ReadMemoryDetail.call", return_value={"status": "success", "content": json.dumps({"summary": "Memory Content"})}):
            response = client.get("/v1/sessions/test_session_123")
            assert response.status_code == 200
            data = response.json()
            assert len(data["memories"]) == 1
            assert data["memories"][0]["clue"] == "发热 - 39度 - 建议急诊"
            assert data["memories"][0]["summary"] == "Memory Content"

def test_knowledge_skills_endpoint():
    """测试 /v1/knowledge/skills 接口"""
    mock_skills = [{"name": "medical_consultation_workflow", "description": "Side effect assessment"}]
    with patch("mcp.server.get_all_skill_metadata", return_value=mock_skills):
        response = client.get("/v1/knowledge/skills")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["name"] == "medical_consultation_workflow"

def test_knowledge_learn_endpoint():
    """测试 /v1/knowledge/learn 接口 (异步触发)"""
    with patch("mcp.server.learning_agent.run") as mock_run:
        response = client.post("/v1/knowledge/learn")
        assert response.status_code == 200
        assert response.json()["status"] == "processing"
        # Background task should be added

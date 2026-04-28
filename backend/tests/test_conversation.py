import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.app.main import app
from backend.app.database import SessionLocal, Base, engine

@pytest.fixture
def client():
    # Setup test database
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    # No teardown needed for sqlite in-memory or file for now, 
    # but in a real app we'd drop tables.

def test_assessment_includes_history(client):
    """
    Test that subsequent assessments include previous history.
    """
    session_id = "test_session_history"
    
    # 1. First interaction
    mock_response_1 = {
        "risk_level": "未知",
        "advice": "请问您还有其他症状吗？",
        "contact_team": False,
        "evidence": "初次询问",
        "rule_id": "INIT"
    }
    
    with patch("backend.app.services.assessment_service.evaluate_symptoms", return_value=mock_response_1) as mock_eval:
        client.post("/api/v1/assessments", json={
            "user_input": "你好",
            "session_id": session_id
        })
        # Check that history was empty for the first call
        args, kwargs = mock_eval.call_args
        # Based on current implementation, it doesn't even accept history yet,
        # but once we update it, we want it to be empty or []
    
    # 2. Second interaction
    mock_response_2 = {
        "risk_level": "中风险",
        "advice": "建议就医",
        "contact_team": True,
        "evidence": "结合前文判定",
        "rule_id": "QA-001"
    }
    
    with patch("backend.app.services.assessment_service.evaluate_symptoms", return_value=mock_response_2) as mock_eval:
        client.post("/api/v1/assessments", json={
            "user_input": "我有点发烧",
            "session_id": session_id,
            "history": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "请问您还有其他症状吗？"}
            ]
        })
        
        # VERIFY: history should contain the first interaction
        # We expect history to be passed to evaluate_symptoms
        # The expected history format is:
        # [
        #   {"role": "user", "content": "你好"},
        #   {"role": "assistant", "content": "请问您还有其他症状吗？"}
        # ]
        args, kwargs = mock_eval.call_args
        # We need to update evaluate_symptoms signature first, but for now this test will fail
        # because the current implementation doesn't pass history.
        
        # If we change signature to evaluate_symptoms(user_input, session_id, history=[])
        # then history should be the 3rd arg or a kwarg
        history = args[2] if len(args) > 2 else kwargs.get('history')
        
        assert history is not None
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "你好"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "请问您还有其他症状吗？"

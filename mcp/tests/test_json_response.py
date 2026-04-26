import json
import pytest
from mcp.agents.rag_agent import RAGAgent
from mcp.agents.master import MedicalMaster
from mcp.agents.config import MASTER_MODEL, get_llm_cfg
from mcp.server import parse_agent_response
from unittest.mock import MagicMock, patch

@pytest.fixture
def llm_cfg():
    return get_llm_cfg(MASTER_MODEL)

from mcp.agents.schemas import RiskLevel

def test_rag_agent_json_output(llm_cfg):
    agent = RAGAgent(llm_cfg=llm_cfg)
    from unittest.mock import MagicMock
    json_response = json.dumps({
        "risk_level": "MEDIUM",
        "advice": "Rest",
        "contact_team": False,
        "evidence": "Test",
        "rule_id": "QA-001"
    })
    agent.agent.run = MagicMock(return_value=[{'content': json_response}])
    
    response = agent.chat("我手麻")
    data = json.loads(response)
    assert data["risk_level"] == "MEDIUM"

def test_master_agent_json_output(llm_cfg):
    with patch('mcp.agents.master.get_all_skill_metadata', return_value=[]), \
         patch('mcp.agents.tools.memory_tools.ReadMemoryList.call', return_value={'status': 'success', 'memories': []}):
        agent = MedicalMaster()
    
    json_response = json.dumps({
        "type": "evaluation",
        "data": {
            "risk_level": "MEDIUM",
            "advice": "Rest",
            "contact_team": False,
            "evidence": "Test",
            "rule_id": "QA-001"
        },
        "display_text": "Results"
    })
    agent.agent.run = MagicMock(return_value=[{'content': json_response}])
    
    response = agent.chat("我手麻")
    data = json.loads(response)
    assert data["type"] == "evaluation"

def test_server_parsing():
    json_input = json.dumps({
        "type": "evaluation",
        "data": {
            "risk_level": "HIGH",
            "advice": "Emergency",
            "contact_team": True,
            "evidence": "Crit",
            "rule_id": "QA-999"
        },
        "display_text": "Attention"
    })
    
    res = parse_agent_response(json_input)
    assert res.risk_level == RiskLevel.HIGH
    assert res.advice == "Emergency"
    assert res.contact_team == True
    assert res.rule_id == "QA-999"
    assert res.display_text == "Attention"

def test_server_parsing_question():
    json_input = json.dumps({
        "type": "question",
        "content": "How long?",
        "display_text": "Need more info"
    })
    
    res = parse_agent_response(json_input)
    assert res.risk_level == RiskLevel.UNKNOWN
    assert res.advice == "How long?"
    assert res.display_text == "Need more info"

if __name__ == "__main__":
    pytest.main([__file__])

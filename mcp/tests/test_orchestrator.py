import pytest
import json
from mcp.agents.orchestrator import OrchestratorAgent, OrchestratorResponse

def test_orchestrator_initialization():
    # 测试主 Agent 初始化
    agent = OrchestratorAgent()
    assert agent.name == 'Orchestrator'
    assert hasattr(agent, 'prompt_template')

def test_orchestrator_get_api_tools():
    # 测试工具的动态加载
    agent = OrchestratorAgent()
    tools = agent._get_api_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0
    tool_names = [t['function']['name'] for t in tools]
    assert 'discover_skills' in tool_names
    assert 'delegate_assessment_task' in tool_names

@pytest.mark.asyncio
async def test_orchestrator_generate_response_mock(mocker):
    # 测试使用 OpenAI 原生 Function Calling 的流程
    agent = OrchestratorAgent()
    
    # 直接替换实例中的客户端，防止发起真实的 API 请求
    mock_client_instance = mocker.AsyncMock()
    agent.client = mock_client_instance
    
    # 构造原生的工具调用返回体
    mock_choice = mocker.Mock()
    mock_choice.message.content = "我正在为您查找相关的评估建议..."
    
    mock_tool_call = mocker.Mock()
    mock_tool_call.function.name = "discover_skills"
    mock_tool_call.function.arguments = '{"query": "手痛"}'
    mock_choice.message.tool_calls = [mock_tool_call]
    
    mock_api_response = mocker.Mock()
    mock_api_response.choices = [mock_choice]
    
    mock_client_instance.chat.completions.create.return_value = mock_api_response
    
    response = await agent.generate_response("手痛")
    
    # 验证返回值能够正确兼容原有 OrchestratorResponse 格式
    assert response.thought == "我正在为您查找相关的评估建议..."
    assert response.reply is None
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0]["name"] == "discover_skills"
    assert response.tool_calls[0]["arguments"]["query"] == "手痛"

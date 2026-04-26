import os
from typing import List, Iterator
from qwen_agent.agents import Assistant
from langsmith import traceable
import dashscope
from mcp.agents.tools import RAGQueryTool # Ensure tool is registered

class RAGAgent:
    """
    RAGAgent is a specialized medical knowledge agent.
    It uses the rag_query_tool to retrieve information from medical guidelines.
    """
    
    def __init__(self, llm_cfg: dict, name: str = 'RAG_Expert', description: str = '医疗知识专家，负责检索知识库并按要求返回建议。'):
        self.llm_cfg = llm_cfg
        self.name = name
        self.description = description
        
        from mcp.agents.schemas import RiskLevel, ActionRequired, CTCAEGrade
        risk_levels = ", ".join([f"'{level.value}'" for level in RiskLevel if level != RiskLevel.UNKNOWN])
        actions = ", ".join([f"'{action.value}'" for action in ActionRequired])
        grades = ", ".join([f"'{grade.value}'" for grade in CTCAEGrade])
        
        self.system_prompt = (
            f"你是一个专业的乳腺癌副作用评估专家。你的职责是调用 'rag_query_tool' 检索指南，并严格按 JSON 格式回答。\n\n"
            f"### 【评估标准映射】\n"
            "1. **HIGH** + **立即线下就医** + **Grade 1**\n"
            "2. **HIGH** + **24小时内联系团队** + **Grade 2**\n"
            "3. **MEDIUM** + **联系团队** + **Grade 3**\n"
            "4. **MEDIUM** + **密切观察** + **Grade 4**\n"
            "5. **LOW** + **继续观察与记录** + **Grade 5**\n\n"
            "### 输出格式：\n"
            "```json\n"
            "{\n"
            "  \"risk_level\": \"HIGH\",\n"
            "  \"action_required\": \"立即线下就医\",\n"
            "  \"ctcae_grade\": \"Grade 1\",\n"
            "  \"advice\": \"建议立即前往急诊...\",\n"
            "  \"contact_team\": true,\n"
            "  \"evidence\": \"根据 CTCAE v5.0 指南...\",\n"
            "  \"rule_id\": \"QA-H-001\"\n"
            "}\n"
            "```\n"
            "原则：\n"
            "- 必须基于 'rag_query_tool' 的检索结果，禁止凭空捏造。\n"
            "- 如果检索工具未返回相关内容，或内容无法支持判断，必须回复：`{\"status\": \"not_found\"}`。"
        )
        
        self.agent = Assistant(
            llm=self.llm_cfg,
            system_message=self.system_prompt,
            function_list=['rag_query_tool'],
            name=self.name,
            description=self.description
        )

    @traceable(name="RAGAgent Run")
    def run(self, messages: List[dict]) -> Iterator[dict]:
        """
        Run the RAG agent with messages.
        """
        for chunk in self.agent.run(messages):
            yield chunk

    @traceable(name="RAGAgent Chat")
    def chat(self, user_input: str) -> str:
        """
        Synchronous chat helper.
        """
        messages = [{'role': 'user', 'content': user_input}]
        responses = []
        for chunk in self.run(messages):
            responses.append(chunk)
        
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and len(last_msg) > 0:
                return last_msg[-1]['content']
            elif isinstance(last_msg, dict):
                return last_msg.get('content', '')
        return "不清楚"

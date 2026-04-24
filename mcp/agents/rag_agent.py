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
    
    def __init__(self, llm_cfg: dict, name: str = 'RAG_Expert', description: str = '医疗知识专家，负责查询指南和提供专业建议。'):
        self.llm_cfg = llm_cfg
        self.name = name
        self.description = description
        
        self.system_prompt = (
            "你是一个专业的乳腺癌副作用评估专家。你的职责是调用 'rag_query_tool' 检索指南，并严格按以下格式回答：\n\n"
            "1. **风险等级**：[根据指南判断的级别]\n"
            "2. **下一步建议**：[具体的处置指导]\n"
            "3. **是否建议联系团队**：[是/否]\n"
            "4. **简单依据说明**：[简述指南中的判断标准或原因]\n"
            "5. **参考依据ID**：[返回检索到的文档 ID，如 QA-M-004]\n\n"
            "原则：\n"
            "- 必须基于 'rag_query_tool' 的检索结果，禁止凭空捏造。\n"
            "- 如果检索工具未返回相关内容，或内容无法支持判断，必须直接回复：“不清楚”。"
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
        return self.agent.run(messages)

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

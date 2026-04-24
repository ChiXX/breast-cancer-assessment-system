import os
from typing import List, Optional, Union, Iterator
from qwen_agent.agents import Assistant
from langsmith import traceable
import dashscope
from mcp.agents.tools import get_all_skill_metadata

class MedicalMaster:
    """
    MedicalMaster Agent responsible for orchestrating the medical assessment process.
    Uses qwen-agent framework and integrates LangSmith for tracing.
    """
    
    def __init__(self, model_type: str = 'qwen3.5-plus', name: str = 'Medical Assistant'):
        dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')
        self.llm_cfg = {
            'model': model_type,
            'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'api_key': dashscope.api_key,
            'generate_cfg': {
                'top_p': 0.8,
                'temperature': 0.7
            }
        }
        
        # Load all skill metadata for system prompt
        skills_metadata = get_all_skill_metadata()
        skills_info = "\n".join([f"- {m.get('name')}: {m.get('description')}" for m in skills_metadata])
        
        # Define the system prompt for the master agent
        self.system_prompt = (
            "你是一个专业的乳腺癌副作用评估助手。你的任务是通过与患者交流，提取症状、程度、持续时间等信息。\n"
            "以下是系统中可用的评估技能（元数据）：\n"
            f"{skills_info}\n\n"
            "决策逻辑：\n"
            "1. 查阅技能：如果上述元数据中某个技能与用户描述匹配，必须先调用 'read_skill' 查看其完整执行手册，然后严格按照手册指令行事。\n"
            "2. 知识检索：如果没有匹配的技能，请使用 'rag_query_tool' 查询医疗指南（L2级）。\n"
            "3. 沟通原则：回答应专业、富有同情心，并清晰指出任何需要立即就医的红旗信号。信息不足时应主动引导患者补充细节。"
        )
        
        # Tools to be used by the agent
        self.tools = [
            'read_skill',
            'rag_query_tool'
        ]
        
        # Initialize the underlying Qwen Assistant
        self.agent = Assistant(
            llm=self.llm_cfg,
            system_message=self.system_prompt,
            function_list=self.tools,
            name=name
        )

    @traceable(name="MedicalMaster Response Generation")
    def run(self, messages: List[dict]) -> Iterator[dict]:
        """
        Run the agent with the given message history.
        Returns a generator for streaming responses.
        """
        # qwen-agent's run method returns a generator
        return self.agent.run(messages)

    @traceable(name="MedicalMaster Sync Response")
    def chat(self, user_input: str, history: Optional[List[dict]] = None) -> str:
        """
        A synchronous helper for non-streaming interaction.
        """
        if history is None:
            history = []
        
        history.append({'role': 'user', 'content': user_input})
        
        responses = []
        for chunk in self.run(history):
            responses.append(chunk)
        
        if responses:
            # The last chunk in Assistant.run usually contains the final response
            # Format depends on qwen-agent version, but typically it's a list of messages
            last_msg = responses[-1]
            if isinstance(last_msg, list) and len(last_msg) > 0:
                return last_msg[-1]['content']
            elif isinstance(last_msg, dict):
                return last_msg.get('content', '')
        
        return "抱歉，我暂时无法处理您的请求。"

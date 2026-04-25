import os
from typing import List, Optional, Iterator
from qwen_agent.agents import Assistant
import dashscope
from langsmith import traceable

class MemoryAgent:
    """
    MemoryAgent responsible for summarizing and persisting session conversations.
    It can be triggered by a specific command or at the end of a session.
    """
    def __init__(self, model_type: str = 'qwen3.5-plus', name: str = 'Memory Agent'):
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
        
        self.system_prompt = (
            "你是一个记忆管理专家。你的任务是在对话结束或接到指令时，对之前的对话进行总结并归档记忆。\n"
            "这些记忆随后会被 'Learning Agent' 提取并转化为系统技能（Skills）。\n"
            "你需要调用 'create_memory' 工具将对话存储到记忆库中。\n"
            "【关键要求】：\n"
            "1. title（精简标题）：必须采用结构化格式 `[核心症状/问题] - [当前状态/阶段] - [关键处置/动作]`，"
            "例如 '手足综合征(初发) - 中风险 - 已建议就医'，不要写无意义的词（如'症状评估'）。\n"
            "2. summary（一句话总结）：几百字内，明确描述症状变化、最终风险等级以及确认的下一步动作。"
        )
        
        self.tools = [
            'create_memory',
            'summarize_memory'
        ]
        
        self.agent = Assistant(
            llm=self.llm_cfg,
            system_message=self.system_prompt,
            function_list=self.tools,
            name=name
        )

    @traceable(name="MemoryAgent Process")
    def process_session(self, session_id: str, history: List[dict]) -> str:
        """
        Takes the full conversation history, passes it to the agent, and asks it to create a memory.
        """
        # Convert history into a readable string format to be saved
        full_conversation = ""
        for msg in history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            full_conversation += f"[{role.upper()}]: {content}\n\n"
            
        prompt = (
            f"请为会话 {session_id} 创建记忆档案。请总结以下对话，并调用 create_memory 工具进行保存。\n"
            f"注意必须提供 title、summary 和传入我下面给你的完整对话记录：\n"
            f"<full_conversation>\n{full_conversation}\n</full_conversation>"
        )
        
        messages = [{'role': 'user', 'content': prompt}]
        
        responses = []
        for chunk in self.agent.run(messages):
            responses.append(chunk)
            
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and len(last_msg) > 0:
                return last_msg[-1]['content']
            elif isinstance(last_msg, dict):
                return last_msg.get('content', '')
                
        return "记忆处理完成。"

    @traceable(name="MemoryAgent Summarize All")
    def summarize_all(self, session_id: str) -> str:
        prompt = f"请使用 summarize_memory 工具获取会话 {session_id} 的所有历史记忆，并输出一段全局的总结归纳。"
        messages = [{'role': 'user', 'content': prompt}]
        
        responses = []
        for chunk in self.agent.run(messages):
            responses.append(chunk)
            
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and len(last_msg) > 0:
                return last_msg[-1]['content']
            elif isinstance(last_msg, dict):
                return last_msg.get('content', '')
                
        return "总结完成。"

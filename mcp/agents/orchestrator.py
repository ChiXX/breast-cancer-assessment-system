import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import os

from mcp.agents.tools.skill_tools import DiscoverSkills
from mcp.agents.tools.orchestrator_tools import DelegateAssessmentTask, UpdateAgentContext, TerminateTask

class OrchestratorResponse(BaseModel):
    """Orchestrator 的结构化输出模型"""
    thought: str = Field(..., description="对当前对话意图的思考和推理")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="需要调用的工具列表，包含 name 和 arguments")
    reply: Optional[str] = Field(None, description="直接给用户的回复内容")

class OrchestratorPrompt(BaseModel):
    """Orchestrator 的提示词模型"""
    system_prompt: str = (
        "你是健康助手的主代理（Orchestrator）。"
        "你负责识别用户的意图并调度任务。你的首要任务是判断用户是否需要副作用评估。"
        "\n决策逻辑："
        "1. 如果用户描述症状，优先使用 discover_skills 查找是否存在现成的评估技能(L1)。"
        "2. 如果发现匹配技能，或者确认需要进入评估流程，调用 delegate_assessment_task 启动子代理。"
        "3. 如果用户补充了当前评估的信息，使用 update_agent_context。"
        "4. 如果需要查阅历史，使用 search_patient_memory。"
        "5. 如果对话结束，使用 terminate_task。"
    )
    user_input: str
    history: List[Dict[str, str]] = []

    def render(self) -> str:
        """渲染最终提示词"""
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in self.history])
        return (
            f"System: {self.system_prompt}\n"
            f"History:\n{history_str}\n"
            f"User: {self.user_input}\n"
            "Assistant:"
        )

class OrchestratorAgent:
    """
    主 Agent (Orchestrator)
    使用 Pydantic 管理提示词，使用原生 OpenAI API 原生 Tool Calling
    """
    
    def __init__(self, model_name: str = "qwen-max", base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        self.name = "Orchestrator"
        self.model_name = model_name
        self.base_url = base_url
        self.prompt_template = OrchestratorPrompt
        
        # 初始化需要的工具实例
        self.tools_instances = {
            "discover_skills": DiscoverSkills(),
            "delegate_assessment_task": DelegateAssessmentTask(),
            "update_agent_context": UpdateAgentContext(),
            "terminate_task": TerminateTask()
        }
        
        self.client = AsyncOpenAI(
            api_key=os.environ.get("DASHSCOPE_API_KEY", "dummy"),
            base_url=self.base_url
        )

    def _get_api_tools(self) -> List[Dict[str, Any]]:
        """提取工具 schema 列表"""
        api_tools = []
        for name, tool in self.tools_instances.items():
            api_tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        return api_tools

    async def generate_response(self, user_input: str, history: List[Dict[str, str]] = []) -> OrchestratorResponse:
        """生成支持原生 Tool Calling 的结构化回复"""
        prompt_data = self.prompt_template(user_input=user_input, history=history)
        
        messages = [{"role": "system", "content": prompt_data.system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input})
        
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=self._get_api_tools(),
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        # 兼容原有 OrchestratorResponse 数据结构
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                })
                
        return OrchestratorResponse(
            thought=message.content or "执行工具调用", # 如果有工具调用，模型可能只返回 tool_calls 而不返回文本
            tool_calls=tool_calls,
            reply=message.content if not tool_calls else None
        )



import re
import json
from typing import List, Optional, Iterator
from langsmith import traceable
from mcp.agents.base import BaseMedicalAgent
from mcp.agents.config import MEMORY_MODEL, get_llm_cfg

class MemoryAgent(BaseMedicalAgent):
    """
    MemoryAgent responsible for summarizing and persisting session conversations.
    It can be triggered by a specific command or at the end of a session.
    """
    def __init__(self, llm_cfg: Optional[dict] = None, name: str = 'Memory Agent'):
        llm_cfg = llm_cfg or get_llm_cfg(MEMORY_MODEL)
        
        system_prompt = (
            "你是一个记忆管理专家。你的任务是对之前的对话进行总结，提取核心元数据以供归档。\n"
            "【输出格式要求】：\n"
            "必须输出一个标准的 JSON 对象，包含 'title' 和 'summary' 两个字段。\n"
            "1. title: [核心症状] - [当前状态] - [关键处置]\n"
            "2. summary: 一句话简述对话核心结论。\n"
            "注意：只需输出 JSON 块，不要包含任何其他文字。"
        )
        
        tools = [
            'summarize_memory'
        ]
        
        super().__init__(
            llm_cfg=llm_cfg,
            name=name,
            system_prompt=system_prompt,
            tools=tools
        )

    @traceable(name="MemoryAgent Run")
    def run(self, messages: List[dict]) -> Iterator[dict]:
        """
        Standard run method.
        """
        for chunk in self.agent.run(messages):
            yield chunk

    @traceable(name="MemoryAgent Process")
    def process_session(self, session_id: str, history: List[dict]) -> str:
        """
        Takes the full conversation history, passes it to the agent, and asks it to create a memory.
        The memory will only contain a title and a one-sentence summary.
        """
        # 1. Programmatically extract the latest assessment JSON block from history
        latest_assessment = None
        for msg in reversed(history):
            # Check for structured assessment field first
            if 'assessment' in msg and msg['assessment']:
                latest_assessment = msg['assessment']
                break
                
            content = msg.get('content', '')
            if not content:
                continue

            # Find JSON blocks: prioritize ```json ... ``` blocks, then look for raw {}
            json_blocks = re.findall(r'```json\n(.*?)\n```', content, re.DOTALL)
            if not json_blocks:
                # Fallback to finding anything that looks like a JSON object
                json_blocks = re.findall(r'(\{.*\})', content, re.DOTALL)
            
            for j_str in reversed(json_blocks):
                try:
                    data = json.loads(j_str)
                    if data.get('type') == 'evaluation' and 'data' in data:
                        latest_assessment = data['data']
                        break
                    elif 'risk_level' in data and 'advice' in data:
                        latest_assessment = data
                        break
                except:
                    continue
            if latest_assessment:
                break
        
        # 2. Prepare the prompt for the agent
        # Convert history into a readable string format
        conversation_text = ""
        for msg in history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            clean_content = re.sub(r'```json\n.*?\n```', '[ASSESSMENT_JSON]', content, flags=re.DOTALL)
            conversation_text += f"[{role.upper()}]: {clean_content}\n\n"
            
        prompt = (
            f"请根据以下对话记录，为会话 {session_id} 生成记忆归档所需的元数据。\n"
            f"系统已提取到最终评估结果：\n{json.dumps(latest_assessment, ensure_ascii=False, indent=2) if latest_assessment else '未发现明确评估'}\n\n"
            f"【你的任务】：\n"
            f"1. title（精简标题）：采用结构化格式 `[核心症状] - [阶段] - [处置]`。\n"
            f"2. summary（一句话总结100字内）：简述对话核心结论。\n\n"
            f"请严格按以下 JSON 格式输出，不要包含任何其他文字：\n"
            f'{{"title": "...", "summary": "..."}}\n\n'
            f"对话记录：\n{conversation_text}"
        )
        
        # Use LLM directly to avoid tool-calling parsing overhead and potential loops
        # for this simple summarization task.
        messages = [{'role': 'user', 'content': prompt}]
        responses = []
        for chunk in self.agent.llm.chat(messages):
            responses.append(chunk)
            
        agent_output = ""
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and last_msg:
                agent_output = last_msg[-1].get('content', '')
            elif isinstance(last_msg, dict):
                agent_output = last_msg.get('content', '')

        # 3. Parse Agent Output and Finalize Memory
        title = "未命名会话"
        summary = "无总结"
        
        try:
            # Extract JSON from output
            json_match = re.search(r'\{.*\}', agent_output, re.DOTALL)
            if json_match:
                metadata = json.loads(json_match.group(0))
                title = metadata.get('title', title)
                summary = metadata.get('summary', summary)
        except Exception as e:
            # Fallback to simple extraction if JSON parsing fails
            if "title" in agent_output and "summary" in agent_output:
                # Basic line-based fallback could be added here
                pass

        # 4. Programmatically call the CreateMemory tool to save the file
        from mcp.agents.tools.memory_tools import CreateMemory
        cm = CreateMemory()
        result = cm.call({
            'session_id': session_id,
            'title': title,
            'summary': summary,
            'full_conversation': "", # We don't store full text in memory files to save space
            'assessment': latest_assessment or {}
        })
        
        if result.get('status') == 'success':
            return f"记忆已归档：{title} (Path: {result.get('path')})"
        else:
            return f"归档失败：{result.get('message')}"

    @traceable(name="MemoryAgent Summarize All")
    def summarize_all(self, session_id: str) -> str:
        prompt = f"请使用 summarize_memory 工具获取会话 {session_id} 的所有历史记忆，并输出一段全局的总结归纳。"
        return self.chat(prompt)

import os
from typing import List, Optional, Iterator
from qwen_agent.agents import Assistant
import dashscope
from langsmith import traceable
from mcp.agents.tools.memory_tools import CreateMemory, SummarizeMemoryTool

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
            "你是一个记忆管理专家。你的任务是对之前的对话进行总结，提取核心元数据以供归档。\n"
            "这些记忆随后会被 'Learning Agent' 提取并转化为系统技能（Skills）。\n"
            "【输出格式要求】：\n"
            "你必须输出一个 JSON 对象，包含 'title' 和 'summary' 两个字段。\n"
            "1. title（精简标题）：必须采用结构化格式 `[核心症状/问题] - [当前状态/阶段] - [关键处置/动作]`，"
            "例如 '手足综合征(初发) - 中风险 - 已建议就医'。\n"
            "2. summary（一句话总结）：明确描述症状变化、最终风险等级以及确认的下一步动作。\n\n"
            "注意：只需输出 JSON 块，不要包含任何其他解释文字。如果是调用 summarize_memory 工具，请按工具规范执行。"
        )
        
        self.tools = [
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
        The memory will only contain a title and a one-sentence summary.
        """
        # 1. Programmatically extract the latest assessment JSON block from history
        import re
        import json
        latest_assessment = None
        # Search backwards from the end of history
        for msg in reversed(history):
            raw_data = None
            
            # 1. First, check if there's a structured 'assessment' field (modern format)
            if 'assessment' in msg and msg['assessment']:
                raw_data = msg['assessment']
            
            # 2. If not, try to parse from content (legacy/fallback format)
            if not raw_data:
                content = msg.get('content', '')
                # Improved JSON extraction: find all potential JSON blocks or objects
                # 1. Look for ```json ... ``` blocks
                json_blocks = re.findall(r'```(?:json)?\n?(.*?)\n?```', content, re.DOTALL)
                # 2. Also try to find raw JSON-like structures if no blocks found
                if not json_blocks and content.strip().startswith('{') and content.strip().endswith('}'):
                    json_blocks = [content.strip()]
                
                for j_str in reversed(json_blocks):
                    try:
                        data = json.loads(j_str)
                        if data.get('type') == 'evaluation' and 'data' in data:
                            raw_data = data['data']
                        elif 'risk_level' in data and 'advice' in data:
                            # Filter out stub/fallback assessments
                            risk = str(data.get('risk_level', '')).upper()
                            rule_id = str(data.get('rule_id', '')).upper()
                            if risk != '未知' and risk != 'UNKNOWN' and rule_id != 'N/A':
                                raw_data = data
                        
                        if raw_data:
                            break
                    except:
                        continue
            
            if raw_data:
                # Normalize to standard EvaluationData schema
                # Ensure risk_level is uppercase and ctcae_grade is in "Grade X" format
                raw_risk = raw_data.get("risk_level")
                raw_grade = raw_data.get("ctcae_grade")
                
                # Final check to ensure we don't save "UNKNOWN" as a valid memory assessment
                if str(raw_risk).upper() in ['UNKNOWN', '未知', 'N/A']:
                    raw_data = None
                    continue

                latest_assessment = {
                    "risk_level": str(raw_risk).upper() if raw_risk else None,
                    "action_required": raw_data.get("action_required"),
                    "ctcae_grade": f"Grade {raw_grade}" if isinstance(raw_grade, (int, float)) else raw_grade,
                    "advice": raw_data.get("advice"),
                    "contact_team": raw_data.get("contact_team"),
                    "evidence": raw_data.get("evidence"),
                    "rule_id": raw_data.get("rule_id") or raw_data.get("matched_rule_id")
                }
                # Filter out None values and ensure consistent types
                latest_assessment = {k: v for k, v in latest_assessment.items() if v is not None}
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
            f"2. summary（一句话总结）：简述对话核心结论。\n\n"
            f"请严格按以下 JSON 格式输出，不要包含任何其他文字：\n"
            f'{{"title": "...", "summary": "..."}}\n\n'
            f"对话记录：\n{conversation_text}"
        )
        
        messages = [{'role': 'user', 'content': prompt}]
        
        # We use a separate loop to get the text response
        responses = []
        for chunk in self.agent.run(messages):
            responses.append(chunk)
            
        agent_output = ""
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and len(last_msg) > 0:
                # Find the last assistant message
                for m in reversed(last_msg):
                    if m.get('role') == 'assistant' and m.get('content'):
                        agent_output = m.get('content')
                        break
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
            print(f"Error parsing agent metadata: {e}")
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
        messages = [{'role': 'user', 'content': prompt}]
        
        responses = []
        for chunk in self.agent.run(messages):
            responses.append(chunk)
            
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and len(last_msg) > 0:
                for m in reversed(last_msg):
                    if m.get('role') == 'assistant' and m.get('content'):
                        return m.get('content')
            elif isinstance(last_msg, dict):
                return last_msg.get('content', '')
                
        return "总结完成。"

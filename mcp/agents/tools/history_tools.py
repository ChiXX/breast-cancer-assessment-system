import os
import httpx
import json
from typing import Union
from qwen_agent.tools.base import BaseTool, register_tool
from langsmith import traceable

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

@register_tool('read_memory_conversation')
class ReadMemoryConversation(BaseTool):
    description = '从后端数据库获取指定会话的全量历史对话原文。当需要深入了解过去的沟通细节、语气或具体主诉时使用。'
    parameters = {
        'type': 'object',
        'properties': {
            'session_id': {
                'type': 'string',
                'description': '需要查询的会话ID'
            }
        },
        'required': ['session_id']
    }

    @traceable(name="Read Memory Conversation Tool")
    def call(self, params: Union[str, dict], **kwargs):
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                return {'status': 'error', 'message': 'Invalid params'}
        
        session_id = params.get('session_id')
        if not session_id:
            return {'status': 'error', 'message': 'session_id is required'}
            
        url = f"{BACKEND_URL}/api/v1/assessments/history?session_id={session_id}"
        
        try:
            # trust_env=False to avoid proxy issues in some environments
            with httpx.Client(timeout=10.0, trust_env=False) as client:
                response = client.get(url)
                response.raise_for_status()
                history = response.json()
                return {'status': 'success', 'history': history}
        except Exception as e:
            return {'status': 'error', 'message': f"Failed to fetch conversation history: {str(e)}"}

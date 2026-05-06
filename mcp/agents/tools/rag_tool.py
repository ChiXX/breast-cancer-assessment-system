import json
from qwen_agent.tools.base import BaseTool, register_tool
from langsmith import traceable
from typing import Union
from mcp.agents.rag_agent import RAGAgent

@register_tool('rag_query_tool')
class RAGQueryTool(BaseTool):
    description = '使用 RAG 专家 Agent 查询乳腺癌副作用知识库并给出评估。当技能库(Skills)和记忆(Memory)无法解答时调用此工具。'
    parameters = {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': '患者的具体症状描述或需要评估的问题'
            }
        },
        'required': ['query']
    }

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.rag_agent = None

    @traceable(name="RAG Agent Tool Call")
    def call(self, params: Union[str, dict], **kwargs) -> str:
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                query = params
            else:
                query = params.get('query', '')
        else:
            query = params.get('query', '')
            
        if not query:
            return json.dumps({"status": "error", "message": "No query provided."}, ensure_ascii=False)
            
        if self.rag_agent is None:
            self.rag_agent = RAGAgent()
            
        try:
            from mcp.utils.event_logger import eventlog
            eventlog("RAG_QUERY_TOOL", f"Calling RAGAgent with query: {query}", {"query": query})
            
            result = self.rag_agent.chat(query)
            return result
        except Exception as e:
            from mcp.utils.event_logger import eventlog
            eventlog("ERROR", f"Error in RAGAgent tool: {str(e)}", {"error": str(e)})
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

from qwen_agent.agents import Assistant
from mcp.agents.tools.rag_tool import RAGQueryTool

class AssessmentAgent(Assistant):
    """
    子 Agent (Assessment)
    """
    def __init__(self, **kwargs):
        if 'function_list' not in kwargs:
            kwargs['function_list'] = ['rag_query_tool']
        
        if 'system_message' not in kwargs:
            kwargs['system_message'] = (
                "You are a medical assistant. Use the rag_query_tool to query the database and answer user questions about side effects.\n"
                "Constraints:\n"
                "1. If the tool returns 'No relevant information found.' or you cannot find an answer, reply exactly with '未检索到答案' and nothing else.\n"
                "2. If you find an answer, you MUST format your response strictly as a JSON string (do not wrap it in markdown code blocks like ```json). It must contain exactly these keys:\n"
                "  - \"风险等级\" (The risk level, e.g., 高风险/中风险/低风险)\n"
                "  - \"下一步建议\" (What the patient should do next)\n"
                "  - \"是否建议联系团队\" (是/否)\n"
                "  - \"简单依据说明\" (Brief explanation based on the retrieved data)\n"
                "  - \"参考来源\" (The ID from the retrieved tool result)\n"
                "Do not output any additional text or explanations outside of the JSON."
            )
            
        if 'name' not in kwargs:
            kwargs['name'] = 'Assessment Sub Agent'
            
        super().__init__(**kwargs)

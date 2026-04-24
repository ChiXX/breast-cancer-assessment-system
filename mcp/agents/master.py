import os
import json
from typing import List, Optional, Union, Iterator
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from langsmith import traceable
import dashscope
from mcp.agents.tools import get_all_skill_metadata
from mcp.agents.rag_agent import RAGAgent

class MedicalMaster:
    """
    MedicalMaster Agent responsible for orchestrating the medical assessment process.
    Uses qwen-agent Router framework and integrates LangSmith for tracing.
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
        
        # Initialize sub-agents
        self.rag_expert = RAGAgent(llm_cfg=self.llm_cfg)
        
        # Define a wrapper tool for RAG_Expert to make it more reliable for the Assistant
        rag_expert_instance = self.rag_expert
        @register_tool('RAG_Expert')
        class RAGExpertTool(BaseTool):
            description = '医疗知识专家，负责查询指南和提供专业建议。当用户提到症状时必须调用。'
            parameters = {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': '需要查询的症状或问题描述'
                    }
                },
                'required': ['query']
            }

            def call(self, params: Union[str, dict], **kwargs) -> str:
                if isinstance(params, str):
                    try:
                        params = json.loads(params)
                    except json.JSONDecodeError:
                        query = params
                    else:
                        query = params.get('query', params)
                else:
                    query = params.get('query', '')
                # Call the agent synchronously
                return rag_expert_instance.chat(query)

        # Load all skill metadata for system prompt
        skills_metadata = get_all_skill_metadata()
        skills_info = "\n".join([f"- {m.get('name')}: {m.get('description')}" for m in skills_metadata])
        
        # Load historical memory clues (Shared across all sessions)
        historical_memory_text = "暂无历史记忆。"
        from mcp.agents.tools.memory_tools import ReadMemoryList
        memory_list_tool = ReadMemoryList()
        res = memory_list_tool.call({})
        if res.get('status') == 'success' and res.get('memories'):
            clues = []
            for mem in res['memories']:
                clues.append(f"- 时间: {mem['timestamp']} | 会话: {mem['session_id']} | 标题: {mem['title']}")
            historical_memory_text = "以下为已有历史记忆档案的线索：\n" + "\n".join(clues) + "\n\n(提示：请根据上述线索，通过调用 'read_memory_detail' 工具并提供对应的 session_id 和 timestamp 获取详细记录。)"
                
        # Define the system prompt for the master agent
        self.system_prompt = (
            "你是一个专业的医疗服务中控（客服）。你的职责是作为患者与医疗专家系统之间的桥梁，负责初步接待、意图识别和资源调度。\n"
            "每次对话开始时，你应当调用 'read_memory_list' 获取当前会话的历史记忆，并根据需要调用 'read_memory_detail' 了解上下文。\n"
            "以下是系统中可用的专家工具与评估技能：\n"
            "## 专家工具\n"
            f"- RAG_Expert: {self.rag_expert.description}\n\n"
            "## 评估技能\n"
            f"{skills_info}\n\n"
            "## 历史记忆\n"
            f"{historical_memory_text}\n\n"
            "工作准则：\n"
            "1. **中控定位**：你不是医生，严禁直接给出医疗建议。你的任务是合理调度工具与记忆资源。\n"
            "2. **记忆优先与工具调用**：只要用户提到症状，**首先**检查【历史记忆】。如果历史记忆中已有该症状相关的可参考回答或评估，你可以优先复用该记忆或调用 'read_memory_detail' 查阅详情，而无需重复调用 'RAG_Expert'。如果记忆中没有相关内容，你必须立即调用 'RAG_Expert'。若信息依然缺失，再配合 'read_skill' 查看手册进行极简追问。\n"
            "3. **服务态度**：态度专业且亲切，内容必须极致简洁。每次回复只准提一个最核心的问题，追问总数不超 2 次。\n"
            "4. **信息汇总**：作为中控，你应将评估结果（无论是来自 'RAG_Expert' 还是【历史记忆】）**原样转达**给用户，严禁改动其格式或核心内容（如风险等级、ID等）。你只需在前面添加简洁的开场白，或在末尾进行必要的补充提醒。"
        )
        
        # Tools to be used by the Assistant
        self.tools = [
            'read_skill',
            'RAG_Expert',
            'read_memory_list',
            'read_memory_detail'
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

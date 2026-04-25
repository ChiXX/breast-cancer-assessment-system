import os
import json
from typing import List, Optional, Union, Iterator
from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from langsmith import traceable
import dashscope
from mcp.agents.tools import get_all_skill_metadata
from mcp.agents.rag_agent import RAGAgent
from mcp.agents.learning_agent import LearningAgent
from mcp.agents.config import MASTER_MODEL, get_llm_cfg

class MedicalMaster:
    """
    MedicalMaster Agent responsible for orchestrating the medical assessment process.
    Uses qwen-agent Router framework and integrates LangSmith for tracing.
    """
    
    def __init__(self, model_type: str = MASTER_MODEL, name: str = 'Medical Assistant'):
        dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')
        self.llm_cfg = get_llm_cfg(model_type)
        
        # Initialize sub-agents
        self.rag_expert = RAGAgent(llm_cfg=self.llm_cfg)
        self.learning_agent = LearningAgent(llm_cfg=self.llm_cfg)
        
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
        
        # Load unlearned historical memory clues (Shared across all sessions)
        historical_memory_text = "暂无未学习的历史记忆线索。"
        from mcp.agents.tools.memory_tools import ReadMemoryList
        memory_list_tool = ReadMemoryList()
        res = memory_list_tool.call({'learned': False})
        if res.get('status') == 'success' and res.get('memories'):
            clues = []
            for mem in res['memories']:
                clues.append(f"- 时间: {mem['timestamp']} | 会话: {mem['session_id']} | 标题: {mem['title']}")
            historical_memory_text = "以下为尚未提炼为技能的最近记忆线索（未学习）：\n" + "\n".join(clues) + "\n\n(提示：请优先参考 Skills 库。如果匹配不到，再查阅这些最近记忆。)"
                
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
            "2. **检索优先级 (CRITICAL)**：\n"
            "   - **Top Priority: Skills**: 首先检查【评估技能】库。如果匹配，直接参考其手册（read_skill）回答。\n"
            "   - **Secondary: Memory**: 如果 Skills 未命中，检查【未学习的历史记忆】。如果匹配，调用 'read_memory_detail' 查阅详情。\n"
            "   - **Last Resort: RAG**: 若以上均无匹配，调用 'RAG_Expert' 获取最新指南。\n"
            "3. **服务态度**：态度专业且亲切，内容必须极致简洁。每次回复只准提一个最核心的问题，追问总数不超 2 次。\n"
            "4. **结构化回答硬约束 (IMPORTANT)**：当你转达来自 RAG_Expert 或 Skills 的评估结果时，**必须严格按照以下四个部分进行结构化回复**，严禁改动标题：\n"
            "   - **风险等级**：[标注风险级别]\n"
            "   - **下一步建议**：[具体的处置指导与生活护理建议]\n"
            "   - **是否建议联系团队**：[是/否]\n"
            "   - **参考依据和说明**：[简述指南标准、判断逻辑及参考 ID]\n"
            "   (如果是日常寒暄或追问，则无需遵循此四部分结构)"
        )
        
        # Tools to be used by the Assistant
        self.tools = [
            'read_skill',
            'RAG_Expert',
            'read_memory_list',
            'read_memory_detail',
            'resolve_skill_references'
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
        # 在 LangSmith 中注入系统提示词和工具元数据，提高监控可见性
        from langsmith import get_current_run_tree
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.metadata.update({
                "system_prompt": self.system_prompt,
                "tools": self.tools,
                "model": self.llm_cfg.get('model')
            })
            
        # Change from return to yield loop so @traceable can capture the generator output
        for chunk in self.agent.run(messages):
            yield chunk

    @traceable(name="MedicalMaster Sync Response")
    def chat(self, user_input: str, history: Optional[List[dict]] = None) -> str:
        """
        A synchronous helper for non-streaming interaction.
        """
        if history is None:
            history = []
        
        # 1. 检查是否触发手动学习
        if user_input.strip() == "/learn":
            return self.learning_agent.run(force=True)
            
        # 2. 自动检查学习 (静默执行或返回提示)
        # 这里我们简单地在每次对话前检查一下
        self.learning_agent.run()

        history.append({'role': 'user', 'content': user_input})
        
        responses = []
        for chunk in self.run(history):
            responses.append(chunk)
        
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and len(last_msg) > 0:
                return last_msg[-1]['content']
            elif isinstance(last_msg, dict):
                return last_msg.get('content', '')
        
        return "抱歉，我暂时无法处理您的请求。"

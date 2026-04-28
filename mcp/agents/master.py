from typing import List, Optional, Iterator
from langsmith import traceable
from mcp.agents.base import BaseMedicalAgent
from mcp.agents.tools import get_all_skill_metadata
from mcp.agents.learning_agent import LearningAgent
from mcp.agents.config import MASTER_MODEL, LEARNING_MODEL, get_llm_cfg

class MedicalMaster(BaseMedicalAgent):
    """
    MedicalMaster Agent responsible for orchestrating the medical assessment process.
    Uses qwen-agent Router framework and integrates LangSmith for tracing.
    """
    
    def __init__(self, llm_cfg: Optional[dict] = None, name: str = 'Medical Assistant'):
        llm_cfg = llm_cfg or get_llm_cfg(MASTER_MODEL)
        
        # Initialize sub-agents
        self.learning_agent = LearningAgent(llm_cfg=get_llm_cfg(LEARNING_MODEL))
        
        # Initial prompt generation
        system_prompt = self._generate_system_prompt()
        
        # Tools to be used by the Assistant
        tools = [
            'read_skill',
            'resolve_skill_references',
            'read_memory_list',
            'read_memory_detail',
            'read_memory_conversation',
            'rag_query_tool',
        ]
        
        super().__init__(
            llm_cfg=llm_cfg,
            name=name,
            system_prompt=system_prompt,
            tools=tools
        )

    def _generate_system_prompt(self) -> str:
        """
        Generates the system prompt dynamically based on current skills and memories.
        """
        # Load all skill metadata for system prompt
        skills_metadata = get_all_skill_metadata()
        skills_info = "\n".join([f"- {m.get('name')}: {m.get('description')}" for m in skills_metadata])
        if not skills_info:
            skills_info = "暂无可用技能库。"
        
        # Load unlearned historical memory clues
        historical_memory_text = "暂无未学习的历史记忆线索。"
        from mcp.agents.tools.memory_tools import ReadMemoryList
        memory_list_tool = ReadMemoryList()
        res = memory_list_tool.call({'learned': False})
        if res.get('status') == 'success' and res.get('memories'):
            clues = []
            for mem in res['memories']:
                assessment = mem.get('assessment', {})
                risk_info = f" | 风险: {assessment.get('risk_level', '未知')}" if assessment else ""
                clues.append(f"- 时间: {mem['timestamp']} | 会话: {mem['session_id']} | 标题: {mem['title']}{risk_info}\n  总结: {mem['summary']}")
            historical_memory_text = "以下为尚未提炼为技能的最近记忆线索（未学习）：\n" + "\n".join(clues) + "\n\n(提示：请优先参考 Skills 库。如果匹配不到且需要详细评估数据，请调用 read_memory_detail 获取该会话的完整记忆内容。)"
                
        
        return (
            "你是一个高度专业的乳腺癌副作用评估系统。你负责通过对话收集患者症状，并在信息充分时提供基于指南的评估。\n\n"
            "以下是系统中可用的评估资源：\n"
            "## 评估技能（Skills）\n"
            f"{skills_info}\n\n"
            "## 历史记忆（Memory）\n"
            f"{historical_memory_text}\n\n"
            "### 【核心任务】\n"
            "1. **信息收集**：如果患者描述不全，请进行追问（question）。追问必须简单明了，字数限制在50字以内。最多只允许追问两次。如果追问两次后信息仍不全，请基于现有信息给出初步评估或引导就医。\n"
            "2. **专业评估**：一旦信息充足，必须通过调用技能库、检索历史记忆（Memory）或使用 `rag_query_tool` 获取指南依据。\n"
            "   - **【强制要求】**：如果工具返回了完整的评估 JSON（包含 risk_level, action_required 等），你**必须原封不动**地将其放入输出 JSON 的 `data` 字段中。严禁修改任何字段值（如 Grade 或风险等级）。\n"
            "   - 你只需根据评估结果，在 `display_text` 中提供一段自然语言的开场白或简述即可。\n\n"
            "### 【风险分级与行动映射参考】\n"
            "（用于追问决策参考，最终输出以工具返回为准）：\n"
            "1. **高风险 (HIGH)** + **立即线下就医** + **Grade 1**\n"
            "2. **高风险 (HIGH)** + **24小时内联系团队** + **Grade 2**\n"
            "3. **中风险 (MEDIUM)** + **联系团队** + **Grade 3**\n"
            "4. **中风险 (MEDIUM)** + **密切观察** + **Grade 4**\n"
            "5. **低风险 (LOW)** + **继续观察与记录** + **Grade 5**\n\n"
            "### 【工作准则】\n"
            "1. **中控定位**：你的任务是合理调度工具与资源。你是评估流程的组织者，而不是决策的修改者。\n"
            "2. **检索优先级**：Skills > Memory > rag_query_tool。\n"
            "3. **最终回复格式 (HARD REQUIREMENT)**：当你准备好向用户（患者）进行【追问】或提供【评估结果】时，你**必须且只能**以 JSON 格式返回。严禁在 JSON 块之外添加任何解释文字。\n\n"
            "注意：在调用工具时，请直接按照系统预设的工具调用格式输出，严禁将工具调用过程包装在上述 JSON 最终回复格式中。"
            "### 【输出协议】\n"
            "1. **必须包含 `type` 字段**，值只能是 `evaluation` 或 `question`。\n"
            "2. **如果是 `evaluation`**：\n"
            "   - 必须包含 `data` 对象（直接复用工具返回的评估 JSON）。\n"
            "   - 必须包含 `display_text` 字符串。\n"
            "3. **如果是 `question`**：\n"
            "   - 必须包含 `content` 字符串，即你对患者的追问内容。\n\n"
            "### 输出示例 (Evaluation):\n"
            "```json\n"
            "{\n"
            "  \"type\": \"evaluation\",\n"
            "  \"display_text\": \"根据您的描述，我们为您整理了以下评估结果：\",\n"
            "  \"data\": {\n"
            "    \"risk_level\": \"HIGH\",\n"
            "    \"action_required\": \"立即线下就医\",\n"
            "    \"ctcae_grade\": \"Grade 1\",\n"
            "    \"advice\": \"建议立即前往最近的急诊科...\",\n"
            "    \"contact_team\": true,\n"
            "    \"evidence\": \"符合 CTCAE v5.0 发热性中性粒细胞减少标准...\",\n"
            "    \"rule_id\": \"QA-H-001\"\n"
            "  }\n"
            "}\n"
            "```\n\n"
            "### 输出示例 (Question):\n"
            "```json\n"
            "{\n"
            "  \"type\": \"question\",\n"
            "  \"content\": \"请问您的手麻症状是在化疗后多久出现的？\"\n"
            "}\n"
            "```"
        )

    @traceable(name="MedicalMaster Response Generation")
    def run(self, messages: List[dict]) -> Iterator[dict]:
        """
        Run the agent with the given message history.
        Returns a generator for streaming responses.
        """
        # Refresh system prompt to include latest skills/memories
        self.system_prompt = self._generate_system_prompt()
        self.agent.system_message = self.system_prompt
        
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
    def chat(self, user_input: str, session_id: str = "default_session", history: Optional[List[dict]] = None) -> str:
        """
        A synchronous helper for non-streaming interaction.
        """
        if history is None:
            history = []
        
        # 1. 检查是否触发手动学习
        if user_input.strip() == "/learn":
            return self.learning_agent.start_learning(force=True)
            
        # Add session information to the first user message or as a system hint
        # We can prepend it to the current input to ensure the agent knows the session_id for tools
        context_input = f"[Session ID: {session_id}]\n{user_input}"
        history.append({'role': 'user', 'content': context_input})
        
        responses = []
        for chunk in self.run(history):
            responses.append(chunk)
        
        if responses:
            last_msg = responses[-1]
            content = ""
            if isinstance(last_msg, list) and len(last_msg) > 0:
                content = last_msg[-1].get('content', '')
            elif isinstance(last_msg, dict):
                content = last_msg.get('content', '')
            
            return content if content else "抱歉，我暂时无法处理您的请求。"
        
        return "抱歉，我暂时无法处理您的请求。"

from typing import List, Iterator, Optional
from langsmith import traceable
from mcp.agents.base import BaseMedicalAgent
from mcp.agents.config import EXPERT_MODEL, get_llm_cfg

class RAGAgent(BaseMedicalAgent):
    """
    RAGAgent is a specialized medical knowledge agent.
    It uses the rag_query_tool to retrieve information from medical guidelines.
    """
    
    def __init__(self, llm_cfg: Optional[dict] = None, name: str = 'RAG_Expert'):
        llm_cfg = llm_cfg or get_llm_cfg(EXPERT_MODEL)
        
        
        system_prompt = (
            f"你是一个专业的乳腺癌副作用评估专家。你的职责是调用 'rag_query_tool' 检索指南，并严格按 JSON 格式回答。\n\n"
            f"### 【评估标准映射】\n"
            "1. **HIGH** + **立即线下就医** + **Grade 1**\n"
            "2. **HIGH** + **24小时内联系团队** + **Grade 2**\n"
            "3. **MEDIUM** + **联系团队** + **Grade 3**\n"
            "4. **MEDIUM** + **密切观察** + **Grade 4**\n"
            "5. **LOW** + **继续观察与记录** + **Grade 5**\n\n"
            "### 输出格式：\n"
            "```json\n"
            "{\n"
            "  \"risk_level\": \"HIGH\",\n"
            "  \"action_required\": \"立即线下就医\",\n"
            "  \"ctcae_grade\": \"Grade 1\",\n"
            "  \"advice\": \"建议立即前往急诊...\",\n"
            "  \"contact_team\": true,\n"
            "  \"evidence\": \"根据 CTCAE v5.0 指南...\",\n"
            "  \"rule_id\": \"QA-H-001\"\n"
            "}\n"
            "```\n"
            "原则：\n"
            "- `rag_query_tool` 每次会召回 3 个候选答案。你的核心任务是判断召回的内容中是否有可以回答患者问题的。\n"
            "- 必须选择**最相关的一个**答案作为依据进行评估，**严禁融合多个答案**的内容。\n"
            "- 必须基于选出的这单一检索结果进行判断，禁止凭空捏造，将多个答案进行融合。\n"
            "- 如果检索工具未返回相关内容，或 3 个答案都无法支持判断，必须回复：`{\"status\": \"not_found\"}`。"
        )
        
        super().__init__(
            llm_cfg=llm_cfg,
            name=name,
            system_prompt=system_prompt,
            tools=['rag_query_tool']
        )

    @traceable(name="RAGAgent Run")
    def run(self, messages: List[dict]) -> Iterator[dict]:
        """
        Run the RAG agent with messages.
        """
        for chunk in self.agent.run(messages):
            yield chunk

    @traceable(name="RAGAgent Chat")
    def chat(self, user_input: str, history: Optional[List[dict]] = None) -> str:
        """
        Synchronous chat helper.
        """
        return super().chat(user_input, history)

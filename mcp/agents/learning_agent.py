import os
from typing import List, Dict, Optional, Iterator
from langsmith import traceable
from mcp.agents.base import BaseMedicalAgent
from mcp.agents.reviewer_agent import ReviewerAgent
from mcp.agents.config import LEARNING_MODEL, REVIEWER_MODEL, get_llm_cfg
import mcp.agents.tools # Ensure tools are registered

class LearningAgent(BaseMedicalAgent):
    """
    LearningAgent is responsible for distilling fragmented session memories 
    into structured, high-priority knowledge (Skills).
    """
    def __init__(self, llm_cfg: Optional[dict] = None, name: str = 'Learning Agent'):
        llm_cfg = llm_cfg or get_llm_cfg(LEARNING_MODEL)
        
        system_prompt = (
            "你是一个医疗决策知识提炼专家。你的任务是将散乱的会话记忆（Sessions）提炼为精准、唯一的‘症状-风险映射字典’。\n\n"
            "### 【核心行为准则】\n"
            "1. **必要性评估 (Necessity)**：并非每次对话都需要提炼知识。只有当对话中包含‘未曾记录的症状’、‘更优的处置逻辑’或‘更细致的风险判定标准’时，才执行更新。\n"
            "2. **逻辑优选 (Superiority)**：如果新对话中的判定更专业，应更新现有内容。\n"
            "3. **冲突检查 (Conflict Check)**：确保整个‘医疗决策字典’内部逻辑自洽。\n"
            "4. **【红线约束】原样提炼**：从记忆 JSON 中原样提取 `assessment` 对象并持久化到 Skill 资源文件中。**严禁对评估逻辑、风险等级、依据 ID 进行任何二次加工或幻觉。**\n"
            "5. **结构化维护 (SKILL.md Standard)**：\n"
            "   - **顶级目录**：使用 `SKILL.md` 作为技能入口。包含 `name` 和 `description` 在 YAML frontmatter 中。**技能名称固定使用 `chemotherapy-side-effect-triage`。**\n"
            "   - **子资源**：具体的症状评估逻辑存放在 `.md` 文件中（如 `alopecia.md`）。\n"
            "   - **内容格式**：资源文件内部应包含一个描述性的 Markdown 正文，且必须包含一个包含结构化 JSON 数据（即原样提取的 `assessment` 对象）的代码块。\n\n"
            "### 【工作流程约束】\n"
            "- **原子化更新**：更新应针对具体的子资源文件（如 `rash.md`）。\n"
            "- **闭环**：处理完记忆后必须调用 `mark_memory_learned`。"
        )
        
        tools = [
            'read_memory_list',
            'read_memory_detail',
            'read_skill',
            'resolve_skill_references',
            'upsert_skill',
            'upsert_skill_resource',
            'mark_memory_learned'
        ]
        
        super().__init__(
            llm_cfg=llm_cfg,
            name=name,
            system_prompt=system_prompt,
            tools=tools
        )
        
        # Reviewer agent is a sub-agent
        self.reviewer_llm_cfg = get_llm_cfg(REVIEWER_MODEL)
        self.reviewer = ReviewerAgent(llm_cfg=self.reviewer_llm_cfg)

    @traceable(name="LearningAgent Run")
    def run(self, messages: List[dict]) -> Iterator[dict]:
        """
        Standard run method.
        """
        for chunk in self.agent.run(messages):
            yield chunk

    @traceable(name="LearningAgent Learning Workflow")
    def start_learning(self, force: bool = False) -> str:
        """
        Runs the full learning workflow.
        """
        # First, check unlearned memories
        prompt = "请检查是否有尚未学习（learned: false）的记忆文档。如果有，请开始学习工作流，提炼知识并更新 Skill 库（遵循 SKILL.md 标准）。【重要】：请统一更新到 `chemotherapy-side-effect-triage` 技能中。处理完后记得标记为已学习。"
        
        if not force:
            unlearned_count = self._get_unlearned_count()
            if unlearned_count < 5:
                return f"尚未达到自动学习阈值 (当前未学习: {unlearned_count}/5)。"

        messages = [{'role': 'user', 'content': prompt}]
        
        responses = []
        for chunk in self.run(messages):
            responses.append(chunk)
            
        result_str = "学习任务执行完毕。"
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and len(last_msg) > 0:
                result_str = last_msg[-1].get('content', result_str)
            elif isinstance(last_msg, dict):
                result_str = last_msg.get('content', result_str)
                
        # Trigger ReviewerAgent for mandatory audit
        print("Triggering ReviewerAgent for audit...")
        skill_name = "chemotherapy-side-effect-triage"
        skill_dir = os.path.join(os.path.abspath("mcp/agents/skills"), skill_name)
        if os.path.exists(skill_dir):
            resources = [f for f in os.listdir(skill_dir) if f.endswith('.md')]
            resources = [r for r in resources if r != 'SKILL.md']
            review_result = self.reviewer.audit(skill_name, resources)
            return f"{result_str}\n\n### 【审计报告】\n{review_result}"
            
        return result_str

    def _get_unlearned_count(self) -> int:
        from mcp.agents.tools.memory_tools import ReadMemoryList
        tool = ReadMemoryList()
        result = tool.call({'learned': False})
        if result.get('status') == 'success':
            return len(result.get('memories', []))
        return 0

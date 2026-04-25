import os
import dashscope
from typing import List, Dict
from qwen_agent.agents import Assistant
from langsmith import traceable
from mcp.agents.reviewer_agent import ReviewerAgent
from mcp.agents.config import REVIEWER_MODEL, get_llm_cfg
import mcp.agents.tools # Ensure tools are registered

class LearningAgent:
    """
    LearningAgent is responsible for distilling fragmented session memories 
    into structured, high-priority knowledge (Skills).
    """
    def __init__(self, llm_cfg: dict, name: str = 'Learning Agent'):
        self.llm_cfg = llm_cfg
        # Reviewer model controlled by config
        self.reviewer_llm_cfg = get_llm_cfg(REVIEWER_MODEL)
        self.reviewer = ReviewerAgent(llm_cfg=self.reviewer_llm_cfg)
        
        self.system_prompt = (
            "你是一个医疗决策知识提炼专家。你的任务是将散乱的会话记忆（Sessions）提炼为精准、唯一的‘症状-风险映射字典’。\n\n"
            "### 【核心行为准则】\n"
            "1. **必要性评估 (Necessity)**：并非每次对话都需要提炼知识。只有当对话中包含‘未曾记录的症状’、‘更优的处置逻辑’或‘更细致的风险判定标准’时，才执行更新。如果现有字典已覆盖且逻辑一致，仅标记记忆为已学习即可。\n"
            "2. **逻辑优选 (Superiority)**：如果新对话中的处置建议或风险判定比现有手册更专业、更符合最新指南或逻辑更严密，应果断更新现有内容。新知识通常具有更高的参考价值。\n"
            "3. **冲突检查 (Conflict Check)**：在更新前，必须查阅现有 Skill 内容。如果新提炼的知识与旧有条款存在冲突，必须进行消歧处理，确保整个‘医疗决策字典’内部逻辑自洽，严禁出现矛盾的判定标准。\n"
            "4. **词典化维护与输出规范**：坚持‘单一 Skill (medical_consultation_workflow) + 多子资源 (.md)’的结构。`SKILL.md` 仅作为索引映射。\n"
            "   - **输出格式约束**：资源文件（如 `fever.md`）中的每一项知识条目（如每个 Grade）必须严格包含以下字段：\n"
            "     - **风险等级**：明确标注（如：低风险 / 中风险 / 高风险 / 危急风险）。\n"
            "     - **下一步建议**：提供具体、可操作的临床处置步骤。\n"
            "     - **是否建议联系团队**：明确回答“是”或“否”。\n"
            "     - **参考依据**：必须提供具体的指南 ID（如 QA-M-005）。\n"
            "   - **【红线约束】**：如果对话中未提及明确的“参考依据 ID”，则视为该条知识缺乏权威性，**严禁将其生成或记录到字典中**。\n\n"
            "### 【工作流程约束】\n"
            "- **过滤**：仅提取与‘副作用/并发症’相关的临床知识。剔除一切流程性、交互性或无关的文字。\n"
            "- **原子化更新**：更新应尽可能针对具体的子资源文件（如 `rash.md`），保持 `SKILL.md` 的索引简洁。\n"
            "- **闭环**：所有处理过的记忆（无论是否产生知识更新）都必须调用 `mark_memory_learned`。\n\n"
            "### 【工具链调用规范】\n"
            "- 先用 `read_skill` 和 `resolve_skill_references` 评估现状。\n"
            "- 确定有必要更新时，再用 `upsert_skill_resource` 或 `upsert_skill`。\n"
            "- 最后必须执行 `mark_memory_learned`。"
        )
        
        self.tools = [
            'read_memory_list',
            'read_memory_detail',
            'read_skill',
            'resolve_skill_references',
            'upsert_skill',
            'upsert_skill_resource',
            'mark_memory_learned'
        ]
        
        self.agent = Assistant(
            llm=self.llm_cfg,
            system_message=self.system_prompt,
            function_list=self.tools,
            name=name
        )

    @traceable(name="LearningAgent Run")
    def run(self, force: bool = False) -> str:
        """
        Runs the learning workflow.
        If force is True, it processes unlearned memories regardless of count.
        Otherwise, it checks if the count reaches N=5.
        """
        # First, check unlearned memories
        # We use the agent to do this check via its tools
        prompt = "请检查是否有尚未学习（learned: false）的记忆文档。如果有，请开始学习工作流，提炼知识并更新 Skill 库。处理完后记得标记为已学习。"
        
        if not force:
            # Check count first (optional optimization, but let's just use the agent for simplicity or do a quick check here)
            unlearned_count = self._get_unlearned_count()
            if unlearned_count < 5:
                return f"尚未达到自动学习阈值 (当前未学习: {unlearned_count}/5)。"

        messages = [{'role': 'user', 'content': prompt}]
        
        responses = []
        for chunk in self.agent.run(messages):
            responses.append(chunk)
            
        result_str = "学习任务执行完毕。"
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and len(last_msg) > 0:
                result_str = last_msg[-1]['content']
            elif isinstance(last_msg, dict):
                result_str = last_msg.get('content', '')
                
        # Trigger ReviewerAgent for mandatory audit
        print("Triggering ReviewerAgent for audit...")
        skill_name = "medical_consultation_workflow"
        skill_dir = os.path.join(os.path.abspath("mcp/agents/skills"), skill_name)
        if os.path.exists(skill_dir):
            resources = [f for f in os.listdir(skill_dir) if f.endswith('.md')]
            review_result = self.reviewer.run(skill_name, resources)
            return f"{result_str}\n\n### 【审计报告】\n{review_result}"
            
        return result_str

    def _get_unlearned_count(self) -> int:
        from mcp.agents.tools.memory_tools import ReadMemoryList
        tool = ReadMemoryList()
        result = tool.call({'learned': False})
        if result.get('status') == 'success':
            return len(result.get('memories', []))
        return 0

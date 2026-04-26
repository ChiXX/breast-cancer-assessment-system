import os
import json
from typing import Union
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.agents import Assistant
from langsmith import traceable
from mcp.agents.config import REVIEWER_MODEL, get_llm_cfg

@register_tool('verify_skill_format')
class VerifySkillFormat(BaseTool):
    description = '检查技能资源文件格式。强制要求 JSON 包含：风险等级、下一步建议、是否建议联系团队、参考依据。缺失参考依据的条目将被移除。'
    parameters = {
        'type': 'object',
        'properties': {
            'skill_name': {
                'type': 'string',
                'description': '技能名称'
            },
            'resource_name': {
                'type': 'string',
                'description': '资源文件名（如 fever.json）'
            }
        },
        'required': ['skill_name', 'resource_name']
    }

    def __init__(self, llm_cfg: dict = None):
        super().__init__()
        self.llm_cfg = llm_cfg or get_llm_cfg(REVIEWER_MODEL)

    @traceable(name="Verify Skill Format")
    def call(self, params: Union[str, dict], **kwargs) -> dict:
        if isinstance(params, str):
            params = json.loads(params)
        
        skill_name = params.get('skill_name')
        resource_name = params.get('resource_name')
        
        if not resource_name.endswith('.json'):
            resource_name = resource_name.split('.')[0] + '.json'
            
        skill_dir = os.path.join(os.path.abspath("mcp/agents/skills"), skill_name)
        file_path = os.path.join(skill_dir, resource_name)
        
        if not os.path.exists(file_path):
            return {'status': 'error', 'message': 'File not found'}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 使用 LLM 进行格式审查和清理
        prompt = (
            "你是一个严谨的医疗文档审计员。请检查以下 JSON 内容中的每一项知识条目。\n"
            "要求：每一项必须严格包含以下四个字段：\n"
            "1. **风险等级**\n"
            "2. **下一步建议**\n"
            "3. **是否建议联系团队**\n"
            "4. **参考依据** (必须有具体的 ID，如 QA-xxx)\n\n"
            "【规则】：\n"
            "- 如果某一项缺失任何字段，尤其是缺失‘参考依据’，请直接移除该条目。\n"
            "- 保持其余合格条目的内容原封不动。\n"
            "- 必须返回合法的 JSON 格式内容。\n\n"
            f"待审查内容：\n{content}"
        )
        
        reviewer = Assistant(llm=self.llm_cfg, system_message="你是一个专业的医疗文档审计员。")
        responses = list(reviewer.run([{'role': 'user', 'content': prompt}]))
        if responses:
            raw_res = responses[-1][-1]['content']
            # 提取 JSON 部分
            if '```json' in raw_res:
                raw_res = raw_res.split('```json')[1].split('```')[0].strip()
            elif '```' in raw_res:
                raw_res = raw_res.split('```')[1].split('```')[0].strip()
                
            try:
                # 校验 JSON
                json.loads(raw_res)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(raw_res)
                return {'status': 'success', 'message': 'Format verified and cleaned.'}
            except Exception as e:
                return {'status': 'error', 'message': f'Invalid JSON output from reviewer: {e}'}
        
        return {'status': 'error', 'message': 'Review failed'}

@register_tool('resolve_skill_conflicts')
class ResolveSkillConflicts(BaseTool):
    description = '检查技能库内部是否存在矛盾的判定标准或处置建议，并进行消歧处理。'
    parameters = {
        'type': 'object',
        'properties': {
            'skill_name': {
                'type': 'string',
                'description': '技能名称'
            }
        },
        'required': ['skill_name']
    }

    def __init__(self, llm_cfg: dict = None):
        super().__init__()
        self.llm_cfg = llm_cfg or get_llm_cfg(REVIEWER_MODEL)

    @traceable(name="Resolve Skill Conflicts")
    def call(self, params: Union[str, dict], **kwargs) -> dict:
        if isinstance(params, str):
            params = json.loads(params)
        
        skill_name = params.get('skill_name')
        skill_dir = os.path.join(os.path.abspath("mcp/agents/skills"), skill_name)
        
        if not os.path.exists(skill_dir):
            return {'status': 'error', 'message': 'Skill directory not found'}
            
        all_content = []
        files_map = {}
        for filename in os.listdir(skill_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(skill_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    all_content.append(f"--- 文件: {filename} ---\n{content}")
                    files_map[filename] = content
                    
        full_context = "\n\n".join(all_content)
        
        prompt = (
            "你是一个专业的医疗知识消歧专家。请审查以下技能库（JSON格式）中的所有内容，查找是否存在内部矛盾。\n"
            "【检查重点】：\n"
            "- 相同的症状是否在不同地方被判定为不同的风险等级？\n"
            "- 对于相同的风险等级，处置建议是否存在冲突？\n\n"
            "【处理规则】：\n"
            "1. 发现冲突时，优先保留逻辑更严密、更符合医疗安全的建议（通常是从严原则）。\n"
            "2. 如果冲突涉及多个文件，请输出每个文件修正后的完整内容。\n"
            "3. 输出格式要求：请使用 JSON 格式返回，键为文件名，值为修正后的内容。格式如：{\"filename.json\": \"content...\"}\n"
            "4. 如果没有冲突，返回空 JSON 对象 {}。\n"
            f"待审查内容：\n{full_context}"
        )
        
        reviewer = Assistant(llm=self.llm_cfg, system_message="你是一个专业的医疗知识消歧专家。")
        responses = list(reviewer.run([{'role': 'user', 'content': prompt}]))
        if responses:
            raw_res = responses[-1][-1]['content']
            try:
                # 提取 JSON 部分
                if '```json' in raw_res:
                    raw_res = raw_res.split('```json')[1].split('```')[0].strip()
                elif '```' in raw_res:
                    raw_res = raw_res.split('```')[1].split('```')[0].strip()
                
                updates = json.loads(raw_res)
                for filename, new_content in updates.items():
                    if not filename.endswith('.json'):
                        filename = filename.split('.')[0] + '.json'
                    file_path = os.path.join(skill_dir, filename)
                    # 确保 new_content 是字符串
                    if not isinstance(new_content, str):
                        new_content = json.dumps(new_content, ensure_ascii=False, indent=2)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                return {'status': 'success', 'updates': list(updates.keys())}
            except Exception as e:
                return {'status': 'error', 'message': f'Failed to parse or apply updates: {str(e)}'}
                
        return {'status': 'success', 'message': 'No conflicts found.'}

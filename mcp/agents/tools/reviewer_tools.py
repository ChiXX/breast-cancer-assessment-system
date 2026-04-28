import os
import json
import json5
from typing import Union, List
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import Message, USER, SYSTEM
from langsmith import traceable
from mcp.agents.config import REVIEWER_MODEL, get_llm_cfg

@register_tool('verify_skill_format')
class VerifySkillFormat(BaseTool):
    description = '检查技能资源文件格式。强制要求内容包含：风险等级、下一步建议、是否建议联系团队、参考依据。'
    parameters = {
        'type': 'object',
        'properties': {
            'skill_name': {
                'type': 'string',
                'description': '技能名称'
            },
            'resource_name': {
                'type': 'string',
                'description': '资源文件名（如 fever.md）'
            }
        },
        'required': ['skill_name', 'resource_name']
    }

    def __init__(self, cfg: dict = None):
        super().__init__(cfg)
        self.llm_cfg = (cfg or {}).get('llm_cfg') or get_llm_cfg(REVIEWER_MODEL)
        self.llm = get_chat_model(self.llm_cfg)

    @traceable(name="Verify Skill Format")
    def call(self, params: Union[str, dict], **kwargs) -> dict:
        if isinstance(params, str):
            params = json5.loads(params)
        
        skill_name = params.get('skill_name')
        resource_name = params.get('resource_name')
        
        skill_dir = os.path.join(os.path.abspath("mcp/agents/skills"), skill_name)
        file_path = os.path.join(skill_dir, resource_name)
        
        if not os.path.exists(file_path):
            return {'status': 'error', 'message': f'File not found: {resource_name}'}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        is_md = resource_name.endswith('.md')
        if not is_md:
            return {'status': 'error', 'message': 'Only .md resource files are supported.'}
        
        # 使用 LLM 进行格式审查和清理
        prompt = (
            "你是一个严谨的医疗文档审计员。请检查以下内容中的知识条目（通常在 JSON 块中）。\n"
            "要求：每一项必须严格包含以下四个字段：\n"
            "1. **风险等级**\n"
            "2. **下一步建议**\n"
            "3. **是否建议联系团队**\n"
            "4. **参考依据** (必须有具体的 ID，如 QA-xxx)\n\n"
            "【规则】：\n"
            "- 如果某一项缺失任何字段，尤其是缺失‘参考依据’，请直接移除该条目。\n"
            "- 保持其余合格条目的内容原封不动。\n"
            "- 必须返回完整的文件内容。如果输入是 Markdown，则返回包含修正后 JSON 块的 Markdown；如果输入是纯 JSON，则返回 JSON。\n\n"
            f"待审查内容：\n{content}"
        )
        
        responses = []
        messages = [
            Message(role=SYSTEM, content="你是一个专业的医疗文档审计员。"),
            Message(role=USER, content=prompt)
        ]
        for chunk in self.llm.chat(messages=messages, stream=True):
            responses.append(chunk)
            
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and last_msg:
                last_item = last_msg[-1]
                new_content = last_item.content if hasattr(last_item, 'content') else last_item.get('content', '')
            elif hasattr(last_msg, 'content'):
                new_content = last_msg.content
            else:
                new_content = last_msg.get('content', '')
            
            # Clean up output: if it's wrapped in markdown blocks, extract them
            import re
            md_blocks = re.findall(r'```(?:markdown|json)?\n(.*?)\n```', new_content, re.DOTALL)
            if md_blocks:
                new_content = md_blocks[0]
            
            if 'risk_level' in new_content or 'advice' in new_content:
                if not file_path.endswith('.md'):
                    file_path = file_path.split('.')[0] + '.md'
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return {'status': 'success', 'message': f'Format verified and cleaned for {resource_name}.'}
            else:
                return {'status': 'error', 'message': 'Reviewer output seems corrupted or lacks required fields.'}
        
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

    def __init__(self, cfg: dict = None):
        super().__init__(cfg)
        self.llm_cfg = (cfg or {}).get('llm_cfg') or get_llm_cfg(REVIEWER_MODEL)
        self.llm = get_chat_model(self.llm_cfg)

    @traceable(name="Resolve Skill Conflicts")
    def call(self, params: Union[str, dict], **kwargs) -> dict:
        if isinstance(params, str):
            params = json5.loads(params)
        
        skill_name = params.get('skill_name')
        skill_dir = os.path.join(os.path.abspath("mcp/agents/skills"), skill_name)
        
        if not os.path.exists(skill_dir):
            return {'status': 'error', 'message': 'Skill directory not found'}
            
        all_content = []
        for filename in os.listdir(skill_dir):
            if filename.endswith('.md') and filename != 'SKILL.md':
                file_path = os.path.join(skill_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    all_content.append(f"--- 文件: {filename} ---\n{content}")
                    
        if not all_content:
            return {'status': 'success', 'message': 'No resources to check.'}

        full_context = "\n\n".join(all_content)
        
        prompt = (
            "你是一个专业的医疗知识消歧专家。请审查以下技能库（Markdown 格式）中的所有内容，查找是否存在内部矛盾。\n"
            "【检查重点】：\n"
            "- 相同的症状是否在不同地方被判定为不同的风险等级？\n"
            "- 对于相同的风险等级，处置建议是否存在冲突？\n\n"
            "【处理规则】：\n"
            "1. 发现冲突时，优先保留逻辑更严密、更符合医疗安全的建议（通常是从严原则）。\n"
            "2. 如果冲突涉及多个文件，请输出每个文件修正后的完整内容。\n"
            "3. 输出格式要求：请使用 JSON 格式返回，键为文件名，值为修正后的完整文件内容（字符串）。格式如：{\"filename.md\": \"content...\"}\n"
            "4. 如果没有冲突，返回空 JSON 对象 {}。\n"
            f"待审查内容：\n{full_context}"
        )
        
        responses = []
        messages = [
            Message(role=SYSTEM, content="你是一个专业的医疗知识消歧专家。"),
            Message(role=USER, content=prompt)
        ]
        for chunk in self.llm.chat(messages=messages, stream=True):
            responses.append(chunk)
            
        if responses:
            last_msg = responses[-1]
            if isinstance(last_msg, list) and last_msg:
                last_item = last_msg[-1]
                raw_res = last_item.content if hasattr(last_item, 'content') else last_item.get('content', '')
            elif hasattr(last_msg, 'content'):
                raw_res = last_msg.content
            else:
                raw_res = last_msg.get('content', '')
            try:
                # Robust JSON extraction using regex
                import re
                json_blocks = re.findall(r'```json\n(.*?)\n```', raw_res, re.DOTALL)
                if not json_blocks:
                    json_blocks = re.findall(r'(\{.*\})', raw_res, re.DOTALL)
                
                if not json_blocks:
                    return {'status': 'success', 'message': 'No conflicts found or no updates suggested.'}
                
                updates = json5.loads(json_blocks[0])
                for filename, new_content in updates.items():
                    # 强制使用 .md 扩展名
                    filename_base = filename.split('.')[0]
                    target_filename = filename_base + '.md'
                    file_path = os.path.join(skill_dir, target_filename)
                    # 确保 new_content 是字符串
                    if not isinstance(new_content, str):
                        new_content = json.dumps(new_content, ensure_ascii=False, indent=2)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                return {'status': 'success', 'updates': list(updates.keys())}
            except Exception as e:
                return {'status': 'error', 'message': f'Failed to parse or apply updates: {str(e)}'}
                
        return {'status': 'success', 'message': 'No conflicts found.'}


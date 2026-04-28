import os
import re
import json
import json5
from typing import Union, List
from qwen_agent.tools.base import BaseTool, register_tool
from qwen_agent.llm import get_chat_model
from qwen_agent.llm.schema import Message, USER, SYSTEM
from langsmith import traceable
from mcp.agents.config import REVIEWER_MODEL, get_llm_cfg

# 必须使用英文字段名的四个必填项
REQUIRED_RESOURCE_FIELDS = {'risk_level', 'action_required', 'matched_rule_id', 'contact_team'}


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

        if not resource_name.endswith('.md'):
            return {'status': 'error', 'message': 'Only .md resource files are supported.'}

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 纯静态校验：从 ```json 代码块提取字段，不调用 LLM，不修改文件
        json_blocks = re.findall(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
        if not json_blocks:
            return {'status': 'error', 'message': f'{resource_name}: 缺少 ```json 代码块'}
        try:
            data = json.loads(json_blocks[0])
        except json.JSONDecodeError as e:
            return {'status': 'error', 'message': f'{resource_name}: JSON 解析失败: {e}'}

        REQUIRED_FIELDS = {'risk_level', 'action_required', 'matched_rule_id', 'contact_team'}
        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            return {'status': 'error', 'message': f'{resource_name}: 缺少必填字段: {missing}'}

        return {'status': 'success', 'message': f'{resource_name}: 格式校验通过。'}


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
        for filename in sorted(os.listdir(skill_dir)):
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
            "3. 【重要】输出格式：请使用 JSON 对象返回，键为文件名，值为修正后的完整 Markdown 字符串。\n"
            "   Markdown 内容必须包含：标题行、描述段落、以及一个 ```json 代码块。\n"
            "   代码块内 JSON 必须含以下英文字段：risk_level / action_required / matched_rule_id / contact_team。\n"
            "   示例：{\"filename.md\": \"# 标题\\n\\n描述...\\n\\n```json\\n{\\\"risk_level\\\": \\\"HIGH\\\", ...}\\n```\"}\n"
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

        if not responses:
            return {'status': 'success', 'message': 'No conflicts found.'}

        last_msg = responses[-1]
        if isinstance(last_msg, list) and last_msg:
            last_item = last_msg[-1]
            raw_res = last_item.content if hasattr(last_item, 'content') else last_item.get('content', '')
        elif hasattr(last_msg, 'content'):
            raw_res = last_msg.content
        else:
            raw_res = last_msg.get('content', '')

        try:
            # 优先提取 ```json 块，其次尝试裸 JSON 对象
            json_blocks = re.findall(r'```json\s*\n(.*?)\n```', raw_res, re.DOTALL)
            if not json_blocks:
                json_blocks = re.findall(r'(\{.*\})', raw_res, re.DOTALL)

            if not json_blocks:
                return {'status': 'success', 'message': 'No conflicts found or no updates suggested.'}

            updates = json5.loads(json_blocks[0])
            if not updates:
                return {'status': 'success', 'message': 'No conflicts found.'}

            from mcp.agents.tools.skill_tools import REQUIRED_RESOURCE_FIELDS
            updated_files = []
            skipped_files = []

            for filename, new_content in updates.items():
                filename_base = filename.split('.')[0]
                target_filename = filename_base + '.md'
                file_path = os.path.join(skill_dir, target_filename)

                # 确保 new_content 是字符串
                if not isinstance(new_content, str):
                    new_content = json.dumps(new_content, ensure_ascii=False, indent=2)

                # 写入前校验：必须有 ```json 块且含必填字段
                blocks = re.findall(r'```json\s*\n(.*?)\n```', new_content, re.DOTALL)
                valid = False
                if blocks:
                    try:
                        d = json.loads(blocks[0])
                        if not (REQUIRED_RESOURCE_FIELDS - set(d.keys())):
                            valid = True
                    except Exception:
                        pass
                if not valid:
                    skipped_files.append(target_filename)
                    continue

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                updated_files.append(target_filename)

            result = {'status': 'success', 'updates': updated_files}
            if skipped_files:
                result['skipped'] = skipped_files
            return result

        except Exception as e:
            return {'status': 'error', 'message': f'Failed to parse or apply updates: {str(e)}'}

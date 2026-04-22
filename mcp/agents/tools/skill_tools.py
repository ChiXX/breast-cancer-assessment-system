import os
from qwen_agent.tools.base import BaseTool, register_tool

@register_tool('discover_skills')
class DiscoverSkills(BaseTool):
    description = '在 skills/ 目录下通过读取 SKILL.md 的元数据来搜索匹配意图的技能'
    parameters = {
        'type': 'object',
        'properties': {
            'query': {
                'type': 'string',
                'description': '意图关键词或症状描述'
            }
        },
        'required': ['query']
    }

    def call(self, params: str, **kwargs):
        # 注意：这里路径需要向上跳一级到 mcp/skills
        skills_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'skills')
        matched_skills = []
        
        if not os.path.exists(skills_root):
            return {'status': 'error', 'message': f'Skills directory {skills_root} not found'}

        for skill_dir in os.listdir(skills_root):
            skill_path = os.path.join(skills_root, skill_dir)
            if os.path.isdir(skill_path):
                skill_md_path = os.path.join(skill_path, 'SKILL.md')
                if os.path.exists(skill_md_path):
                    with open(skill_md_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if params.get('query', '').lower() in content.lower():
                            matched_skills.append({
                                'name': skill_dir,
                                'path': skill_md_path
                            })
        
        return {
            'status': 'success',
            'skills': matched_skills,
            'message': f'Found {len(matched_skills)} skills matching query.'
        }

@register_tool('load_skill')
class LoadSkill(BaseTool):
    description = '加载指定技能的 SKILL.md 完整指令内容'
    parameters = {
        'type': 'object',
        'properties': {
            'skill_name': {
                'type': 'string',
                'description': '技能文件夹名称 (如 hand-foot-syndrome)'
            }
        },
        'required': ['skill_name']
    }

    def call(self, params: str, **kwargs):
        skill_name = params.get('skill_name', '')
        skills_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'skills')
        skill_md_path = os.path.join(skills_root, skill_name, 'SKILL.md')
        
        if os.path.exists(skill_md_path):
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {'status': 'success', 'content': content}
        else:
            return {'status': 'error', 'message': f'Skill {skill_name} not found'}

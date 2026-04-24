import os
import yaml
import json
from typing import Union
from qwen_agent.tools.base import BaseTool, register_tool
from langsmith import traceable

def get_skill_paths():
    """获取技能搜索路径：项目路径和个人路径"""
    paths = []
    # 项目路径: mcp/agents/skills
    project_skills = os.path.abspath("mcp/agents/skills")
    if os.path.exists(project_skills):
        paths.append(project_skills)
    
    # 个人路径: ~/.qwen/skills
    personal_skills = os.path.expanduser("~/.qwen/skills")
    if os.path.exists(personal_skills):
        paths.append(personal_skills)
        
    return paths

def parse_skill_md(file_path):
    """解析 SKILL.md 文件，提取 YAML frontmatter 和内容"""
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1])
                body = parts[2].strip()
                return {
                    'metadata': metadata,
                    'content': body
                }
            except Exception:
                pass
    return {
        'metadata': {},
        'content': content
    }

def get_all_skill_metadata():
    """获取所有技能的元数据（YAML 头）"""
    metadata_list = []
    skill_roots = get_skill_paths()
    
    for root in skill_roots:
        if not os.path.isdir(root):
            continue
        for skill_dir in os.listdir(root):
            skill_path = os.path.join(root, skill_dir)
            if os.path.isdir(skill_path):
                skill_md_path = os.path.join(skill_path, 'SKILL.md')
                parsed = parse_skill_md(skill_md_path)
                if parsed:
                    metadata = parsed['metadata']
                    # 确保包含名称
                    if 'name' not in metadata:
                        metadata['name'] = skill_dir
                    metadata_list.append(metadata)
    return metadata_list

@register_tool('read_skill')
class ReadSkill(BaseTool):
    description = '查阅指定技能的完整执行手册（SKILL.md 内容）。当系统提示词中的元数据表明某个技能可能适用时使用。'
    parameters = {
        'type': 'object',
        'properties': {
            'skill_name': {
                'type': 'string',
                'description': '技能名称 (元数据中的 name)'
            }
        },
        'required': ['skill_name']
    }

    @traceable(name="Read Skill Tool Call")
    def call(self, params: Union[str, dict], **kwargs):
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                skill_name = params
            else:
                skill_name = params.get('skill_name', '')
        else:
            skill_name = params.get('skill_name', '')
            
        skill_roots = get_skill_paths()
        
        for root in skill_roots:
            for skill_dir in os.listdir(root):
                skill_path = os.path.join(root, skill_dir)
                if os.path.isdir(skill_path):
                    skill_md_path = os.path.join(skill_path, 'SKILL.md')
                    parsed = parse_skill_md(skill_md_path)
                    if parsed:
                        if parsed['metadata'].get('name') == skill_name or skill_dir == skill_name:
                            return {
                                'status': 'success', 
                                'name': skill_name,
                                'metadata': parsed['metadata'],
                                'content': parsed['content']
                            }
                            
        return {'status': 'error', 'message': f'Skill {skill_name} not found'}

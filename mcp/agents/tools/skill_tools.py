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
            if not os.path.exists(root):
                continue
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
        
        # 2. 增强逻辑：如果没找到顶级技能，尝试在所有技能目录中查找匹配的资源文件
        # 支持按资源文件名（如 neuropathy.md）或去后缀的文件名（如 neuropathy）查找
        resource_name = skill_name
        if not resource_name.endswith('.md'):
            resource_name += '.md'
            
        for root in skill_roots:
            if not os.path.exists(root):
                continue
            for skill_dir in os.listdir(root):
                skill_path = os.path.join(root, skill_dir)
                if not os.path.isdir(skill_path):
                    continue
                
                # 直接尝试在技能目录下找该文件
                target_file = os.path.join(skill_path, resource_name)
                if os.path.exists(target_file):
                    with open(target_file, 'r', encoding='utf-8') as f:
                        return {
                            'status': 'success',
                            'name': skill_name,
                            'parent_skill': skill_dir,
                            'content': f.read()
                        }
                        
                # 进阶尝试：解析 SKILL.md 中的表格，查找显示名称匹配的路径
                skill_md_path = os.path.join(skill_path, 'SKILL.md')
                if os.path.exists(skill_md_path):
                    with open(skill_md_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    for line in lines:
                        if '|' in line and skill_name in line:
                            import re
                            # 尝试提取链接 [名称](./路径)
                            match = re.search(r'\[(.*?)\]\(\./(.*?)\)', line)
                            if match and (match.group(1) == skill_name or match.group(2) == skill_name or match.group(2) == resource_name):
                                real_path = os.path.join(skill_path, match.group(2))
                                if os.path.exists(real_path):
                                    with open(real_path, 'r', encoding='utf-8') as f:
                                        return {
                                            'status': 'success',
                                            'name': skill_name,
                                            'resolved_path': match.group(2),
                                            'content': f.read()
                                        }
                            
        return {'status': 'error', 'message': f'Skill or Resource "{skill_name}" not found'}

@register_tool('upsert_skill')
class UpsertSkill(BaseTool):
    description = '更新或创建一个技能执行手册（SKILL.md）。用于将学习到的新知识持久化。'
    parameters = {
        'type': 'object',
        'properties': {
            'skill_name': {
                'type': 'string',
                'description': '技能名称'
            },
            'description': {
                'type': 'string',
                'description': '技能描述'
            },
            'content': {
                'type': 'string',
                'description': '手册正文内容（Markdown格式）'
            }
        },
        'required': ['skill_name', 'description', 'content']
    }

    @traceable(name="Upsert Skill Tool Call")
    def call(self, params: Union[str, dict], **kwargs):
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                return {'status': 'error', 'message': 'Invalid params'}
        
        skill_name = params.get('skill_name', '')
        description = params.get('description', '')
        content = params.get('content', '')
        
        if not skill_name:
            return {'status': 'error', 'message': 'skill_name is required'}
            
        skill_dir = os.path.join(os.path.abspath("mcp/agents/skills"), skill_name)
        os.makedirs(skill_dir, exist_ok=True)
        
        skill_md_path = os.path.join(skill_dir, 'SKILL.md')
        
        import datetime
        metadata = {
            'name': skill_name,
            'description': description,
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        full_content = f"---\n{yaml.dump(metadata, allow_unicode=True)}---\n\n{content}"
        
        with open(skill_md_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
            
        return {'status': 'success', 'path': skill_md_path}

@register_tool('upsert_skill_resource')
class UpsertSkillResource(BaseTool):
    description = '在技能目录下创建或更新子资源文件（如 fever.md）。用于多级渐进式披露。'
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
            },
            'content': {
                'type': 'string',
                'description': '资源文件内容'
            }
        },
        'required': ['skill_name', 'resource_name', 'content']
    }

    @traceable(name="Upsert Skill Resource Tool Call")
    def call(self, params: Union[str, dict], **kwargs):
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                return {'status': 'error', 'message': 'Invalid params'}
        
        skill_name = params.get('skill_name', '')
        resource_name = params.get('resource_name', '')
        content = params.get('content', '')
        
        if not skill_name or not resource_name:
            return {'status': 'error', 'message': 'skill_name and resource_name are required'}
            
        # 统一资源名格式
        if resource_name.startswith('./'):
            resource_name = resource_name[2:]
            
        skill_dir = os.path.join(os.path.abspath("mcp/agents/skills"), skill_name)
        os.makedirs(skill_dir, exist_ok=True)
        
        resource_path = os.path.join(skill_dir, resource_name)
        
        with open(resource_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return {'status': 'success', 'path': resource_path}

@register_tool('resolve_skill_references')
class ResolveSkillReferences(BaseTool):
    description = '解析并读取技能文档（SKILL.md）中引用的外部资源文件内容。例如 [发热](./fever.md) 中的 fever.md。'
    parameters = {
        'type': 'object',
        'properties': {
            'skill_name': {
                'type': 'string',
                'description': '技能名称'
            },
            'resource_path': {
                'type': 'string',
                'description': '引用的资源路径，如 "./fever.md"'
            }
        },
        'required': ['skill_name', 'resource_path']
    }

    @traceable(name="Resolve Skill References Tool Call")
    def call(self, params: Union[str, dict], **kwargs):
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                return {'status': 'error', 'message': 'Invalid params'}
        
        skill_name = params.get('skill_name', '')
        resource_path = params.get('resource_path', '')
        
        if resource_path.startswith('./'):
            resource_name = resource_path[2:]
        else:
            resource_name = resource_path
            
        skill_roots = get_skill_paths()
        
        for root in skill_roots:
            skill_dir = os.path.join(root, skill_name)
            target_file = os.path.join(skill_dir, resource_name)
            if os.path.exists(target_file):
                with open(target_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {'status': 'success', 'content': content}
                            
        return {'status': 'error', 'message': f'Resource {resource_name} not found in skill {skill_name}'}

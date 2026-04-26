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

def parse_skill_json(file_path):
    """解析 SKILL.json 文件"""
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            return data
        except Exception:
            return None

def get_all_skill_metadata():
    """获取所有技能的元数据"""
    metadata_list = []
    skill_roots = get_skill_paths()
    
    for root in skill_roots:
        if not os.path.isdir(root):
            continue
        for skill_dir in os.listdir(root):
            skill_path = os.path.join(root, skill_dir)
            if os.path.isdir(skill_path):
                skill_json_path = os.path.join(skill_path, 'SKILL.json')
                parsed = parse_skill_json(skill_json_path)
                if parsed:
                    metadata = parsed.get('metadata', {})
                    # 确保包含名称
                    if 'name' not in metadata:
                        metadata['name'] = skill_dir
                    metadata_list.append(metadata)
    return metadata_list

@register_tool('read_skill')
class ReadSkill(BaseTool):
    description = '查阅指定技能的完整执行手册（SKILL.json 内容）。当系统提示词中的元数据表明某个技能可能适用时使用。'
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
                    skill_json_path = os.path.join(skill_path, 'SKILL.json')
                    parsed = parse_skill_json(skill_json_path)
                    if parsed:
                        if parsed.get('metadata', {}).get('name') == skill_name or skill_dir == skill_name:
                            return {
                                'status': 'success', 
                                'name': skill_name,
                                'metadata': parsed.get('metadata', {}),
                                'content': parsed.get('content', '')
                            }
        
        # 2. 增强逻辑：如果没找到顶级技能，尝试在所有技能目录中查找匹配的资源文件
        resource_name = skill_name
        if not resource_name.endswith('.json'):
            resource_name += '.json'
            
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
                            
        return {'status': 'error', 'message': f'Skill or Resource "{skill_name}" not found'}

@register_tool('upsert_skill')
class UpsertSkill(BaseTool):
    description = '更新或创建一个技能执行手册（SKILL.json）。用于将学习到的新知识持久化。'
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
                'description': '手册正文内容（JSON 格式字符串）'
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
        
        skill_json_path = os.path.join(skill_dir, 'SKILL.json')
        
        import datetime
        data = {
            'metadata': {
                'name': skill_name,
                'description': description,
                'updated_at': datetime.datetime.now().isoformat()
            },
            'content': content
        }
        
        with open(skill_json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return {'status': 'success', 'path': skill_json_path}

@register_tool('upsert_skill_resource')
class UpsertSkillResource(BaseTool):
    description = '在技能目录下创建或更新子资源文件（如 fever.json）。用于多级渐进式披露。'
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
            },
            'content': {
                'type': 'string',
                'description': '资源文件内容（JSON 格式字符串）'
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
        if not resource_name.endswith('.json'):
            resource_name = resource_name.split('.')[0] + '.json'
            
        skill_dir = os.path.join(os.path.abspath("mcp/agents/skills"), skill_name)
        os.makedirs(skill_dir, exist_ok=True)
        
        resource_path = os.path.join(skill_dir, resource_name)
        
        with open(resource_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return {'status': 'success', 'path': resource_path}

@register_tool('resolve_skill_references')
class ResolveSkillReferences(BaseTool):
    description = '解析并读取技能文档（SKILL.json）中引用的外部资源文件内容。'
    parameters = {
        'type': 'object',
        'properties': {
            'skill_name': {
                'type': 'string',
                'description': '技能名称'
            },
            'resource_path': {
                'type': 'string',
                'description': '引用的资源路径，如 "./fever.json"'
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
            
        if not resource_name.endswith('.json'):
            resource_name = resource_name.split('.')[0] + '.json'
            
        skill_roots = get_skill_paths()
        
        for root in skill_roots:
            skill_dir = os.path.join(root, skill_name)
            target_file = os.path.join(skill_dir, resource_name)
            if os.path.exists(target_file):
                with open(target_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {'status': 'success', 'content': content}
                            
        return {'status': 'error', 'message': f'Resource {resource_name} not found in skill {skill_name}'}

import os
import re
import yaml
import json
from typing import Union
from qwen_agent.tools.base import BaseTool, register_tool
from langsmith import traceable

REQUIRED_RESOURCE_FIELDS = {'risk_level', 'action_required', 'matched_rule_id', 'contact_team'}
MEMORY_DIR = os.path.abspath("mcp/agents/memory")

def get_skill_paths():
    """获取技能搜索路径：项目路径和个人路径"""
    paths = []
    project_skills = os.path.abspath("mcp/agents/skills")
    if os.path.exists(project_skills):
        paths.append(project_skills)
        
    return paths

def parse_skill_md(file_path):
    """解析 SKILL.md 文件中的 YAML frontmatter 和内容"""
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    content = content.strip()
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                metadata = yaml.safe_load(parts[1])
                return {
                    'metadata': metadata,
                    'content': parts[2].strip()
                }
            except Exception:
                return None
    return None

def get_all_skill_metadata():
    """获取所有技能的元数据 (从 SKILL.md 提取)"""
    metadata_list = []
    skill_roots = get_skill_paths()
    
    for root in skill_roots:
        if not os.path.isdir(root):
            continue
        for skill_dir in os.listdir(root):
            skill_path = os.path.join(root, skill_dir)
            if os.path.isdir(skill_path):
                # 优先查阅 SKILL.md
                skill_md_path = os.path.join(skill_path, 'SKILL.md')
                parsed = parse_skill_md(skill_md_path)
                if parsed:
                    metadata = parsed.get('metadata', {})
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
        from mcp.utils.event_logger import eventlog
        for root in skill_roots:
            if not os.path.exists(root):
                continue
            for skill_dir in os.listdir(root):
                skill_path = os.path.join(root, skill_dir)
                if os.path.isdir(skill_path):
                    # 1. 尝试 SKILL.md
                    skill_md_path = os.path.join(skill_path, 'SKILL.md')
                    parsed = parse_skill_md(skill_md_path)
                    if parsed:
                        if parsed.get('metadata', {}).get('name') == skill_name or skill_dir == skill_name:
                            eventlog("SKILL_READ", f"Reading skill: {skill_name}", {"skill_name": skill_name, "path": skill_md_path})
                            return {
                                'status': 'success', 
                                'name': skill_name,
                                'metadata': parsed.get('metadata', {}),
                                'content': parsed.get('content', '')
                            }
        
        # 3. 增强逻辑：如果没找到顶级技能，尝试在所有技能目录中查找匹配的资源文件 (.md)
        resource_name = skill_name
        possible_names = [resource_name]
        if not resource_name.endswith('.md'):
            possible_names.append(resource_name + '.md')
            
        for root in skill_roots:
            if not os.path.exists(root):
                continue
            for skill_dir in os.listdir(root):
                skill_path = os.path.join(root, skill_dir)
                if not os.path.isdir(skill_path):
                    continue
                
                for name in possible_names:
                    target_file = os.path.join(skill_path, name)
                    if os.path.exists(target_file):
                        with open(target_file, 'r', encoding='utf-8') as f:
                            eventlog("SKILL_READ", f"Reading skill resource: {skill_name}", {"skill_name": skill_name, "parent_skill": skill_dir, "path": target_file})
                            return {
                                'status': 'success',
                                'name': skill_name,
                                'parent_skill': skill_dir,
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
                'description': '技能名称 (必须仅包含小写字母、数字和连字符，严禁使用下划线)'
            },
            'description': {
                'type': 'string',
                'description': '技能描述'
            },
            'content': {
                'type': 'string',
                'description': '手册正文内容（Markdown 格式）'
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
        
        # Strip existing yaml header from content if present to avoid double headers
        clean_content = content.strip()
        if clean_content.startswith('---'):
            parts = clean_content.split('---', 2)
            if len(parts) >= 3:
                clean_content = parts[2].strip()
        
        md_content = f"---\n{yaml.dump(metadata, allow_unicode=True)}---\n\n{clean_content}"
        
        with open(skill_md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
            
        return {'status': 'success', 'path': skill_md_path}

@register_tool('upsert_skill_resource')
class UpsertSkillResource(BaseTool):
    description = (
        '在技能目录下创建或更新子资源文件（如 fever.md）。'
        '工具直接从指定的记忆文件读取完整 assessment 并生成 Markdown，'
        '你只需提供记忆的 session_id 和 timestamp 标识符。'
    )
    parameters = {
        'type': 'object',
        'properties': {
            'skill_name': {
                'type': 'string',
                'description': '技能名称（固定为 chemotherapy-side-effect-triage）'
            },
            'resource_name': {
                'type': 'string',
                'description': '资源文件名（如 oral-mucositis.md）'
            },
            'title': {
                'type': 'string',
                'description': '症状模块标题，如 "口腔黏膜炎（化疗后）"'
            },
            'session_id': {
                'type': 'string',
                'description': '记忆文件所属的 session_id，如 session_7whj6uk5ycu'
            },
            'timestamp': {
                'type': 'string',
                'description': '记忆文件的时间戳，如 2026-04-28_14-14-15'
            }
        },
        'required': ['skill_name', 'resource_name', 'title', 'session_id', 'timestamp']
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
        title = params.get('title', '')
        session_id = params.get('session_id', '')
        timestamp = params.get('timestamp', '')

        if not all([skill_name, resource_name, session_id, timestamp]):
            return {'status': 'error', 'message': 'skill_name, resource_name, session_id, timestamp are required'}

        # 直接从记忆文件读取完整 assessment，不经过 LLM
        memory_path = os.path.join(MEMORY_DIR, session_id, f"{timestamp}.json")
        if not os.path.exists(memory_path):
            return {'status': 'error', 'message': f'Memory file not found: {memory_path}'}

        with open(memory_path, 'r', encoding='utf-8') as f:
            memory_data = json.load(f)

        assessment = memory_data.get('assessment')
        if not assessment or not isinstance(assessment, dict):
            return {'status': 'error', 'message': 'No assessment found in memory file'}

        # 校验必填字段
        missing = REQUIRED_RESOURCE_FIELDS - set(assessment.keys())
        if missing:
            return {'status': 'error', 'message': f'Memory assessment 缺少必填字段: {missing}'}

        # 工具自己构建标准 Markdown
        assessment_json = json.dumps(assessment, ensure_ascii=False, indent=2)
        content = (
            f"# {title or resource_name}\n\n"
            f"## 评估逻辑\n\n"
            f"```json\n{assessment_json}\n```\n"
        )

        resource_base = resource_name.split('.')[0]
        resource_name = resource_base + '.md'

        skill_dir = os.path.join(os.path.abspath("mcp/agents/skills"), skill_name)
        os.makedirs(skill_dir, exist_ok=True)

        resource_path = os.path.join(skill_dir, resource_name)
        with open(resource_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {'status': 'success', 'path': resource_path}

@register_tool('resolve_skill_references')
class ResolveSkillReferences(BaseTool):
    description = '解析并读取技能文档（SKILL.md）中引用的外部资源文件内容。'
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
            
            # 兼容性处理：如果没带扩展名，尝试 .md
            if '.' not in resource_name:
                target_file = os.path.join(skill_dir, resource_name + '.md')
                if os.path.exists(target_file):
                    with open(target_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return {'status': 'success', 'content': content}
                            
        return {'status': 'error', 'message': f'Resource {resource_name} not found in skill {skill_name}'}


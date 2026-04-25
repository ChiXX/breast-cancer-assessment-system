import os
import json
import time
import datetime
import yaml
from typing import Union, List, Optional
from qwen_agent.tools.base import BaseTool, register_tool
from langsmith import traceable

MEMORY_DIR = os.path.abspath("mcp/agents/memory")

def ensure_memory_dir(session_id: str):
    path = os.path.join(MEMORY_DIR, session_id)
    os.makedirs(path, exist_ok=True)
    return path

@register_tool('read_memory_list')
class ReadMemoryList(BaseTool):
    description = '获取所有历史记忆线索，返回包含会话ID、时间戳和精简标题的列表。'
    parameters = {
        'type': 'object',
        'properties': {
            'learned': {
                'type': 'boolean',
                'description': '是否只获取已学习(true)或未学习(false)的记忆。不传则获取全部。'
            }
        },
        'required': []
    }

    @traceable(name="Read Memory List")
    def call(self, params: Union[str, dict], **kwargs):
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                params = {}
        
        filter_learned = params.get('learned')
        
        if not os.path.exists(MEMORY_DIR):
            return {'status': 'success', 'memories': []}
            
        memories = []
        for session_dir_name in sorted(os.listdir(MEMORY_DIR)):
            session_dir = os.path.join(MEMORY_DIR, session_dir_name)
            if not os.path.isdir(session_dir):
                continue
                
            for filename in sorted(os.listdir(session_dir)):
                if filename.endswith('.md'):
                    file_path = os.path.join(session_dir, filename)
                    timestamp = filename.replace('.md', '')
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 解析 Frontmatter
                    learned = False
                    body = content
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            try:
                                metadata = yaml.safe_load(parts[1])
                                learned = metadata.get('learned', False)
                                body = parts[2].strip()
                            except Exception:
                                pass
                    
                    if filter_learned is not None and learned != filter_learned:
                        continue
                        
                    first_line = body.split('\n')[0].strip()
                    title = first_line.lstrip('#').strip() if first_line.startswith('#') else 'No Title'
                    
                    memories.append({
                        'session_id': session_dir_name,
                        'timestamp': timestamp, 
                        'title': title,
                        'learned': learned
                    })
        
        return {'status': 'success', 'memories': memories}

@register_tool('read_memory_detail')
class ReadMemoryDetail(BaseTool):
    description = '按需渐进式加载历史记忆的详细内容。'
    parameters = {
        'type': 'object',
        'properties': {
            'session_id': {
                'type': 'string',
                'description': '会话ID'
            },
            'timestamp': {
                'type': 'string',
                'description': '记忆文档的时间戳(文件名，不包含.md)'
            }
        },
        'required': ['session_id', 'timestamp']
    }

    @traceable(name="Read Memory Detail")
    def call(self, params: Union[str, dict], **kwargs):
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                return {'status': 'error', 'message': 'Invalid params'}
        
        session_id = params.get('session_id', '')
        timestamp = params.get('timestamp', '')
        
        file_path = os.path.join(MEMORY_DIR, session_id, f"{timestamp}.md")
        if not os.path.exists(file_path):
            return {'status': 'error', 'message': 'Memory not found'}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return {'status': 'success', 'content': content}

@register_tool('create_memory')
class CreateMemory(BaseTool):
    description = '创建一条新的记忆文档。需要提供精简标题、核心一句话总结和完整对话记录。'
    parameters = {
        'type': 'object',
        'properties': {
            'session_id': {
                'type': 'string',
                'description': '会话ID'
            },
            'title': {
                'type': 'string',
                'description': '精简标题，几十个字'
            },
            'summary': {
                'type': 'string',
                'description': '一句话极简总结，用于描述核心结论或状态变化，几百字'
            },
            'full_conversation': {
                'type': 'string',
                'description': '全文对话记录'
            }
        },
        'required': ['session_id', 'title', 'summary', 'full_conversation']
    }

    @traceable(name="Create Memory")
    def call(self, params: Union[str, dict], **kwargs):
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                return {'status': 'error', 'message': 'Invalid params'}
                
        session_id = params.get('session_id', '')
        title = params.get('title', '')
        summary = params.get('summary', '')
        full_conversation = params.get('full_conversation', '')
        
        if not session_id:
            return {'status': 'error', 'message': 'session_id is required'}
            
        session_dir = ensure_memory_dir(session_id)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = os.path.join(session_dir, f"{timestamp}.md")
        
        # 使用 YAML Frontmatter 标记 learned 状态
        frontmatter = {
            'learned': False,
            'created_at': datetime.datetime.now().isoformat()
        }
        
        content = f"---\n{yaml.dump(frontmatter)}---\n\n# {title}\n{summary}\n\n---\n{full_conversation}"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return {'status': 'success', 'timestamp': timestamp, 'path': file_path}


@register_tool('summarize_memory')
class SummarizeMemoryTool(BaseTool):
    description = '总结记忆的工具。当记忆较多时，用于整合和归纳所有的历史记忆文档。'
    parameters = {
        'type': 'object',
        'properties': {},
        'required': []
    }
    
    @traceable(name="Summarize Memory Tool")
    def call(self, params: Union[str, dict], **kwargs):
        if not os.path.exists(MEMORY_DIR):
            return {'status': 'success', 'summary': '无历史记忆'}
            
        memories = []
        # 遍历 MEMORY_DIR 下的所有会话目录
        for session_dir_name in sorted(os.listdir(MEMORY_DIR)):
            session_dir = os.path.join(MEMORY_DIR, session_dir_name)
            if not os.path.isdir(session_dir):
                continue
                
            for filename in sorted(os.listdir(session_dir)):
                if filename.endswith('.md'):
                    file_path = os.path.join(session_dir, filename)
                    timestamp = filename.replace('.md', '')
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # 解析 Frontmatter 去掉标题前的 YAML
                    body = content
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            body = parts[2].strip()
                            
                    parts = body.split('---', 1)
                    header = parts[0].strip()
                    memories.append(f"[会话: {session_dir_name} | 时间: {timestamp}]\n{header}")
                    
        if not memories:
            return {'status': 'success', 'content': '无历史记忆'}
            
        all_summary = "\n\n".join(memories)
        return {'status': 'success', 'content': all_summary}

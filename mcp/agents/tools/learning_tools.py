import os
import yaml
import json
from typing import Union
from qwen_agent.tools.base import BaseTool, register_tool
from langsmith import traceable

MEMORY_DIR = os.path.abspath("mcp/agents/memory")

@register_tool('mark_memory_learned')
class MarkMemoryLearned(BaseTool):
    description = '将指定的记忆文档标记为已学习（learned: true）。'
    parameters = {
        'type': 'object',
        'properties': {
            'session_id': {
                'type': 'string',
                'description': '会话ID'
            },
            'timestamp': {
                'type': 'string',
                'description': '记忆文档的时间戳'
            }
        },
        'required': ['session_id', 'timestamp']
    }

    @traceable(name="Mark Memory Learned")
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
            
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1])
                    metadata['learned'] = True
                    new_content = f"---\n{yaml.dump(metadata, allow_unicode=True)}---\n{parts[2]}"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    return {'status': 'success'}
                except Exception as e:
                    return {'status': 'error', 'message': str(e)}
        
        # 如果没有 frontmatter，添加一个
        metadata = {'learned': True}
        new_content = f"---\n{yaml.dump(metadata, allow_unicode=True)}---\n\n{content}"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return {'status': 'success'}

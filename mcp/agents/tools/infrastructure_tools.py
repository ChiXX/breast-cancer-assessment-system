from qwen_agent.tools.base import BaseTool, register_tool

@register_tool('search_patient_memory')
class SearchPatientMemory(BaseTool):
    description = '搜索患者历史记忆'
    parameters = {
        'type': 'object',
        'properties': {
            'query': { 'type': 'string' }
        },
        'required': ['query']
    }

    def call(self, params: str, **kwargs):
        return {'status': 'success', 'result': 'Mock memory data'}

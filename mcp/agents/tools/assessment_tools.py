from qwen_agent.tools.base import BaseTool, register_tool

@register_tool('extract_symptoms')
class ExtractSymptoms(BaseTool):
    description = '提取症状实体'
    parameters = {
        'type': 'object',
        'properties': {
            'text': { 'type': 'string' }
        },
        'required': ['text']
    }

    def call(self, params: str, **kwargs):
        return {'status': 'success', 'symptoms': []}

@register_tool('submit_assessment_result')
class SubmitAssessmentResult(BaseTool):
    description = '提交评估结果'
    parameters = {
        'type': 'object',
        'properties': {
            'result': { 'type': 'object' }
        },
        'required': ['result']
    }

    def call(self, params: str, **kwargs):
        return {'status': 'submitted'}

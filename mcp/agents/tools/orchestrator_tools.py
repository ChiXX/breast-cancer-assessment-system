from qwen_agent.tools.base import BaseTool, register_tool

@register_tool('delegate_assessment_task')
class DelegateAssessmentTask(BaseTool):
    description = '派发任务给评估子代理'
    parameters = {
        'type': 'object',
        'properties': {
            'patient_input': { 'type': 'string' },
            'skill_context': { 'type': 'string', 'description': 'Optional skill instructions to pass' }
        },
        'required': ['patient_input']
    }

    def call(self, params: str, **kwargs):
        return {'status': 'delegated', 'message': 'Task passed to AssessmentAgent'}

@register_tool('update_agent_context')
class UpdateAgentContext(BaseTool):
    description = '更新运行中子代理的上下文'
    parameters = {
        'type': 'object',
        'properties': {
            'additional_info': { 'type': 'string' }
        },
        'required': ['additional_info']
    }

    def call(self, params: str, **kwargs):
        return {'status': 'success', 'message': 'Context updated'}

@register_tool('terminate_task')
class TerminateTask(BaseTool):
    description = '终结当前任务'
    parameters = {
        'type': 'object',
        'properties': {
            'reason': { 'type': 'string' }
        },
        'required': ['reason']
    }

    def call(self, params: str, **kwargs):
        return {'status': 'terminated', 'message': 'Task finished'}

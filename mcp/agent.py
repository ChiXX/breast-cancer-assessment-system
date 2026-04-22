import os
import asyncio
from dotenv import load_dotenv
import sys

# Ensure mcp modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.agents.orchestrator import OrchestratorAgent
from mcp.agents.assessment_agent import AssessmentAgent

load_dotenv()

class Orchestrator:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or 'qwen3.6-max-preview'
        llm_cfg = {'model': self.model_name, 'api_key': os.getenv('DASHSCOPE_API_KEY')}
        
        self.sub_agent = AssessmentAgent(llm=llm_cfg)
        self.main_agent = OrchestratorAgent(model_name=self.model_name)
        
        self.active_sub_task = False
        self.sub_agent_history = []
        self.main_agent_history = []

    async def delegate_task(self, task_instruction: str):
        """异步派发任务，启动专属子 Agent"""
        print(f"\n[Orchestrator] Delegating task to Sub-Agent...")
        self.active_sub_task = True
        self.sub_agent_history.append({'role': 'user', 'content': task_instruction})
        
        await self._run_sub_agent()

    async def update_agent_context(self, new_info: str):
        """状态注入。当用户补充信息时，无缝打断并注入到运行中的子 Agent"""
        print(f"\n[Orchestrator] Updating context for active Sub-Agent...")
        self.sub_agent_history.append({'role': 'user', 'content': f"Context update/interrupt: {new_info}"})
        
        await self._run_sub_agent()

    async def _run_sub_agent(self):
        print(f"\n[Assessment Sub-Agent]: ", end="", flush=True)
        response = []
        printed_lens = {}
        reported_funcs = set()
        
        for chunk in self.sub_agent.run(self.sub_agent_history):
            response = chunk
            if not response:
                continue
                
            for i, msg in enumerate(response):
                if i not in printed_lens:
                    printed_lens[i] = 0
                
                role = msg.get('role', '')
                
                if role == 'assistant':
                    func_call = msg.get('function_call')
                    if func_call and i not in reported_funcs:
                        name = func_call.name if hasattr(func_call, 'name') else func_call.get('name', 'unknown')
                        print(f"\n[System: ⏳ 正在调用工具 `{name}` 进行查询...]")
                        print(f"[Assessment Sub-Agent]: ", end="", flush=True)
                        reported_funcs.add(i)
                    
                    content = msg.get('content', '')
                    if content and isinstance(content, str):
                        new_text = content[printed_lens[i]:]
                        if new_text:
                            print(new_text, end="", flush=True)
                            printed_lens[i] = len(content)
                            
                elif role in ['function', 'tool']:
                    if i not in reported_funcs:
                        name = msg.get('name', 'unknown')
                        print(f"\n[System: ✅ 工具 `{name}` 返回结果]")
                        print(f"[Assessment Sub-Agent]: ", end="", flush=True)
                        reported_funcs.add(i)

        print() # Final newline
        if response:
            self.sub_agent_history.extend(response)

    async def terminate_task(self):
        """终止子任务或放弃当前话题"""
        print("\n[Orchestrator] Terminating active sub-task. Returning to main menu.")
        self.active_sub_task = False
        self.sub_agent_history = []

    async def run_tui(self):
        print("="*50)
        print(" Medical Side Effect Assessment TUI (qwen-agent) ")
        print("="*50)
        print("Commands:")
        print("  'exit' / 'quit' : Stop the application")
        print("  'terminate'     : Terminate active sub-task")
        print("="*50)
        
        while True:
            try:
                user_input = input("\nUser: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
                
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting...")
                break
            elif user_input.lower() == 'terminate':
                await self.terminate_task()
                continue
            
            if self.active_sub_task:
                await self.update_agent_context(user_input)
            else:
                self.main_agent_history.append({'role': 'user', 'content': user_input})
                
                response = await self.main_agent.generate_response(user_input, self.main_agent_history[:-1])
                
                if response.thought and response.thought != "执行工具调用":
                    print(f"\n[Orchestrator 思考]: {response.thought}")
                
                # Check tool calls
                delegated = False
                if response.tool_calls:
                    for tc in response.tool_calls:
                        tool_name = tc["name"]
                        print(f"\n[System: 🤖 Orchestrator 决定调用工具 `{tool_name}`]")
                        
                        if tool_name == "delegate_assessment_task":
                            await self.delegate_task(user_input)
                            delegated = True
                        elif tool_name == "terminate_task":
                            await self.terminate_task()
                        elif tool_name == "update_agent_context":
                            await self.update_agent_context(user_input)
                        elif tool_name == "discover_skills":
                            tool_instance = self.main_agent.tools_instances.get(tool_name)
                            if tool_instance:
                                result = tool_instance.call(tc.get("arguments", {}))
                                skills_found = result.get('skills', [])
                                print(f"[System: ✅ 工具 `{tool_name}` 执行完成: 找到 {len(skills_found)} 个技能]")
                                # 模拟 LLM 多轮机制：由于现在是 MVP 单轮，查完直接派发
                                print(f"[System: ➡️ 根据检索结果，自动转交评估代理...]")
                                await self.delegate_task(user_input)
                                delegated = True
                
                if response.reply and not delegated:
                    print(f"\n[Orchestrator Agent]: {response.reply}")
                    self.main_agent_history.append({'role': 'assistant', 'content': response.reply})
                elif not response.reply and not response.tool_calls and not delegated:
                    print("\n[Orchestrator Agent]: (没有任何回复)")

if __name__ == '__main__':
    orchestrator = Orchestrator()
    asyncio.run(orchestrator.run_tui())

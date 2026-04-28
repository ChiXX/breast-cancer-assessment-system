import os
import json
from abc import ABC, abstractmethod
from typing import List, Optional, Iterator, Union
import dashscope
from qwen_agent.agents import Assistant
from langsmith import traceable
from mcp.utils.event_logger import eventlog

class BaseMedicalAgent(ABC):
    """
    Abstract base class for all medical agents in the system.
    Ensures consistent initialization and interface.
    """
    
    def __init__(self, llm_cfg: dict, name: str, system_prompt: str, tools: Optional[List[str]] = None):
        self.llm_cfg = llm_cfg
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []
        self._last_logged_action = None # To avoid duplicate logs in stream
        
        # Ensure API key is set
        dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')
        
        # Initialize the underlying Qwen Assistant
        self.agent = Assistant(
            llm=self.llm_cfg,
            system_message=self.system_prompt,
            function_list=self.tools,
            name=self.name
        )

    def _log_tool_call(self, tool_name: str, tool_input: Union[str, dict]):
        """
        Log tool calls to the event log.
        """
        # Create a unique signature for this tool call to avoid duplicates in the stream
        action_signature = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
        if self._last_logged_action == action_signature:
            return
        
        self._last_logged_action = action_signature
        
        eventlog(
            event_type="TOOL_CALL",
            message=f"Agent [{self.name}] using tool [{tool_name}]",
            data={"agent": self.name, "tool": tool_name, "input": tool_input}
        )

    @abstractmethod
    def run(self, messages: List[dict]) -> Iterator[dict]:
        """
        Main execution method for the agent.
        """
        pass

    @traceable(name="Agent Chat")
    def chat(self, user_input: str, history: Optional[List[dict]] = None) -> str:
        """
        Synchronous helper for one-off interactions.
        """
        # Sanitize history to prevent "Invalid json tool-calling arguments" warnings in qwen-agent
        sanitized_history = []
        import json5
        for msg in (history or []):
            if msg.get('function_call') and isinstance(msg['function_call'].get('arguments'), str):
                try:
                    # If it's already valid JSON, keep it
                    json5.loads(msg['function_call']['arguments'])
                except Exception:
                    # If it's invalid, wrap it in a JSON string or just clear it to avoid spam
                    # We store it in a way that json5.loads will succeed but it indicates an error
                    msg = msg.copy()
                    msg['function_call'] = msg['function_call'].copy()
                    msg['function_call']['arguments'] = json.dumps({
                        "error": "Original arguments were invalid JSON", 
                        "original": msg['function_call']['arguments']
                    })
            sanitized_history.append(msg)
            
        messages = sanitized_history + [{'role': 'user', 'content': user_input}]
        responses = []
        self._last_logged_action = None # Reset for new chat
        
        # Helper to monitor tool calls in the stream
        for chunk in self.run(messages):
            # Qwen-agent Assistant.run yields increments of the response.
            # When a tool is called, the chunk often contains the tool call information.
            if isinstance(chunk, list) and len(chunk) > 0:
                last_chunk = chunk[-1]
                if last_chunk.get('role') == 'assistant' and 'action' in last_chunk:
                    action = last_chunk.get('action')
                    action_input = last_chunk.get('action_input')
                    if action:
                        self._log_tool_call(action, action_input)
            
            responses.append(chunk)
        
        if responses:
            last_msg = responses[-1]
            content = ""
            if isinstance(last_msg, list) and len(last_msg) > 0:
                content = last_msg[-1].get('content', '')
            elif isinstance(last_msg, dict):
                content = last_msg.get('content', '')
            return content
        return ""

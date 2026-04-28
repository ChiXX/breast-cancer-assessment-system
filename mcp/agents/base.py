import os
from abc import ABC, abstractmethod
from typing import List, Optional, Iterator, Union
import dashscope
from qwen_agent.agents import Assistant
from langsmith import traceable

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
        
        # Ensure API key is set
        dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')
        
        # Initialize the underlying Qwen Assistant
        self.agent = Assistant(
            llm=self.llm_cfg,
            system_message=self.system_prompt,
            function_list=self.tools,
            name=self.name
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
        if history is None:
            history = []
        
        messages = history + [{'role': 'user', 'content': user_input}]
        responses = []
        for chunk in self.run(messages):
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

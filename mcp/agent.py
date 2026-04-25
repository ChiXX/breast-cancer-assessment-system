import os
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env before importing other modules
load_dotenv()

import sys
# Ensure the project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.agents.master import MedicalMaster
from mcp.agents.memory_agent import MemoryAgent
import mcp.agents.tools.skill_tools
import mcp.agents.tools.rag_tool
import mcp.agents.tools.memory_tools

async def run_tui():
    """
    A simple Text User Interface for interacting with the MedicalMaster agent.
    """
    import uuid
    session_id = f"{uuid.uuid4().hex}"
    master = MedicalMaster()
    memory_agent = MemoryAgent()
    history = []
    
    print("=" * 100)
    print(" " * 30 + f"Medical Side Effect Assessment TUI (Session: {session_id})")
    print("-" * 100)

    while True:
        try:
            user_input = input("\nUser: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                print("Saving memory before exit...")
                result = memory_agent.process_session(session_id, history)
                print(f"[Memory Agent]: {result}")
                print("Goodbye!")
                break
            
            if user_input.lower() == 'clear':
                history = []
                print("History cleared.")
                continue
                
            if user_input.lower() == '/memory':
                print("Triggering Memory Agent to save current session...")
                result = memory_agent.process_session(session_id, history)
                print(f"[Memory Agent]: {result}")
                continue
                
            if user_input.lower() == '/summarize_all':
                print("Summarizing all memories for this session...")
                result = memory_agent.summarize_all(session_id)
                print(f"[Memory Agent]: {result}")
                continue
            
            if user_input.lower() == '/learn':
                print("Triggering Learning Agent to distill knowledge...")
                # We can call master.chat or master.learning_agent.run directly
                # To be consistent with master's logic, let's call chat or replicate the logic
                result = master.learning_agent.run(force=True)
                print(f"\n[Learning Agent]: {result}")
                continue
            
            # Add user message to history
            history.append({'role': 'user', 'content': user_input})
            
            full_response = ""
            for response_chunk in master.run(history):
                if isinstance(response_chunk, list) and len(response_chunk) > 0:
                    current_content = response_chunk[-1].get('content', '')
                    if current_content:
                        full_response = current_content
            
            print(f"\n[Medical Assistant]: {full_response}")
            
            history.append({'role': 'assistant', 'content': full_response})

        except KeyboardInterrupt:
            print("\nSaving memory before exit...")
            result = memory_agent.process_session(session_id, history)
            print(f"[Memory Agent]: {result}")
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n[Error]: {str(e)}")

if __name__ == "__main__":
    # Check if necessary environment variables are set
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("Warning: DASHSCOPE_API_KEY is not set in environment.")
    
    asyncio.run(run_tui())

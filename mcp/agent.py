import os
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env before importing other modules
load_dotenv()

from mcp.agents.master import MedicalMaster
import mcp.agents.tools.skill_tools
import mcp.agents.tools.rag_tool

async def run_tui():
    """
    A simple Text User Interface for interacting with the MedicalMaster agent.
    """
    master = MedicalMaster()
    history = []
    
    print("=" * 100)
    print(" " * 30 + "Medical Side Effect Assessment TUI")
    print("-" * 100)

    while True:
        try:
            user_input = input("\nUser: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                print("Goodbye!")
                break
            
            if user_input.lower() == 'clear':
                history = []
                print("History cleared.")
                continue
            
            # Add user message to history
            history.append({'role': 'user', 'content': user_input})
            
            full_response = ""
            # Use the generator for potential future streaming support in TUI
            # For now, we'll just collect the final response
            for response_chunk in master.run(history):
                # qwen-agent Assistant returns a list of messages representing the current state
                if isinstance(response_chunk, list) and len(response_chunk) > 0:
                    current_content = response_chunk[-1].get('content', '')
                    if current_content:
                        full_response = current_content
            
            print(f"\n[Medical Assistant]: {full_response}")
            
            # Update history with assistant response
            history.append({'role': 'assistant', 'content': full_response})

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n[Error]: {str(e)}")

if __name__ == "__main__":
    # Check if necessary environment variables are set
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("Warning: DASHSCOPE_API_KEY is not set in environment.")
    
    asyncio.run(run_tui())

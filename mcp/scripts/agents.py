from mcp.agents.master import MedicalMaster
from mcp.agents.learning_agent import LearningAgent
from mcp.agents.memory_agent import MemoryAgent
from mcp.agents.config import MASTER_MODEL, LEARNING_MODEL, MEMORY_MODEL, get_llm_cfg

# --- State ---
# Singletons for the application
master_agent = MedicalMaster(llm_cfg=get_llm_cfg(MASTER_MODEL))
learning_agent = LearningAgent(llm_cfg=get_llm_cfg(LEARNING_MODEL))
memory_agent = MemoryAgent(llm_cfg=get_llm_cfg(MEMORY_MODEL))

import os

# Centralized Model Configuration for MCP Agents
# This allows switching models for all agents from a single place.

# Default model types
MASTER_MODEL = os.getenv("MASTER_MODEL", "deepseek-v4-flash")
EXPERT_MODEL = os.getenv("EXPERT_MODEL", "qwen3.6-flash")
LEARNING_MODEL = os.getenv("LEARNING_MODEL", "deepseek-v4-flash")
REVIEWER_MODEL = os.getenv("REVIEWER_MODEL", "qwen3.6-flash")
MEMORY_MODEL = os.getenv("MEMORY_MODEL", "qwen3.6-flash")

# LLM Server Config (Common for DashScope)
DEFAULT_LLM_CONFIG = {
    'model_server': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'api_key': os.getenv('DASHSCOPE_API_KEY'),
    'generate_cfg': {
        'top_p': 0.8,
        'temperature': 0.1
    }
}

def get_llm_cfg(model_type: str, override_cfg: dict = None):
    """
    Helper to get a full LLM config for a specific model type.
    """
    cfg = DEFAULT_LLM_CONFIG.copy()
    cfg['model'] = model_type
    if override_cfg:
        cfg.update(override_cfg)
    return cfg

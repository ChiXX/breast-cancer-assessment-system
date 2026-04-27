import httpx
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:9001")

def evaluate_symptoms(user_input: str, session_id: str, history: list = None) -> Dict[str, Any]:
    """
    Calls the MCP server to evaluate symptoms.
    """
    url = f"{MCP_URL}/v1/evaluate"
    payload = {
        "user_input": user_input,
        "session_id": session_id,
        "history": history or [],
    }
    
    try:
        # Explicitly disable environment proxy settings for local calls
        with httpx.Client(timeout=60.0, trust_env=False) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Error calling MCP: {e}")
        # In a real app, we might want to raise a custom exception for the caller to handle
        raise e

def store_memory(session_id: str, history: list) -> Dict[str, Any]:
    """
    Calls the MCP server to store session memory.
    """
    url = f"{MCP_URL}/v1/memory/store"
    payload = {
        "session_id": session_id,
        "history": history
    }
    
    try:
        with httpx.Client(timeout=60.0, trust_env=False) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Error calling MCP store_memory: {e}")
        raise e

def get_all_memories() -> list:
    """
    Calls the MCP server to get all memories with learned status.
    """
    url = f"{MCP_URL}/v1/memory/all"
    try:
        with httpx.Client(timeout=10.0, trust_env=False) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error calling MCP get_all_memories: {e}")
        return []

def trigger_learning() -> Dict[str, Any]:
    """
    Calls the MCP server to trigger knowledge learning.
    """
    url = f"{MCP_URL}/v1/knowledge/learn"
    try:
        with httpx.Client(timeout=10.0, trust_env=False) as client:
            response = client.post(url)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error calling MCP trigger_learning: {e}")
        raise e

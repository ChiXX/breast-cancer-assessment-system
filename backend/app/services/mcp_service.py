import httpx
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

MCP_URL = os.getenv("MCP_URL", "http://localhost:9001")

def evaluate_symptoms(user_input: str, session_id: str) -> Dict[str, Any]:
    """
    Calls the MCP server to evaluate symptoms.
    """
    url = f"{MCP_URL}/v1/evaluate"
    payload = {
        "user_input": user_input,
        "session_id": session_id,
        "history": []
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.error(f"Error calling MCP: {e}")
        # In a real app, we might want to raise a custom exception for the caller to handle
        raise e

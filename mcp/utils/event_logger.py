import os
import json
import logging
import datetime
from typing import Any, Dict, Optional

# Constants
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs"))
LOG_FILE = os.path.join(LOG_DIR, "agent_events.jsonl")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

class EventLogger:
    """
    Structured event logger for monitoring agent behavior.
    Writes events to mcp/logs/agent_events.jsonl and terminal.
    """
    def __init__(self, name: str = "MCP"):
        self.name = name
        self.logger = logging.getLogger(f"EventLogger.{name}")
        self.logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            # File handler (JSONL)
            fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
            fh.setLevel(logging.INFO)
            
            # Console handler (Formatted)
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            
            # Custom formatter for console
            console_formatter = logging.Formatter('\033[1;30m%(asctime)s\033[0m [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
            ch.setFormatter(console_formatter)
            
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def log_event(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None):
        """
        Log a structured event.
        """
        timestamp = datetime.datetime.now().isoformat()
        
        # Clean event for JSONL file (No ANSI colors)
        event = {
            "timestamp": timestamp,
            "level": "INFO",
            "type": event_type,
            "message": message, # Original plain message
            "data": data or {}
        }
        
        # Write clean JSON to file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        
        # Prepare colored message for TERMINAL only
        color = "\033[0m"
        if event_type == "TOOL_CALL":
            color = "\033[1;36m" # Cyan
        elif event_type == "SKILL_READ":
            color = "\033[1;32m" # Green
        elif event_type == "RAG_QUERY":
            color = "\033[1;35m" # Purple
        elif event_type == "MEMORY_READ":
            color = "\033[1;34m" # Blue
        elif event_type == "REQUEST":
            color = "\033[1;30m" # Gray
        elif event_type == "ERROR":
            color = "\033[1;31m" # Red
            
        console_msg = f"{color}[{event_type}] {message}\033[0m"
        if data:
            # Condensed data view for console
            data_str = json.dumps(data, ensure_ascii=False)
            if len(data_str) > 200:
                data_str = data_str[:197] + "..."
            console_msg += f" | {data_str}"
            
        self.logger.info(console_msg)

# Global instances for easy access
eventlog = EventLogger("Global").log_event

# app/utils/api_key_manager.py
import os
import json
import base64
import logging
from typing import Optional # <--- ADD THIS LINE

logger = logging.getLogger(__name__)

class APIKeyManager:
    # ...
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.api_key: Optional[str] = None # <--- CHANGE THIS LINE
        self.load_api_key()

    def save_api_key(self, key: str) -> bool:
        """Encodes and saves the API key to the config file."""
        try:
            encoded_key = base64.b64encode(key.encode()).decode()
            with open(self.config_file, 'w') as f:
                json.dump({"gemini_api_key": encoded_key}, f)
            self.api_key = key
            return True
        except Exception as e:
            logger.error(f"Error saving API key: {e}")
            return False

    def load_api_key(self):
        """Loads and decodes the API key from the config file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                encoded_key = config.get("gemini_api_key", "")
                if encoded_key:
                    self.api_key = base64.b64decode(encoded_key).decode()
        except Exception as e:
            logger.error(f"Error loading API key: {e}")

    def is_configured(self) -> bool:
        """Checks if an API key is currently loaded."""
        return self.api_key is not None and len(self.api_key.strip()) > 0

    def clear_api_key(self) -> bool:
        """Removes the API key file from the disk."""
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            self.api_key = None
            return True
        except Exception as e:
            logger.error(f"Error clearing API key: {e}")
            return False
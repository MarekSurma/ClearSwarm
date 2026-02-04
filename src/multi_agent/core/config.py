"""
Configuration module for loading environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root (3 levels up from this file)
# __file__ = .../src/multi_agent/core/config.py
# project_root = .../
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / '.env'

# Override=True forces values from .env to take precedence over system environment variables
load_dotenv(dotenv_path=env_path, override=True)


class Config:
    """Configuration class for API settings."""

    OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')

    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be set in .env file")
        return True

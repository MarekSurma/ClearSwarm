"""Tests for config module."""
import os
import pytest
from pathlib import Path
from unittest.mock import patch

from multi_agent.core.config import Config


class TestConfig:
    """Test cases for Config class."""

    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        # Create a clean environment without OPENAI_ vars
        env_without_config = {k: v for k, v in os.environ.items()
                             if not k.startswith('OPENAI_')}

        with patch.dict(os.environ, env_without_config, clear=True):
            # Mock load_dotenv to prevent it from loading .env file
            with patch('dotenv.load_dotenv'):
                # Re-import to get fresh values
                import importlib
                from multi_agent.core import config
                importlib.reload(config)

                # Note: OPENAI_API_KEY will be None since it's not set
                assert config.Config.OPENAI_API_BASE == 'https://api.openai.com/v1'
                assert config.Config.OPENAI_MODEL == 'gpt-4'

    def test_environment_override(self):
        """Test that environment variables can be set when .env is not loaded."""
        test_env = {
            'OPENAI_API_BASE': 'https://custom-api.example.com/v1',
            'OPENAI_API_KEY': 'test-api-key-12345',
            'OPENAI_MODEL': 'gpt-4-turbo'
        }

        with patch.dict(os.environ, test_env, clear=True):
            # Mock load_dotenv to prevent .env from overriding
            with patch('dotenv.load_dotenv'):
                # Re-import config to pick up new environment
                import importlib
                from multi_agent.core import config
                importlib.reload(config)

                assert config.Config.OPENAI_API_BASE == 'https://custom-api.example.com/v1'
                assert config.Config.OPENAI_API_KEY == 'test-api-key-12345'
                assert config.Config.OPENAI_MODEL == 'gpt-4-turbo'

    def test_validate_with_api_key(self):
        """Test validation passes when API key is set."""
        test_env = {'OPENAI_API_KEY': 'valid-api-key'}

        with patch.dict(os.environ, test_env):
            # Re-import to get fresh config
            import importlib
            from multi_agent.core import config
            importlib.reload(config)

            # Should not raise exception
            assert config.Config.validate() is True

    def test_validate_without_api_key(self):
        """Test validation fails when API key is missing."""
        # Create clean environment without OPENAI_ vars
        env_without_config = {k: v for k, v in os.environ.items()
                             if not k.startswith('OPENAI_')}

        with patch.dict(os.environ, env_without_config, clear=True):
            # Mock load_dotenv to prevent it from loading .env file
            with patch('dotenv.load_dotenv'):
                # Re-import to get fresh config
                import importlib
                from multi_agent.core import config
                importlib.reload(config)

                # Should raise ValueError
                with pytest.raises(ValueError, match="OPENAI_API_KEY must be set"):
                    config.Config.validate()

    def test_validate_with_empty_api_key(self):
        """Test validation fails when API key is empty string."""
        test_env = {'OPENAI_API_KEY': ''}

        with patch.dict(os.environ, test_env, clear=True):
            # Mock load_dotenv to prevent .env from providing a key
            with patch('dotenv.load_dotenv'):
                import importlib
                from multi_agent.core import config
                importlib.reload(config)

                with pytest.raises(ValueError, match="OPENAI_API_KEY must be set"):
                    config.Config.validate()


class TestConfigDotEnvLoading:
    """Test .env file loading functionality."""

    def test_dotenv_path_calculation(self):
        """Test that .env path is calculated correctly from module location."""
        from multi_agent.core import config

        # Check that project_root is calculated correctly
        # config.py is at src/multi_agent/core/config.py
        # project_root should be 4 levels up
        expected_root = Path(config.__file__).parent.parent.parent.parent
        assert config.project_root == expected_root

    def test_env_path_exists(self):
        """Test that .env file path is constructed correctly."""
        from multi_agent.core import config

        env_path = config.env_path
        assert env_path.name == '.env'
        assert env_path.parent == config.project_root

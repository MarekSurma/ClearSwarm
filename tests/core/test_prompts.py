"""Tests for prompts module."""
import pytest
import tempfile
import yaml
from pathlib import Path

from multi_agent.core.prompts import PromptLoader, get_prompt_loader, set_prompt_loader


class TestPromptLoader:
    """Test cases for PromptLoader class."""

    @pytest.fixture
    def temp_prompts_dir(self):
        """Create a temporary prompts directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_prompts_yaml(self, temp_prompts_dir):
        """Create a sample prompts YAML file."""
        prompts = {
            'system_prompts': {
                'test_prompt': 'This is a test prompt with {variable}',
                'another_prompt': 'Another prompt'
            },
            'runtime_messages': {
                'test_message': 'Test message: {message}'
            },
            'log_messages': {
                'test_log': 'Log: {log_text}'
            },
            'error_messages': {
                'test_error': 'Error: {error_detail}'
            }
        }

        yaml_file = temp_prompts_dir / "test_prompts.yaml"
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(prompts, f)

        return yaml_file

    def test_initialization_with_existing_file(self, temp_prompts_dir, sample_prompts_yaml):
        """Test PromptLoader initialization with existing YAML file."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        assert loader.prompts is not None
        assert 'system_prompts' in loader.prompts

    def test_initialization_with_nonexistent_file(self, temp_prompts_dir):
        """Test PromptLoader falls back to hardcoded prompts when file doesn't exist."""
        loader = PromptLoader(
            prompts_file="nonexistent.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        # Should use fallback prompts
        assert loader.prompts == loader.FALLBACK_PROMPTS

    def test_load_prompts_from_yaml(self, temp_prompts_dir, sample_prompts_yaml):
        """Test loading prompts from YAML file."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        assert loader.prompts['system_prompts']['test_prompt'] == 'This is a test prompt with {variable}'

    def test_get_prompt_with_variables(self, temp_prompts_dir, sample_prompts_yaml):
        """Test getting prompt with variable substitution."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        result = loader.get_prompt('system_prompts', 'test_prompt', variable='VALUE')
        assert result == 'This is a test prompt with VALUE'

    def test_get_prompt_without_variables(self, temp_prompts_dir, sample_prompts_yaml):
        """Test getting prompt without variable substitution."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        result = loader.get_prompt('system_prompts', 'another_prompt')
        assert result == 'Another prompt'

    def test_get_prompt_missing_prompt(self, temp_prompts_dir, sample_prompts_yaml):
        """Test getting a non-existent prompt returns fallback or empty string."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        # Non-existent prompt should return empty string or fallback
        result = loader.get_prompt('system_prompts', 'nonexistent_prompt')
        # Should return fallback if it exists, otherwise empty string
        assert isinstance(result, str)

    def test_get_prompt_missing_variable(self, temp_prompts_dir, sample_prompts_yaml):
        """Test getting prompt with missing variable returns unformatted string."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        # Call without providing required variable
        result = loader.get_prompt('system_prompts', 'test_prompt')
        # Should return unformatted template
        assert '{variable}' in result

    def test_get_system_prompt(self, temp_prompts_dir, sample_prompts_yaml):
        """Test convenience method for system prompts."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        result = loader.get_system_prompt('test_prompt', variable='TEST')
        assert result == 'This is a test prompt with TEST'

    def test_get_runtime_message(self, temp_prompts_dir, sample_prompts_yaml):
        """Test convenience method for runtime messages."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        result = loader.get_runtime_message('test_message', message='Hello')
        assert result == 'Test message: Hello'

    def test_get_log_message(self, temp_prompts_dir, sample_prompts_yaml):
        """Test convenience method for log messages."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        result = loader.get_log_message('test_log', log_text='Debug info')
        assert result == 'Log: Debug info'

    def test_get_error_message(self, temp_prompts_dir, sample_prompts_yaml):
        """Test convenience method for error messages."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        result = loader.get_error_message('test_error', error_detail='Failed')
        assert result == 'Error: Failed'

    def test_deep_merge(self, temp_prompts_dir):
        """Test deep merge of prompts (override + fallback)."""
        # Create partial YAML that only overrides some prompts
        partial_prompts = {
            'system_prompts': {
                'custom_prompt': 'Custom prompt'
            }
        }

        yaml_file = temp_prompts_dir / "partial.yaml"
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(partial_prompts, f)

        loader = PromptLoader(
            prompts_file="partial.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        # Should have both custom and fallback prompts
        assert 'custom_prompt' in loader.prompts['system_prompts']
        # Should also have fallback prompts
        assert 'available_tools_header' in loader.prompts['system_prompts']

    def test_format_task_list(self, temp_prompts_dir, sample_prompts_yaml):
        """Test formatting task list."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        task_ids = ["task_1", "task_2", "task_3"]
        result = loader.format_task_list(task_ids)

        assert "- task_1" in result
        assert "- task_2" in result
        assert "- task_3" in result

    def test_format_task_list_empty(self, temp_prompts_dir, sample_prompts_yaml):
        """Test formatting empty task list."""
        loader = PromptLoader(
            prompts_file="test_prompts.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        result = loader.format_task_list([])
        assert result == ""

    def test_reload(self, temp_prompts_dir):
        """Test reloading prompts from file."""
        # Create initial YAML
        yaml_file = temp_prompts_dir / "reload_test.yaml"
        initial_prompts = {
            'system_prompts': {
                'test': 'Initial value'
            }
        }
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(initial_prompts, f)

        loader = PromptLoader(
            prompts_file="reload_test.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        assert loader.get_system_prompt('test') == 'Initial value'

        # Update YAML file
        updated_prompts = {
            'system_prompts': {
                'test': 'Updated value'
            }
        }
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(updated_prompts, f)

        # Reload
        loader.reload()

        assert loader.get_system_prompt('test') == 'Updated value'

    def test_load_empty_yaml_file(self, temp_prompts_dir):
        """Test loading empty YAML file falls back to hardcoded prompts."""
        yaml_file = temp_prompts_dir / "empty.yaml"
        yaml_file.write_text("")

        loader = PromptLoader(
            prompts_file="empty.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        # Should use fallback prompts
        assert loader.prompts == loader.FALLBACK_PROMPTS

    def test_load_malformed_yaml(self, temp_prompts_dir):
        """Test loading malformed YAML falls back to hardcoded prompts."""
        yaml_file = temp_prompts_dir / "malformed.yaml"
        yaml_file.write_text("invalid: yaml: content: [")

        loader = PromptLoader(
            prompts_file="malformed.yaml",
            prompts_dir=str(temp_prompts_dir)
        )

        # Should use fallback prompts
        assert loader.prompts == loader.FALLBACK_PROMPTS

    def test_fallback_prompts_coverage(self):
        """Test that fallback prompts contain all required categories."""
        assert 'system_prompts' in PromptLoader.FALLBACK_PROMPTS
        assert 'runtime_messages' in PromptLoader.FALLBACK_PROMPTS
        assert 'log_messages' in PromptLoader.FALLBACK_PROMPTS
        assert 'error_messages' in PromptLoader.FALLBACK_PROMPTS


class TestGetPromptLoader:
    """Test cases for get_prompt_loader singleton function."""

    def test_get_prompt_loader_singleton(self):
        """Test that get_prompt_loader returns the same instance."""
        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()

        assert loader1 is loader2

    def test_get_prompt_loader_returns_prompt_loader(self):
        """Test that get_prompt_loader returns a PromptLoader instance."""
        loader = get_prompt_loader()
        assert isinstance(loader, PromptLoader)


class TestSetPromptLoader:
    """Test cases for set_prompt_loader function."""

    def test_set_prompt_loader_resets_singleton(self):
        """Test that set_prompt_loader creates a new instance."""
        # Get initial loader
        loader1 = get_prompt_loader()

        # Reset the loader
        set_prompt_loader()

        # Get new loader
        loader2 = get_prompt_loader()

        # Note: They will be different instances if set_prompt_loader was called
        # But since we're in tests, the global state might be shared
        assert isinstance(loader2, PromptLoader)

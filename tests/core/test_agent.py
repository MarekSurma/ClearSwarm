"""Tests for agent module."""
import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from multi_agent.core.agent import Agent, AgentConfig, AgentLoader
from multi_agent.core.llm_client import MockLLMClient
from multi_agent.tools.loader import ToolLoader
from multi_agent.tools.base import BaseTool


class TestAgentConfig:
    """Test cases for AgentConfig class."""

    @pytest.fixture
    def temp_agent_dir(self):
        """Create a temporary agent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / "test_agent"
            agent_dir.mkdir()
            yield agent_dir

    def test_load_agent_config(self, temp_agent_dir):
        """Test loading agent configuration from directory."""
        # Create agent files
        (temp_agent_dir / "description.txt").write_text("Test agent description")
        (temp_agent_dir / "system_prompt.txt").write_text("You are a test agent")
        (temp_agent_dir / "tools.txt").write_text("calculator\ntext_analyzer")

        config = AgentConfig("test_agent", temp_agent_dir)

        assert config.name == "test_agent"
        assert config.description == "Test agent description"
        assert config.system_prompt == "You are a test agent"
        assert config.tools == ["calculator", "text_analyzer"]

    def test_load_agent_config_missing_files(self, temp_agent_dir):
        """Test loading agent config with missing files uses empty defaults."""
        config = AgentConfig("test_agent", temp_agent_dir)

        assert config.name == "test_agent"
        assert config.description == ""
        assert config.system_prompt == ""
        assert config.tools == []

    def test_load_tools_list_with_empty_lines(self, temp_agent_dir):
        """Test that empty lines in tools.txt are ignored."""
        (temp_agent_dir / "tools.txt").write_text("calculator\n\ntext_analyzer\n\n")

        config = AgentConfig("test_agent", temp_agent_dir)

        assert config.tools == ["calculator", "text_analyzer"]


class TestAgent:
    """Test cases for Agent class."""

    @pytest.fixture
    def temp_agent_dir(self):
        """Create a temporary agent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / "test_agent"
            agent_dir.mkdir()
            (agent_dir / "description.txt").write_text("Test agent")
            (agent_dir / "system_prompt.txt").write_text("You are a test agent")
            (agent_dir / "tools.txt").write_text("")
            yield agent_dir

    @pytest.fixture
    def mock_tool_loader(self):
        """Create a mock ToolLoader."""
        loader = Mock(spec=ToolLoader)
        loader.get_all_tools.return_value = {}
        loader.get_tool.return_value = None
        return loader

    @pytest.fixture
    def mock_agent_loader(self):
        """Create a mock AgentLoader."""
        loader = Mock(spec=AgentLoader)
        loader.has_agent.return_value = False
        loader.get_agent_config.return_value = None
        return loader

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = Mock()
        db.create_agent_execution.return_value = "test-agent-id-123"
        db.update_agent_state = Mock()
        db.complete_agent_execution = Mock()
        return db

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        return MockLLMClient(responses=["Test response"])

    def test_agent_initialization(self, temp_agent_dir, mock_tool_loader, mock_agent_loader, mock_db, mock_llm_client):
        """Test Agent initialization."""
        config = AgentConfig("test_agent", temp_agent_dir)

        with patch('multi_agent.core.agent.get_database', return_value=mock_db):
            agent = Agent(
                config=config,
                tool_loader=mock_tool_loader,
                agent_loader=mock_agent_loader,
                llm_client=mock_llm_client
            )

            assert agent.config == config
            assert agent.agent_id == "test-agent-id-123"
            assert isinstance(agent.messages, list)
            assert len(agent.messages) == 1  # System prompt
            assert agent.messages[0]["role"] == "system"

    def test_extract_tool_call_valid(self, temp_agent_dir, mock_tool_loader, mock_agent_loader, mock_db, mock_llm_client):
        """Test extracting valid tool call from text."""
        config = AgentConfig("test_agent", temp_agent_dir)

        with patch('multi_agent.core.agent.get_database', return_value=mock_db):
            agent = Agent(config, mock_tool_loader, mock_agent_loader, mock_llm_client)

            text = '''
<tool_call>
<tool_name>calculator</tool_name>
<parameters>
{"operation": "add", "a": 5, "b": 3}
</parameters>
</tool_call>
'''
            result = agent._extract_tool_call(text)

            assert result is not None
            assert result['tool_name'] == 'calculator'
            assert result['parameters'] == {"operation": "add", "a": 5, "b": 3}

    def test_extract_tool_call_invalid_json(self, temp_agent_dir, mock_tool_loader, mock_agent_loader, mock_db, mock_llm_client):
        """Test extracting tool call with invalid JSON returns None."""
        config = AgentConfig("test_agent", temp_agent_dir)

        with patch('multi_agent.core.agent.get_database', return_value=mock_db):
            agent = Agent(config, mock_tool_loader, mock_agent_loader, mock_llm_client)

            text = '''
<tool_call>
<tool_name>calculator</tool_name>
<parameters>
{invalid json}
</parameters>
</tool_call>
'''
            result = agent._extract_tool_call(text)
            assert result is None

    def test_extract_all_tool_calls(self, temp_agent_dir, mock_tool_loader, mock_agent_loader, mock_db):
        """Test extracting multiple tool calls from text (using ToolCallHandler)."""
        from multi_agent.core.orchestrator import ToolCallHandler

        text = '''
<tool_call>
<tool_name>calculator</tool_name>
<parameters>{"operation": "add"}</parameters>
</tool_call>

<tool_call>
<tool_name>text_analyzer</tool_name>
<call_mode>asynchronous</call_mode>
<parameters>{"text": "hello"}</parameters>
</tool_call>
'''
        handler = ToolCallHandler()
        results = handler.extract_all_tool_calls(text)

        assert len(results) == 2
        assert results[0]['tool_name'] == 'calculator'
        assert results[0]['call_mode'] == 'synchronous'  # Default
        assert results[1]['tool_name'] == 'text_analyzer'
        assert results[1]['call_mode'] == 'asynchronous'

    def test_clean_result(self, temp_agent_dir, mock_tool_loader, mock_agent_loader, mock_db, mock_llm_client):
        """Test cleaning result by removing <think> tags."""
        config = AgentConfig("test_agent", temp_agent_dir)

        with patch('multi_agent.core.agent.get_database', return_value=mock_db):
            agent = Agent(config, mock_tool_loader, mock_agent_loader, mock_llm_client)

            text = "<think>This is internal thought</think>\nThis is the result"
            cleaned = agent._clean_result(text)

            assert "<think>" not in cleaned
            assert "This is the result" in cleaned

    def test_save_log_file(self, temp_agent_dir, mock_tool_loader, mock_agent_loader, mock_db, mock_llm_client):
        """Test saving interaction log to file."""
        config = AgentConfig("test_agent", temp_agent_dir)

        with patch('multi_agent.core.agent.get_database', return_value=mock_db):
            agent = Agent(config, mock_tool_loader, mock_agent_loader, mock_llm_client)

            # Add some interaction data
            agent.interaction_log["test_field"] = "test_value"

            # Save log
            agent._save_log_file()

            # Verify file was created
            assert agent.log_file.exists()

            # Verify content
            import json
            with open(agent.log_file, 'r') as f:
                loaded_log = json.load(f)
                assert loaded_log["test_field"] == "test_value"


class TestAgentLoader:
    """Test cases for AgentLoader class."""

    @pytest.fixture
    def temp_agents_dir(self):
        """Create a temporary agents directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / "agents"
            agents_dir.mkdir()
            yield agents_dir

    @pytest.fixture
    def sample_agent(self, temp_agents_dir):
        """Create a sample agent directory."""
        agent_dir = temp_agents_dir / "sample_agent"
        agent_dir.mkdir()
        (agent_dir / "description.txt").write_text("Sample agent for testing")
        (agent_dir / "system_prompt.txt").write_text("You are a sample agent")
        (agent_dir / "tools.txt").write_text("calculator")
        return agent_dir

    def test_agent_loader_initialization(self, temp_agents_dir):
        """Test AgentLoader initialization."""
        loader = AgentLoader(agents_dir=str(temp_agents_dir))
        assert loader.agents_dir == temp_agents_dir
        assert isinstance(loader._agent_configs, dict)

    def test_load_agent_configs(self, temp_agents_dir, sample_agent):
        """Test loading agent configurations from directory."""
        loader = AgentLoader(agents_dir=str(temp_agents_dir))

        assert "sample_agent" in loader._agent_configs
        assert loader._agent_configs["sample_agent"].description == "Sample agent for testing"

    def test_has_agent(self, temp_agents_dir, sample_agent):
        """Test checking if agent exists."""
        loader = AgentLoader(agents_dir=str(temp_agents_dir))

        assert loader.has_agent("sample_agent") is True
        assert loader.has_agent("nonexistent_agent") is False

    def test_get_agent_config(self, temp_agents_dir, sample_agent):
        """Test getting agent configuration by name."""
        loader = AgentLoader(agents_dir=str(temp_agents_dir))

        config = loader.get_agent_config("sample_agent")
        assert isinstance(config, AgentConfig)
        assert config.name == "sample_agent"

    def test_get_available_agents(self, temp_agents_dir, sample_agent):
        """Test getting list of available agents."""
        loader = AgentLoader(agents_dir=str(temp_agents_dir))

        agents = loader.get_available_agents()
        assert "sample_agent" in agents

    def test_create_agent(self, temp_agents_dir, sample_agent):
        """Test creating an agent instance."""
        mock_llm = MockLLMClient()
        loader = AgentLoader(agents_dir=str(temp_agents_dir), llm_client=mock_llm)

        with patch('multi_agent.core.agent.get_database') as mock_get_db:
            mock_db = Mock()
            mock_db.create_agent_execution.return_value = "test-id"
            mock_db.update_agent_state = Mock()
            mock_get_db.return_value = mock_db

            agent = loader.create_agent("sample_agent")

            assert isinstance(agent, Agent)
            assert agent.config.name == "sample_agent"

    def test_create_agent_with_parent(self, temp_agents_dir, sample_agent):
        """Test creating a child agent with parent information."""
        mock_llm = MockLLMClient()
        loader = AgentLoader(agents_dir=str(temp_agents_dir), llm_client=mock_llm)

        with patch('multi_agent.core.agent.get_database') as mock_get_db:
            mock_db = Mock()
            mock_db.create_agent_execution.return_value = "child-id"
            mock_db.update_agent_state = Mock()
            mock_get_db.return_value = mock_db

            agent = loader.create_agent(
                "sample_agent",
                parent_agent_id="parent-id",
                parent_agent_name="parent_agent"
            )

            assert agent.parent_agent_id == "parent-id"
            assert agent.parent_agent_name == "parent_agent"

    def test_load_agents_ignores_underscore_dirs(self, temp_agents_dir):
        """Test that directories starting with underscore are ignored."""
        # Create a directory starting with underscore
        private_dir = temp_agents_dir / "_private_agent"
        private_dir.mkdir()
        (private_dir / "description.txt").write_text("Should be ignored")

        loader = AgentLoader(agents_dir=str(temp_agents_dir))

        assert "_private_agent" not in loader._agent_configs

    def test_load_agents_empty_directory(self, temp_agents_dir):
        """Test loading from empty directory."""
        loader = AgentLoader(agents_dir=str(temp_agents_dir))

        assert loader._agent_configs == {}

    def test_create_agent_not_found(self, temp_agents_dir):
        """Test creating non-existent agent raises KeyError."""
        mock_llm = MockLLMClient()
        loader = AgentLoader(agents_dir=str(temp_agents_dir), llm_client=mock_llm)

        with pytest.raises(KeyError):
            with patch('multi_agent.core.agent.get_database'):
                loader.create_agent("nonexistent_agent")


@pytest.mark.asyncio
class TestAgentAsync:
    """Test cases for Agent async functionality."""

    @pytest.fixture
    def temp_agent_dir(self):
        """Create a temporary agent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_dir = Path(tmpdir) / "async_agent"
            agent_dir.mkdir()
            (agent_dir / "description.txt").write_text("Async test agent")
            (agent_dir / "system_prompt.txt").write_text("You are an async agent")
            (agent_dir / "tools.txt").write_text("test_tool\nend_session")  # Add test_tool to authorized tools
            yield agent_dir

    async def test_execute_tool_async(self, temp_agent_dir):
        """Test launching async tool execution (using TaskManager)."""
        from multi_agent.core.orchestrator import TaskManager

        config = AgentConfig("async_agent", temp_agent_dir)

        # Create mock tool with proper function definition
        mock_tool = Mock(spec=BaseTool)
        mock_tool.name = "test_tool"
        mock_tool.execute.return_value = "Tool result"
        mock_tool.to_function_definition.return_value = {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

        mock_tool_loader = Mock()
        mock_tool_loader.get_all_tools.return_value = {"test_tool": mock_tool}
        mock_tool_loader.get_tool.return_value = mock_tool

        mock_agent_loader = Mock()
        mock_agent_loader.has_agent.return_value = False

        mock_db = Mock()
        mock_db.create_agent_execution.return_value = "agent-id"
        mock_db.create_tool_execution.return_value = "tool-exec-id"
        mock_db.update_agent_state = Mock()
        mock_db.complete_tool_execution = Mock()

        mock_llm = MockLLMClient()

        with patch('multi_agent.core.agent.get_database', return_value=mock_db):
            agent = Agent(config, mock_tool_loader, mock_agent_loader, mock_llm)

            # Use TaskManager to launch async task
            task_manager = TaskManager()
            task_id = task_manager.generate_task_id("test_tool")

            await task_manager.launch_task(
                task_id,
                "test_tool",
                {"param": "value"},
                agent._execute_tool
            )

            assert task_id.startswith("test_tool_")
            assert await task_manager.has_pending_tasks()

            # Wait for task to complete
            result = await task_manager.wait_for_result(timeout=1.0)
            assert result is not None
            completed_task_id, result_text = result
            assert completed_task_id == task_id
            assert result_text == "Tool result"

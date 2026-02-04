"""Tests for tool loader."""
import pytest
import tempfile
from pathlib import Path

from multi_agent.tools.base import BaseTool
from multi_agent.tools.loader import ToolLoader


class TestToolLoader:
    """Test cases for ToolLoader class."""

    @pytest.fixture
    def temp_tools_dir(self):
        """Create a temporary tools directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_tool_file(self, temp_tools_dir):
        """Create a sample tool file."""
        tool_code = '''
from multi_agent.tools.base import BaseTool

class SampleTool(BaseTool):
    @property
    def name(self) -> str:
        return "sample_tool"

    @property
    def description(self) -> str:
        return "A sample tool for testing"

    def execute(self, message: str) -> str:
        return f"Processed: {message}"
'''
        tool_file = temp_tools_dir / "sample_tool.py"
        tool_file.write_text(tool_code)
        return tool_file

    def test_initialization(self, temp_tools_dir):
        """Test ToolLoader initialization."""
        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        assert loader.tools_dir == temp_tools_dir
        assert isinstance(loader._tools, dict)

    def test_load_tools_from_directory(self, temp_tools_dir, sample_tool_file):
        """Test loading tools from directory."""
        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        tools = loader.load_tools()

        assert "sample_tool" in tools
        assert isinstance(tools["sample_tool"], BaseTool)
        assert tools["sample_tool"].description == "A sample tool for testing"

    def test_load_tools_empty_directory(self, temp_tools_dir):
        """Test loading from empty directory."""
        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        tools = loader.load_tools()

        assert tools == {}

    def test_load_tools_nonexistent_directory(self):
        """Test loading from non-existent directory."""
        loader = ToolLoader(tools_dir="nonexistent_directory")
        tools = loader.load_tools()

        assert tools == {}

    def test_ignore_underscore_files(self, temp_tools_dir):
        """Test that files starting with underscore are ignored."""
        # Create a file starting with underscore
        private_file = temp_tools_dir / "_private_tool.py"
        private_file.write_text('''
from multi_agent.tools.base import BaseTool

class PrivateTool(BaseTool):
    @property
    def name(self) -> str:
        return "private_tool"

    @property
    def description(self) -> str:
        return "Should be ignored"

    def execute(self) -> str:
        return "result"
''')

        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        tools = loader.load_tools()

        assert "private_tool" not in tools

    def test_load_multiple_tools_from_one_file(self, temp_tools_dir):
        """Test loading multiple tool classes from a single file."""
        multi_tool_file = temp_tools_dir / "multi_tools.py"
        multi_tool_file.write_text('''
from multi_agent.tools.base import BaseTool

class ToolOne(BaseTool):
    @property
    def name(self) -> str:
        return "tool_one"

    @property
    def description(self) -> str:
        return "First tool"

    def execute(self) -> str:
        return "one"

class ToolTwo(BaseTool):
    @property
    def name(self) -> str:
        return "tool_two"

    @property
    def description(self) -> str:
        return "Second tool"

    def execute(self) -> str:
        return "two"
''')

        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        tools = loader.load_tools()

        assert "tool_one" in tools
        assert "tool_two" in tools
        assert tools["tool_one"].description == "First tool"
        assert tools["tool_two"].description == "Second tool"

    def test_get_tool(self, temp_tools_dir, sample_tool_file):
        """Test getting a specific tool by name."""
        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        loader.load_tools()

        tool = loader.get_tool("sample_tool")
        assert tool.name == "sample_tool"

    def test_get_tool_not_found(self, temp_tools_dir):
        """Test getting a non-existent tool raises KeyError."""
        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        loader.load_tools()

        with pytest.raises(KeyError):
            loader.get_tool("nonexistent_tool")

    def test_get_all_tools(self, temp_tools_dir, sample_tool_file):
        """Test getting all loaded tools."""
        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        loader.load_tools()

        all_tools = loader.get_all_tools()
        assert isinstance(all_tools, dict)
        assert "sample_tool" in all_tools

    def test_get_tool_definitions_all(self, temp_tools_dir, sample_tool_file):
        """Test getting function definitions for all tools."""
        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        loader.load_tools()

        definitions = loader.get_tool_definitions()
        assert isinstance(definitions, list)
        assert len(definitions) == 1
        assert definitions[0]["type"] == "function"
        assert definitions[0]["function"]["name"] == "sample_tool"

    def test_get_tool_definitions_specific_tools(self, temp_tools_dir):
        """Test getting function definitions for specific tools."""
        # Create multiple tools
        multi_tool_file = temp_tools_dir / "multi_tools.py"
        multi_tool_file.write_text('''
from multi_agent.tools.base import BaseTool

class ToolA(BaseTool):
    @property
    def name(self) -> str:
        return "tool_a"

    @property
    def description(self) -> str:
        return "Tool A"

    def execute(self) -> str:
        return "a"

class ToolB(BaseTool):
    @property
    def name(self) -> str:
        return "tool_b"

    @property
    def description(self) -> str:
        return "Tool B"

    def execute(self) -> str:
        return "b"
''')

        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        loader.load_tools()

        # Get definitions for only tool_a
        definitions = loader.get_tool_definitions(tool_names=["tool_a"])
        assert len(definitions) == 1
        assert definitions[0]["function"]["name"] == "tool_a"

    def test_get_tool_definitions_ignores_missing_tools(self, temp_tools_dir, sample_tool_file):
        """Test that get_tool_definitions ignores non-existent tools."""
        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        loader.load_tools()

        # Request definitions including a non-existent tool
        definitions = loader.get_tool_definitions(
            tool_names=["sample_tool", "nonexistent_tool"]
        )

        # Should only return definition for existing tool
        assert len(definitions) == 1
        assert definitions[0]["function"]["name"] == "sample_tool"

    def test_load_tool_with_syntax_error(self, temp_tools_dir, capsys):
        """Test that syntax errors in tool files are handled gracefully."""
        bad_tool_file = temp_tools_dir / "bad_tool.py"
        bad_tool_file.write_text('''
from multi_agent.tools.base import BaseTool

class BadTool(BaseTool):
    @property
    def name(self) -> str
        return "bad_tool"  # Missing colon - syntax error
''')

        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        tools = loader.load_tools()

        # Should not crash, just skip the bad file
        assert "bad_tool" not in tools

        # Should print error message
        captured = capsys.readouterr()
        assert "Error loading tool" in captured.out

    def test_load_tool_with_import_error(self, temp_tools_dir, capsys):
        """Test that import errors in tool files are handled gracefully."""
        bad_import_file = temp_tools_dir / "bad_import.py"
        bad_import_file.write_text('''
from nonexistent_module import something

from multi_agent.tools.base import BaseTool

class ImportErrorTool(BaseTool):
    @property
    def name(self) -> str:
        return "import_error_tool"

    @property
    def description(self) -> str:
        return "Has import error"

    def execute(self) -> str:
        return "result"
''')

        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        tools = loader.load_tools()

        # Should not crash, just skip the bad file
        assert "import_error_tool" not in tools

        # Should print error message
        captured = capsys.readouterr()
        assert "Error loading tool" in captured.out

    def test_load_tools_skips_base_tool_class(self, temp_tools_dir):
        """Test that BaseTool itself is not loaded as a tool."""
        # Create a file that imports BaseTool
        tool_file = temp_tools_dir / "with_base.py"
        tool_file.write_text('''
from multi_agent.tools.base import BaseTool

class ActualTool(BaseTool):
    @property
    def name(self) -> str:
        return "actual_tool"

    @property
    def description(self) -> str:
        return "Actual tool"

    def execute(self) -> str:
        return "result"
''')

        loader = ToolLoader(tools_dir=str(temp_tools_dir))
        tools = loader.load_tools()

        # Should only load ActualTool, not BaseTool
        assert "actual_tool" in tools
        assert len(tools) == 1

"""
Tool loader for the multi-agent system.
Dynamically loads tools from the user/tools directory.
"""
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List

from .base import BaseTool


class ToolLoader:
    """Loads tools from the user/tools directory."""

    def __init__(self, tools_dir: str = "user/tools"):
        """
        Initialize tool loader.

        Args:
            tools_dir: Directory containing tool modules (default: user/tools)
        """
        self.tools_dir = Path(tools_dir)
        self._tools: Dict[str, BaseTool] = {}

    def load_tools(self) -> Dict[str, BaseTool]:
        """
        Load all tools from tools directory.

        Returns:
            Dictionary mapping tool names to tool instances
        """
        if not self.tools_dir.exists():
            return {}

        for tool_file in self.tools_dir.glob("*.py"):
            if tool_file.name.startswith("_"):
                continue

            try:
                # Load module dynamically
                spec = importlib.util.spec_from_file_location(
                    tool_file.stem, tool_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find all BaseTool subclasses in the module
                for item_name in dir(module):
                    item = getattr(module, item_name)
                    if (inspect.isclass(item) and
                        issubclass(item, BaseTool) and
                        item is not BaseTool):
                        tool_instance = item()
                        self._tools[tool_instance.name] = tool_instance

            except Exception as e:
                print(f"Error loading tool from {tool_file}: {e}")

        return self._tools

    def get_tool(self, name: str) -> BaseTool:
        """
        Get a tool by name.

        Args:
            name: Name of the tool

        Returns:
            Tool instance

        Raises:
            KeyError: If tool not found
        """
        return self._tools[name]

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all loaded tools."""
        return self._tools

    def get_tool_definitions(self, tool_names: List[str] = None) -> List[dict]:
        """
        Get OpenAI function definitions for specified tools.

        Args:
            tool_names: List of tool names to include (None = all tools)

        Returns:
            List of function definitions
        """
        if tool_names is None:
            tool_names = list(self._tools.keys())

        definitions = []
        for name in tool_names:
            if name in self._tools:
                definitions.append(self._tools[name].to_function_definition())

        return definitions

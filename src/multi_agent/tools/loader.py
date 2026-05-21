"""
Tool loader for the multi-agent system.
Dynamically loads tools from the user/tools directory.
"""
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Union, Sequence

from .base import BaseTool


PathLike = Union[str, Path]


class ToolLoader:
    """Loads tools from one or more tool directories."""

    def __init__(self, tools_dir: Union[PathLike, Sequence[PathLike]] = "user/tools"):
        """
        Initialize tool loader.

        Args:
            tools_dir: A single directory or an ordered list of directories
                containing tool modules. When a list is given, later directories
                override earlier ones for files with the same name (so the
                typical usage is ``[default_tools, project_tools]``).
        """
        if isinstance(tools_dir, (list, tuple)):
            self.tools_dirs: List[Path] = [Path(d) for d in tools_dir]
            self.tools_dir: Path = self.tools_dirs[-1] if self.tools_dirs else Path(".")
        else:
            self.tools_dir = Path(tools_dir)
            self.tools_dirs = [self.tools_dir]
        self._tools: Dict[str, BaseTool] = {}
        self._tool_sources: Dict[str, str] = {}  # tool_name -> source filename (without .py)
        self._tool_source_dirs: Dict[str, Path] = {}  # tool_name -> source directory

    def load_tools(self) -> Dict[str, BaseTool]:
        """
        Load all tools from the configured directories.

        When multiple directories are configured, a file in a later directory
        with the same name as one in an earlier directory fully replaces the
        earlier file (its tools are not loaded).

        Returns:
            Dictionary mapping tool names to tool instances
        """
        # Resolve which file wins for each stem (later dirs override earlier).
        file_map: Dict[str, Path] = {}
        for tdir in self.tools_dirs:
            if not tdir.exists():
                continue
            for tool_file in tdir.glob("*.py"):
                if tool_file.name.startswith("_"):
                    continue
                file_map[tool_file.stem] = tool_file

        for stem, tool_file in file_map.items():
            try:
                spec = importlib.util.spec_from_file_location(stem, tool_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for item_name in dir(module):
                    item = getattr(module, item_name)
                    if (inspect.isclass(item) and
                        issubclass(item, BaseTool) and
                        item is not BaseTool):
                        tool_instance = item()
                        self._tools[tool_instance.name] = tool_instance
                        self._tool_sources[tool_instance.name] = tool_file.stem
                        self._tool_source_dirs[tool_instance.name] = tool_file.parent

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

    def get_tool_source(self, name: str) -> str:
        """Get the source filename (without .py) for a tool."""
        return self._tool_sources.get(name, "")

    def get_tool_icon_path(self, name: str) -> Optional[Path]:
        """Return path to the tool's icon SVG (colocated with its .py source), or None if missing."""
        source = self._tool_sources.get(name)
        if not source:
            return None
        source_dir = self._tool_source_dirs.get(name, self.tools_dir)
        icon_path = source_dir / f"{source}.svg"
        return icon_path if icon_path.is_file() else None

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

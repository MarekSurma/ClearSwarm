"""
Directory create tool - creates directories in the output directory.
"""
import os
from multi_agent.tools.base import BaseTool


class DirectoryCreateTool(BaseTool):
    """Tool for creating directories recursively."""

    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")

    @property
    def name(self) -> str:
        return "directory_create"

    @property
    def description(self) -> str:
        return (
            "Creates a directory (and any necessary parent directories) inside the output directory. "
            "Works recursively - all intermediate directories are created automatically. "
            "A leading slash means the output directory is the root."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "directory_name": {
                    "type": "string",
                    "description": "Directory path to create (relative to output dir, leading slash is relative to output dir). Supports nested paths like 'a/b/c'."
                }
            },
            "required": ["directory_name"]
        }

    def _resolve_path(self, directory_name: str) -> str:
        """Resolve directory_name to an absolute path within the output directory."""
        directory_name = directory_name.lstrip("/")
        full_path = os.path.normpath(os.path.join(self.OUTPUT_DIR, directory_name))
        if not full_path.startswith(os.path.normpath(self.OUTPUT_DIR)):
            raise ValueError("Path escapes the output directory")
        return full_path

    def execute(self, directory_name: str) -> str:
        try:
            full_path = self._resolve_path(directory_name)
            if os.path.isdir(full_path):
                return f"Directory already exists: {directory_name}"
            os.makedirs(full_path, exist_ok=True)
            return f"Directory created successfully: {directory_name}"
        except Exception as e:
            return f"Error creating directory: {e}"

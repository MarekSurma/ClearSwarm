"""
File read tool - reads the full content of a file in the output directory.
"""
import os
from multi_agent.tools.base import BaseTool


class FileReadTool(BaseTool):
    """Tool for reading the full content of a file."""

    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return (
            "Reads the full content of a file in the output directory. "
            "The file_name can include subdirectory paths (e.g. 'subdir/file.txt'). "
            "A leading slash means the output directory is the root."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to read (can include subdirectory path, leading slash is relative to output dir)"
                }
            },
            "required": ["file_name"]
        }

    def _resolve_path(self, file_name: str) -> str:
        """Resolve file_name to an absolute path within the output directory."""
        file_name = file_name.lstrip("/")
        full_path = os.path.normpath(os.path.join(self.OUTPUT_DIR, file_name))
        if not full_path.startswith(os.path.normpath(self.OUTPUT_DIR)):
            raise ValueError("Path escapes the output directory")
        return full_path

    def execute(self, file_name: str) -> str:
        try:
            full_path = self._resolve_path(file_name)
            if not os.path.isfile(full_path):
                return f"Error: File not found: {file_name}"
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            return f"Error reading file: {e}"

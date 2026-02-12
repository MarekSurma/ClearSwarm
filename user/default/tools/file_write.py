"""
File write tool - writes content to a file in the output directory.
"""
import os
from multi_agent.tools.base import BaseTool


class FileWriteTool(BaseTool):
    """Tool for writing content to a file."""

    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return (
            "Writes content to a file in the output directory. "
            "The file_name can include subdirectory paths (e.g. 'subdir/file.txt'). "
            "A leading slash means the output directory is the root. "
            "Parent directories are created automatically if they don't exist."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to write (can include subdirectory path, leading slash is relative to output dir)"
                },
                "file_content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["file_name", "file_content"]
        }

    def _resolve_path(self, file_name: str) -> str:
        """Resolve file_name to an absolute path within the output directory."""
        file_name = file_name.lstrip("/")
        full_path = os.path.normpath(os.path.join(self.OUTPUT_DIR, file_name))
        if not full_path.startswith(os.path.normpath(self.OUTPUT_DIR)):
            raise ValueError("Path escapes the output directory")
        return full_path

    def execute(self, file_name: str, file_content: str) -> str:
        try:
            full_path = self._resolve_path(file_name)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(file_content)
            return f"File written successfully: {file_name}"
        except Exception as e:
            return f"Error writing file: {e}"

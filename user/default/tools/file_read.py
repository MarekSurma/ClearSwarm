"""
File read tool - reads the full content of a file in the project output directory.
Files are stored in output/<project_dir>/.
The project is determined automatically from the current session.
"""
import os
from multi_agent.tools.base import BaseTool

_ROOT_OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "output")


class FileReadTool(BaseTool):
    """Tool for reading the full content of a file."""

    def _get_output_dir(self) -> str:
        output_dir = os.path.join(_ROOT_OUTPUT, self.project_dir)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return (
            "Reads the full content of a file in the project output directory "
            "(output/<project>/). The file_name can include subdirectory paths "
            "(e.g. 'subdir/file.txt')."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to read (can include subdirectory path)"
                }
            },
            "required": ["file_name"]
        }

    def _resolve_path(self, file_name: str) -> str:
        """Resolve file_name to an absolute path within the project output directory."""
        output_dir = self._get_output_dir()
        file_name = file_name.lstrip("/")
        full_path = os.path.normpath(os.path.join(output_dir, file_name))
        if not full_path.startswith(os.path.normpath(output_dir)):
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

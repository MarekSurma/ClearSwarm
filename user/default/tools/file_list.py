"""
File list tool - lists files and directories in the project output directory.
Files are stored in output/<project_dir>/.
The project is determined automatically from the current session.
"""
import os
from multi_agent.tools.base import BaseTool

_ROOT_OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "output")


class FileListTool(BaseTool):
    """Tool for listing files and directories."""

    def _get_output_dir(self) -> str:
        output_dir = os.path.join(_ROOT_OUTPUT, self.project_dir)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    @property
    def name(self) -> str:
        return "file_list"

    @property
    def description(self) -> str:
        return (
            "Lists files and directories inside the project output directory "
            "(output/<project>/). Provide a subdirectory path to list its contents, "
            "or use '/' to list the project root output directory."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Subdirectory to list (relative to project output dir). Use '/' or empty string for the project root."
                }
            },
            "required": ["directory"]
        }

    def _resolve_path(self, directory: str) -> str:
        """Resolve directory to an absolute path within the project output directory."""
        output_dir = self._get_output_dir()
        directory = directory.lstrip("/")
        if not directory:
            return os.path.normpath(output_dir)
        full_path = os.path.normpath(os.path.join(output_dir, directory))
        if not full_path.startswith(os.path.normpath(output_dir)):
            raise ValueError("Path escapes the output directory")
        return full_path

    def execute(self, directory: str = "/") -> str:
        try:
            full_path = self._resolve_path(directory)
            if not os.path.isdir(full_path):
                return f"Error: Directory not found: {directory}"
            entries = sorted(os.listdir(full_path))
            if not entries:
                return f"Directory is empty: {directory}"
            result_lines = []
            for entry in entries:
                entry_path = os.path.join(full_path, entry)
                if os.path.isdir(entry_path):
                    result_lines.append(f"[DIR]  {entry}")
                else:
                    size = os.path.getsize(entry_path)
                    result_lines.append(f"[FILE] {entry} ({size} bytes)")
            return "\n".join(result_lines)
        except Exception as e:
            return f"Error listing directory: {e}"

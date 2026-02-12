"""
File list tool - lists files and directories in the output directory.
"""
import os
from multi_agent.tools.base import BaseTool


class FileListTool(BaseTool):
    """Tool for listing files and directories."""

    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")

    @property
    def name(self) -> str:
        return "file_list"

    @property
    def description(self) -> str:
        return (
            "Lists files and directories inside the output directory. "
            "Provide a subdirectory path to list its contents, or leave empty / use '/' to list the root output directory. "
            "A leading slash means the output directory is the root."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Subdirectory to list (relative to output dir, leading slash is relative to output dir). Use '/' or empty string for the root output directory."
                }
            },
            "required": ["directory"]
        }

    def _resolve_path(self, directory: str) -> str:
        """Resolve directory to an absolute path within the output directory."""
        directory = directory.lstrip("/")
        if not directory:
            return os.path.normpath(self.OUTPUT_DIR)
        full_path = os.path.normpath(os.path.join(self.OUTPUT_DIR, directory))
        if not full_path.startswith(os.path.normpath(self.OUTPUT_DIR)):
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

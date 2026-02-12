"""
File read rows tool - reads specific rows from a file in the output directory.
"""
import os
from multi_agent.tools.base import BaseTool


class FileReadRowsTool(BaseTool):
    """Tool for reading specific rows from a file."""

    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")

    @property
    def name(self) -> str:
        return "file_read_rows"

    @property
    def description(self) -> str:
        return (
            "Reads specific rows from a file in the output directory. "
            "Row numbers are 1-based. If the requested range exceeds the file size, "
            "it returns whatever rows are available within the range. "
            "The file_name can include subdirectory paths. "
            "A leading slash means the output directory is the root."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to read (can include subdirectory path, leading slash is relative to output dir)"
                },
                "row_from": {
                    "type": "integer",
                    "description": "Starting row number (1-based, inclusive)"
                },
                "row_to": {
                    "type": "integer",
                    "description": "Ending row number (1-based, inclusive)"
                }
            },
            "required": ["file_name", "row_from", "row_to"]
        }

    def _resolve_path(self, file_name: str) -> str:
        """Resolve file_name to an absolute path within the output directory."""
        file_name = file_name.lstrip("/")
        full_path = os.path.normpath(os.path.join(self.OUTPUT_DIR, file_name))
        if not full_path.startswith(os.path.normpath(self.OUTPUT_DIR)):
            raise ValueError("Path escapes the output directory")
        return full_path

    def execute(self, file_name: str, row_from: int, row_to: int) -> str:
        try:
            row_from = int(row_from)
            row_to = int(row_to)
            full_path = self._resolve_path(file_name)
            if not os.path.isfile(full_path):
                return f"Error: File not found: {file_name}"
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            total_lines = len(lines)
            start = max(row_from - 1, 0)
            end = min(row_to, total_lines)
            if start >= total_lines:
                return f"No rows to return. File has {total_lines} rows."
            selected = lines[start:end]
            return f"Rows {start + 1}-{start + len(selected)} of {total_lines}:\n" + "".join(selected)
        except Exception as e:
            return f"Error reading rows: {e}"

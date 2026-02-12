"""
File modify rows tool - replaces specific rows in a file in the output directory.
"""
import os
from multi_agent.tools.base import BaseTool


class FileModifyRowsTool(BaseTool):
    """Tool for modifying specific rows in a file."""

    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output")

    @property
    def name(self) -> str:
        return "file_modify_rows"

    @property
    def description(self) -> str:
        return (
            "Replaces specific rows in a file with new content. "
            "Row numbers are 1-based. The rows from row_from to row_to (inclusive) are replaced "
            "with the provided content. The new content can have a different number of lines than "
            "the range being replaced. "
            "The file_name can include subdirectory paths. "
            "A leading slash means the output directory is the root. "
            "IMPORTANT: When making multiple modifications to the same file in one batch, "
            "always apply changes from the END of the file toward the BEGINNING (i.e. highest "
            "row numbers first). Modifying in the opposite order (from the beginning toward the end) "
            "will shift line numbers after each change and corrupt subsequent modifications."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to modify (can include subdirectory path, leading slash is relative to output dir)"
                },
                "row_from": {
                    "type": "integer",
                    "description": "Starting row number to replace (1-based, inclusive)"
                },
                "row_to": {
                    "type": "integer",
                    "description": "Ending row number to replace (1-based, inclusive)"
                },
                "content": {
                    "type": "string",
                    "description": "New content to insert in place of the specified rows"
                }
            },
            "required": ["file_name", "row_from", "row_to", "content"]
        }

    def _resolve_path(self, file_name: str) -> str:
        """Resolve file_name to an absolute path within the output directory."""
        file_name = file_name.lstrip("/")
        full_path = os.path.normpath(os.path.join(self.OUTPUT_DIR, file_name))
        if not full_path.startswith(os.path.normpath(self.OUTPUT_DIR)):
            raise ValueError("Path escapes the output directory")
        return full_path

    def execute(self, file_name: str, row_from: int, row_to: int, content: str) -> str:
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
            new_lines = content.splitlines(True)
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            lines[start:end] = new_lines
            with open(full_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return f"Rows {row_from}-{row_to} replaced successfully. File now has {len(lines)} rows."
        except Exception as e:
            return f"Error modifying rows: {e}"

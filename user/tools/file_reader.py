"""
File reader tool for reading file contents.
"""
from pathlib import Path
from multi_agent.tools.base import BaseTool


class FileReaderTool(BaseTool):
    """Tool for reading file contents."""

    @property
    def name(self) -> str:
        return "file_reader"

    @property
    def description(self) -> str:
        return "Reads and returns the complete contents of a file"

    def get_parameters_schema(self):
        """Provide detailed parameter descriptions."""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read (relative or absolute)"
                }
            },
            "required": ["file_path"]
        }

    def execute(self, file_path: str) -> str:
        """
        Read file contents.

        Args:
            file_path: Path to the file to read

        Returns:
            File contents or error message
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return f"Error: File '{file_path}' does not exist"

            if not path.is_file():
                return f"Error: '{file_path}' is not a file"

            content = path.read_text(encoding='utf-8')
            return f"File contents of '{file_path}':\n\n{content}"

        except PermissionError:
            return f"Error: Permission denied reading '{file_path}'"
        except Exception as e:
            return f"Error reading file '{file_path}': {str(e)}"

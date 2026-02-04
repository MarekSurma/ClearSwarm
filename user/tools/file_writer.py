"""
File writer tool for writing text to files.
"""
from pathlib import Path
from multi_agent.tools.base import BaseTool


class FileWriterTool(BaseTool):
    """Tool for writing content to files."""

    @property
    def name(self) -> str:
        return "file_writer"

    @property
    def description(self) -> str:
        return "Writes text content to a file in the output directory"

    def get_parameters_schema(self):
        """Provide detailed parameter descriptions."""
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the file to create (will be saved in ./output/ directory)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["filename", "content"]
        }

    def execute(self, filename: str, content: str) -> str:
        """
        Write content to a file.

        Args:
            filename: Name of the file to write
            content: Content to write to the file

        Returns:
            Success or error message
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)

            # Write file
            file_path = output_dir / filename
            file_path.write_text(content, encoding='utf-8')

            return f"Successfully wrote to {file_path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"

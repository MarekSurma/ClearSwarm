"""
File creation tool for creating files safely.
"""
from pathlib import Path
from multi_agent.tools.base import BaseTool


class CreateFileTool(BaseTool):
    """Tool for creating files."""

    @property
    def name(self) -> str:
        return "create_file"

    @property
    def description(self) -> str:
        return "Creates a file at the specified path with optional content. Can create parent directories if they don't exist."

    def get_parameters_schema(self):
        """Provide detailed parameter descriptions."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to create (relative to project root or absolute)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file (optional, creates empty file if not provided)"
                },
                "create_parents": {
                    "type": "boolean",
                    "description": "Create parent directories if they don't exist (default: True)"
                }
            },
            "required": ["path"]
        }

    def execute(self, path: str, content: str = "", create_parents: bool = True) -> str:
        """
        Create a file with optional content.

        Args:
            path: Path to the file to create
            content: Content to write to the file (default: empty string)
            create_parents: Whether to create parent directories (default: True)

        Returns:
            Success or error message
        """
        try:
            # Convert to Path object
            file_path = Path(path)

            # Security check: resolve path and ensure it's valid
            try:
                resolved_path = file_path.resolve()
                project_root = Path.cwd().resolve()

                # Check if path is within project or is absolute path user intended
                # Allow both relative paths within project and absolute paths
                if not str(resolved_path).startswith(str(project_root)) and not file_path.is_absolute():
                    return f"Error: Path '{path}' resolves outside project directory"
            except Exception as e:
                return f"Error: Invalid path '{path}': {str(e)}"

            # Check if file already exists
            if file_path.exists():
                return f"Error: File already exists: {file_path}"

            # Create parent directories if needed
            if create_parents and not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create file with content
            file_path.write_text(content, encoding='utf-8')

            if content:
                return f"Successfully created file with content: {file_path}"
            else:
                return f"Successfully created empty file: {file_path}"

        except Exception as e:
            return f"Error creating file: {str(e)}"

"""
Directory creation tool for creating directories safely.
"""
from pathlib import Path
from multi_agent.tools.base import BaseTool


class CreateDirectoryTool(BaseTool):
    """Tool for creating directories."""

    @property
    def name(self) -> str:
        return "create_directory"

    @property
    def description(self) -> str:
        return "Creates a directory at the specified path. Supports creating parent directories if they don't exist."

    def get_parameters_schema(self):
        """Provide detailed parameter descriptions."""
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the directory to create (relative to project root or absolute)"
                },
                "parents": {
                    "type": "boolean",
                    "description": "Create parent directories if they don't exist (default: True)"
                }
            },
            "required": ["path"]
        }

    def execute(self, path: str, parents: bool = True) -> str:
        """
        Create a directory.

        Args:
            path: Path to the directory to create
            parents: Whether to create parent directories (default: True)

        Returns:
            Success or error message
        """
        try:
            # Convert to Path object
            dir_path = Path(path)

            # Security check: resolve path and ensure it's not trying to escape
            try:
                resolved_path = dir_path.resolve()
                project_root = Path.cwd().resolve()

                # Check if path is within project or is absolute path user intended
                # Allow both relative paths within project and absolute paths
                if not str(resolved_path).startswith(str(project_root)) and not dir_path.is_absolute():
                    return f"Error: Path '{path}' resolves outside project directory"
            except Exception as e:
                return f"Error: Invalid path '{path}': {str(e)}"

            # Create directory
            if dir_path.exists():
                if dir_path.is_dir():
                    return f"Directory already exists: {dir_path}"
                else:
                    return f"Error: Path exists but is not a directory: {dir_path}"

            dir_path.mkdir(parents=parents, exist_ok=False)
            return f"Successfully created directory: {dir_path}"

        except Exception as e:
            return f"Error creating directory: {str(e)}"

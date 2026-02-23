"""
Directory create tool - creates directories in the project output directory.
Directories are created in output/<project_dir>/.
The project is determined automatically from the current session.
"""
import os
from multi_agent.tools.base import BaseTool

_ROOT_OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "output")


class DirectoryCreateTool(BaseTool):
    """Tool for creating directories recursively."""

    def _get_output_dir(self) -> str:
        output_dir = os.path.join(_ROOT_OUTPUT, self.project_dir)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    @property
    def name(self) -> str:
        return "directory_create"

    @property
    def description(self) -> str:
        return (
            "Creates a directory (and any necessary parent directories) inside "
            "the project output directory (output/<project>/). "
            "Works recursively - all intermediate directories are created automatically. "
            "Supports nested paths like 'a/b/c'."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "directory_name": {
                    "type": "string",
                    "description": "Directory path to create (relative to project output dir). Supports nested paths like 'a/b/c'."
                }
            },
            "required": ["directory_name"]
        }

    def _resolve_path(self, directory_name: str) -> str:
        """Resolve directory_name to an absolute path within the project output directory."""
        output_dir = self._get_output_dir()
        directory_name = directory_name.lstrip("/")
        full_path = os.path.normpath(os.path.join(output_dir, directory_name))
        if not full_path.startswith(os.path.normpath(output_dir)):
            raise ValueError("Path escapes the output directory")
        return full_path

    def execute(self, directory_name: str) -> str:
        try:
            full_path = self._resolve_path(directory_name)
            if os.path.isdir(full_path):
                return f"Directory already exists: {directory_name}"
            os.makedirs(full_path, exist_ok=True)
            return f"Directory created successfully: {directory_name}"
        except Exception as e:
            return f"Error creating directory: {e}"

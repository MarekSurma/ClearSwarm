"""
File manipulation tools for the multi-agent system.
All file operations work within the project output directory: output/<project_dir>/.

The project_name is automatically injected by the agent framework via
BaseTool.set_context() — agents do NOT need to pass it as a parameter.
"""
import os

from multi_agent.tools.base import BaseTool

_ROOT_OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "output",
)


class _FileToolMixin:
    """Shared helpers for all file tools (not a BaseTool itself, so the loader skips it)."""

    def _get_output_dir(self) -> str:
        output_dir = os.path.join(_ROOT_OUTPUT, self.project_dir)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def _resolve_path(self, name: str) -> str:
        """Resolve a relative name to an absolute path inside the project output dir."""
        output_dir = self._get_output_dir()
        name = name.lstrip("/")
        full_path = os.path.normpath(os.path.join(output_dir, name))
        if not full_path.startswith(os.path.normpath(output_dir)):
            raise ValueError("Path escapes the output directory")
        return full_path


# ---------------------------------------------------------------------------
# file_list
# ---------------------------------------------------------------------------
class FileListTool(_FileToolMixin, BaseTool):
    """Tool for listing files and directories."""

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
                    "description": "Subdirectory to list (relative to project output dir). Use '/' or empty string for the project root.",
                }
            },
            "required": ["directory"],
        }

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


# ---------------------------------------------------------------------------
# file_read
# ---------------------------------------------------------------------------
class FileReadTool(_FileToolMixin, BaseTool):
    """Tool for reading the full content of a file."""

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
                    "description": "Name of the file to read (can include subdirectory path)",
                }
            },
            "required": ["file_name"],
        }

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


# ---------------------------------------------------------------------------
# file_read_rows
# ---------------------------------------------------------------------------
class FileReadRowsTool(_FileToolMixin, BaseTool):
    """Tool for reading specific rows from a file."""

    @property
    def name(self) -> str:
        return "file_read_rows"

    @property
    def description(self) -> str:
        return (
            "Reads specific rows from a file in the project output directory "
            "(output/<project>/). Row numbers are 1-based. If the requested range "
            "exceeds the file size, it returns whatever rows are available. "
            "The file_name can include subdirectory paths."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to read (can include subdirectory path)",
                },
                "row_from": {
                    "type": "integer",
                    "description": "Starting row number (1-based, inclusive)",
                },
                "row_to": {
                    "type": "integer",
                    "description": "Ending row number (1-based, inclusive)",
                },
            },
            "required": ["file_name", "row_from", "row_to"],
        }

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


# ---------------------------------------------------------------------------
# file_write
# ---------------------------------------------------------------------------
class FileWriteTool(_FileToolMixin, BaseTool):
    """Tool for writing content to a file."""

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return (
            "Writes content to a file in the project output directory "
            "(output/<project>/). The file_name can include subdirectory paths "
            "(e.g. 'subdir/file.txt'). Parent directories are created automatically."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to write (can include subdirectory path)",
                },
                "file_content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["file_name", "file_content"],
        }

    def execute(self, file_name: str, file_content: str) -> str:
        try:
            full_path = self._resolve_path(file_name)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(file_content)
            return f"File written successfully: {file_name}"
        except Exception as e:
            return f"Error writing file: {e}"


# ---------------------------------------------------------------------------
# file_modify_rows
# ---------------------------------------------------------------------------
class FileModifyRowsTool(_FileToolMixin, BaseTool):
    """Tool for modifying specific rows in a file."""

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
            "IMPORTANT: When making multiple modifications to the same file in one batch, "
            "always apply changes from the END of the file toward the BEGINNING (i.e. highest "
            "row numbers first). Modifying in the opposite order will shift line numbers and "
            "corrupt subsequent modifications."
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "Name of the file to modify (can include subdirectory path)",
                },
                "row_from": {
                    "type": "integer",
                    "description": "Starting row number to replace (1-based, inclusive)",
                },
                "row_to": {
                    "type": "integer",
                    "description": "Ending row number to replace (1-based, inclusive)",
                },
                "content": {
                    "type": "string",
                    "description": "New content to insert in place of the specified rows",
                },
            },
            "required": ["file_name", "row_from", "row_to", "content"],
        }

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


# ---------------------------------------------------------------------------
# directory_create
# ---------------------------------------------------------------------------
class DirectoryCreateTool(_FileToolMixin, BaseTool):
    """Tool for creating directories recursively."""

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
                    "description": "Directory path to create (relative to project output dir). Supports nested paths like 'a/b/c'.",
                }
            },
            "required": ["directory_name"],
        }

    def execute(self, directory_name: str) -> str:
        try:
            full_path = self._resolve_path(directory_name)
            if os.path.isdir(full_path):
                return f"Directory already exists: {directory_name}"
            os.makedirs(full_path, exist_ok=True)
            return f"Directory created successfully: {directory_name}"
        except Exception as e:
            return f"Error creating directory: {e}"

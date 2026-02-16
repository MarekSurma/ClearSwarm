"""
Notes tool for saving and reading agent notes.
Notes are stored per-project in output/<project_name>/notes.txt
"""
import os
from datetime import datetime
from pathlib import Path

from multi_agent.tools.base import BaseTool


class NotesWriteTool(BaseTool):
    """Tool for writing notes to a project notebook."""

    @property
    def name(self) -> str:
        return "notes_write"

    @property
    def description(self) -> str:
        return "Writes a note to the project notebook file (output/<project_name>/notes.txt). Each note is timestamped automatically."

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the active project (directory name)"
                },
                "note": {
                    "type": "string",
                    "description": "The note content to write"
                }
            },
            "required": ["project_name", "note"]
        }

    def execute(self, project_name: str, note: str) -> str:
        try:
            notes_dir = Path("output") / project_name
            notes_dir.mkdir(parents=True, exist_ok=True)
            notes_file = notes_dir / "notes.txt"

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"[{timestamp}] {note}\n"

            with open(notes_file, "a", encoding="utf-8") as f:
                f.write(entry)

            return f"Note saved to {notes_file}"
        except Exception as e:
            return f"Error writing note: {e}"


class NotesReadTool(BaseTool):
    """Tool for reading all notes from a project notebook."""

    @property
    def name(self) -> str:
        return "notes_read"

    @property
    def description(self) -> str:
        return "Reads all notes from the project notebook file (output/<project_name>/notes.txt)."

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the active project (directory name)"
                }
            },
            "required": ["project_name"]
        }

    def execute(self, project_name: str) -> str:
        try:
            notes_file = Path("output") / project_name / "notes.txt"

            if not notes_file.exists():
                return f"No notes found for project '{project_name}'. File {notes_file} does not exist."

            with open(notes_file, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                return f"Notes file for project '{project_name}' is empty."

            return content
        except Exception as e:
            return f"Error reading notes: {e}"

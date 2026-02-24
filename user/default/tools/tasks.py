"""
Tasks tool for managing task files with file-level locking.
Tasks are stored in output/<project_name>/tasks/ as numbered .txt files.
Uses fcntl.flock for blocking exclusive locks to ensure process safety.

The project_name is automatically injected by the agent framework via
BaseTool.set_context() — agents do NOT need to pass it as a parameter.
"""
import fcntl
import os
import re
from contextlib import contextmanager
from pathlib import Path

from multi_agent.tools.base import BaseTool

VALID_STATUSES = ["todo", "in_progress", "needs_clarifications", "completed"]
STATUSES_DESC = "Available statuses: todo, in_progress, needs_clarifications, completed"


def _tasks_dir(project_name: str) -> Path:
    return Path("output") / project_name / "tasks"


@contextmanager
def _lock_tasks(project_name: str):
    """Acquire an exclusive blocking file lock on the tasks directory."""
    tasks_path = _tasks_dir(project_name)
    tasks_path.mkdir(parents=True, exist_ok=True)
    lock_file = tasks_path / ".tasks.lock"
    fd = open(lock_file, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield tasks_path
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()


def _find_next_number(tasks_path: Path) -> int:
    """Find the highest existing task number and return next one."""
    max_num = 0
    for f in tasks_path.glob("[0-9][0-9][0-9][0-9].txt"):
        match = re.match(r"^(\d{4})\.txt$", f.name)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return max_num + 1


def _task_file(tasks_path: Path, number: int) -> Path:
    return tasks_path / f"{number:04d}.txt"


def _parse_number(number) -> int:
    return int(number)


class TaskCreateTool(BaseTool):
    @property
    def name(self) -> str:
        return "task_create"

    @property
    def description(self) -> str:
        return (
            "Creates a new task file with auto-incremented 4-digit number "
            "(e.g. 0001.txt, 0002.txt). The file contains: title (line 1), "
            "status [todo] (line 2), content (line 3+). Returns the task number. "
            "The project is determined automatically from the current session. "
            f"{STATUSES_DESC}"
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the task (first line of the file)"
                },
                "content": {
                    "type": "string",
                    "description": "Content/body of the task (third line onward)"
                }
            },
            "required": ["title", "content"]
        }

    def execute(self, title: str, content: str) -> str:
        try:
            with _lock_tasks(self.project_dir) as tasks_path:
                next_num = _find_next_number(tasks_path)
                task_path = _task_file(tasks_path, next_num)
                file_content = f"{title}\n[todo]\n{content}"
                with open(task_path, "w", encoding="utf-8") as f:
                    f.write(file_content)
                return f"Task {next_num:04d} created successfully."
        except Exception as e:
            return f"Error creating task: {e}"


class TaskReadTool(BaseTool):
    @property
    def name(self) -> str:
        return "task_read"

    @property
    def description(self) -> str:
        return (
            "Reads a task file by its number and returns the full content. "
            f"{STATUSES_DESC}"
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "number": {
                    "type": "integer",
                    "description": "Task number (e.g. 1 for 0001.txt)"
                }
            },
            "required": ["number"]
        }

    def execute(self, number: int) -> str:
        try:
            num = _parse_number(number)
            with _lock_tasks(self.project_dir) as tasks_path:
                task_path = _task_file(tasks_path, num)
                if not task_path.exists():
                    return f"Task {num:04d} not found."
                with open(task_path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            return f"Error reading task: {e}"


class TaskListTool(BaseTool):
    @property
    def name(self) -> str:
        return "task_list"

    @property
    def description(self) -> str:
        return (
            "Lists all tasks with their number, title, and status (without content). "
            "Returns lines in format: '0001 [todo] - Task title'. "
            "Use task_read to get full content of a specific task. "
            f"{STATUSES_DESC}"
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": f"Optional: filter by status. {STATUSES_DESC}",
                    "enum": VALID_STATUSES
                }
            },
            "required": []
        }

    def execute(self, status: str = None) -> str:
        try:
            with _lock_tasks(self.project_dir) as tasks_path:
                results = []
                files = sorted(tasks_path.glob("[0-9][0-9][0-9][0-9].txt"))
                for task_file in files:
                    match = re.match(r"^(\d{4})\.txt$", task_file.name)
                    if not match:
                        continue
                    num = match.group(1)
                    with open(task_file, "r", encoding="utf-8") as f:
                        first_line = f.readline().strip()
                        second_line = f.readline().strip()
                    task_status = second_line.strip("[]") if second_line else "unknown"
                    if status and task_status != status:
                        continue
                    results.append(f"{num} [{task_status}] - {first_line}")
                if not results:
                    if status:
                        return f"No tasks found with status [{status}]."
                    return "No tasks found."
                return "\n".join(results)
        except Exception as e:
            return f"Error listing tasks: {e}"


class TaskCommentAddTool(BaseTool):
    @property
    def name(self) -> str:
        return "task_comment_add"

    @property
    def description(self) -> str:
        return (
            "Adds a comment to a task file. The comment is appended at the end "
            "with format: '---\\nagent_name powiedział: comment'. "
            f"{STATUSES_DESC}"
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "number": {
                    "type": "integer",
                    "description": "Task number (e.g. 1 for 0001.txt)"
                },
                "agent_name": {
                    "type": "string",
                    "description": "Name of the agent adding the comment"
                },
                "comment": {
                    "type": "string",
                    "description": "Comment content to add"
                }
            },
            "required": ["number", "agent_name", "comment"]
        }

    def execute(self, number: int, agent_name: str, comment: str) -> str:
        try:
            num = _parse_number(number)
            with _lock_tasks(self.project_dir) as tasks_path:
                task_path = _task_file(tasks_path, num)
                if not task_path.exists():
                    return f"Task {num:04d} not found."
                with open(task_path, "a", encoding="utf-8") as f:
                    f.write(f"\n---\n{agent_name} powiedział: {comment}")
                return f"Comment added to task {num:04d}."
        except Exception as e:
            return f"Error adding comment: {e}"


class TaskSearchByTitleTool(BaseTool):
    @property
    def name(self) -> str:
        return "task_search_by_title"

    @property
    def description(self) -> str:
        return (
            "Searches tasks by title (case-insensitive). Returns matching tasks "
            "in format: '0002 - task title\\n0100 - another task'. "
            f"{STATUSES_DESC}"
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Search string to find in task titles (case-insensitive)"
                }
            },
            "required": ["title"]
        }

    def execute(self, title: str) -> str:
        try:
            with _lock_tasks(self.project_dir) as tasks_path:
                results = []
                files = sorted(tasks_path.glob("[0-9][0-9][0-9][0-9].txt"))
                for task_file in files:
                    match = re.match(r"^(\d{4})\.txt$", task_file.name)
                    if not match:
                        continue
                    num = match.group(1)
                    with open(task_file, "r", encoding="utf-8") as f:
                        first_line = f.readline().strip()
                    if title.lower() in first_line.lower():
                        results.append(f"{num} - {first_line}")
                if not results:
                    return "No tasks found matching the given title."
                return "\n".join(results)
        except Exception as e:
            return f"Error searching tasks: {e}"


class TaskSetStatusTool(BaseTool):
    @property
    def name(self) -> str:
        return "task_set_status"

    @property
    def description(self) -> str:
        return (
            "Sets the status of a task. "
            f"{STATUSES_DESC}"
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "number": {
                    "type": "integer",
                    "description": "Task number (e.g. 1 for 0001.txt)"
                },
                "status": {
                    "type": "string",
                    "description": f"New status to set. {STATUSES_DESC}",
                    "enum": VALID_STATUSES
                }
            },
            "required": ["number", "status"]
        }

    def execute(self, number: int, status: str) -> str:
        try:
            if status not in VALID_STATUSES:
                return f"Invalid status '{status}'. {STATUSES_DESC}"
            num = _parse_number(number)
            with _lock_tasks(self.project_dir) as tasks_path:
                task_path = _task_file(tasks_path, num)
                if not task_path.exists():
                    return f"Task {num:04d} not found."
                with open(task_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if len(lines) < 2:
                    return f"Task {num:04d} has invalid format (missing status line)."
                lines[1] = f"[{status}]\n"
                with open(task_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                return f"Task {num:04d} status set to [{status}]."
        except Exception as e:
            return f"Error setting status: {e}"


class TaskPickUpFirstByStatusTool(BaseTool):
    @property
    def name(self) -> str:
        return "task_pick_up_first_by_status"

    @property
    def description(self) -> str:
        return (
            "Finds the first task with the given status, changes its status to "
            "[in_progress], and returns its number and full content. "
            f"{STATUSES_DESC}"
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": f"Status to search for. {STATUSES_DESC}",
                    "enum": VALID_STATUSES
                }
            },
            "required": ["status"]
        }

    def execute(self, status: str) -> str:
        try:
            if status not in VALID_STATUSES:
                return f"Invalid status '{status}'. {STATUSES_DESC}"
            with _lock_tasks(self.project_dir) as tasks_path:
                files = sorted(tasks_path.glob("[0-9][0-9][0-9][0-9].txt"))
                for task_file in files:
                    match = re.match(r"^(\d{4})\.txt$", task_file.name)
                    if not match:
                        continue
                    num = int(match.group(1))
                    with open(task_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    if len(lines) < 2:
                        continue
                    current_status = lines[1].strip().strip("[]")
                    if current_status == status:
                        lines[1] = "[in_progress]\n"
                        with open(task_file, "w", encoding="utf-8") as f:
                            f.writelines(lines)
                        content = "".join(lines)
                        return f"Task {num:04d} picked up.\n\n{content}"
                return f"No tasks found with status [{status}]."
        except Exception as e:
            return f"Error picking up task: {e}"


class TaskPickUpByNumberTool(BaseTool):
    @property
    def name(self) -> str:
        return "task_pick_up_by_number"

    @property
    def description(self) -> str:
        return (
            "Picks up a specific task by its number, changes its status to "
            "[in_progress], and returns its full content. "
            f"{STATUSES_DESC}"
        )

    def get_parameters_schema(self):
        return {
            "type": "object",
            "properties": {
                "number": {
                    "type": "integer",
                    "description": "Task number (e.g. 1 for 0001.txt)"
                }
            },
            "required": ["number"]
        }

    def execute(self, number: int) -> str:
        try:
            num = _parse_number(number)
            with _lock_tasks(self.project_dir) as tasks_path:
                task_path = _task_file(tasks_path, num)
                if not task_path.exists():
                    return f"Task {num:04d} not found."
                with open(task_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if len(lines) < 2:
                    return f"Task {num:04d} has invalid format (missing status line)."
                lines[1] = "[in_progress]\n"
                with open(task_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                content = "".join(lines)
                return f"Task {num:04d} picked up.\n\n{content}"
        except Exception as e:
            return f"Error picking up task: {e}"

"""
Database module for tracking agent execution.
Uses SQLite to store agent execution history.
"""
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import contextmanager


class AgentDatabase:
    """Manages SQLite database for agent tracking."""

    def __init__(self, db_path: str = "agents.db"):
        """Initialize database connection."""
        self.db_path = Path(db_path)
        self._init_database()

    def _init_database(self):
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_name TEXT NOT NULL UNIQUE,
                    project_dir TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
            """)

            # Agent executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_executions (
                    agent_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    parent_agent_id TEXT,
                    parent_agent_name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    current_state TEXT DEFAULT 'generating',
                    call_mode TEXT DEFAULT 'synchronous',
                    log_file TEXT
                )
            """)

            # Tool executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_executions (
                    tool_execution_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    call_mode TEXT DEFAULT 'synchronous',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    result TEXT,
                    FOREIGN KEY (agent_id) REFERENCES agent_executions (agent_id)
                )
            """)

            # Schedules table for cyclic agent execution
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    schedule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    project_dir TEXT NOT NULL DEFAULT 'default',
                    agent_name TEXT NOT NULL,
                    message TEXT NOT NULL DEFAULT '',
                    schedule_type TEXT NOT NULL,
                    interval_value INTEGER NOT NULL,
                    start_from TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_run_at TEXT,
                    next_run_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Add current_state column if it doesn't exist (migration)
            cursor.execute("PRAGMA table_info(agent_executions)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'current_state' not in columns:
                cursor.execute("ALTER TABLE agent_executions ADD COLUMN current_state TEXT DEFAULT 'generating'")

            # Add call_mode column to tool_executions if it doesn't exist (migration)
            cursor.execute("PRAGMA table_info(tool_executions)")
            tool_columns = [col[1] for col in cursor.fetchall()]
            if 'call_mode' not in tool_columns:
                cursor.execute("ALTER TABLE tool_executions ADD COLUMN call_mode TEXT DEFAULT 'synchronous'")

            # Add call_mode column to agent_executions if it doesn't exist (migration)
            cursor.execute("PRAGMA table_info(agent_executions)")
            agent_columns = [col[1] for col in cursor.fetchall()]
            if 'call_mode' not in agent_columns:
                cursor.execute("ALTER TABLE agent_executions ADD COLUMN call_mode TEXT DEFAULT 'synchronous'")

            # Add log_file column to agent_executions if it doesn't exist (migration)
            cursor.execute("PRAGMA table_info(agent_executions)")
            agent_columns = [col[1] for col in cursor.fetchall()]
            if 'log_file' not in agent_columns:
                cursor.execute("ALTER TABLE agent_executions ADD COLUMN log_file TEXT")

            # Add project_dir column to agent_executions if it doesn't exist (migration)
            cursor.execute("PRAGMA table_info(agent_executions)")
            agent_columns = [col[1] for col in cursor.fetchall()]
            if 'project_dir' not in agent_columns:
                cursor.execute("ALTER TABLE agent_executions ADD COLUMN project_dir TEXT DEFAULT 'default'")

            # Seed default project if not exists
            cursor.execute("SELECT COUNT(*) FROM projects WHERE project_name = 'default'")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO projects (project_name, project_dir, created_at)
                    VALUES (?, ?, ?)
                """, ("default", "default", datetime.now().isoformat()))

            conn.commit()

        # Enable WAL mode for better concurrent write performance
        self._enable_wal_mode()

    def _enable_wal_mode(self):
        """Enable Write-Ahead Logging mode for better concurrency."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def create_agent_execution(
        self,
        agent_name: str,
        parent_agent_id: Optional[str] = None,
        parent_agent_name: str = "root",
        call_mode: str = "synchronous",
        project_dir: str = "default"
    ) -> str:
        """
        Create a new agent execution record.

        Args:
            agent_name: Name of the agent being executed
            parent_agent_id: ID of parent agent (None if root)
            parent_agent_name: Name of parent agent ("root" if no parent)
            call_mode: Execution mode ('synchronous' or 'asynchronous')
            project_dir: Project directory for this execution

        Returns:
            agent_id: Unique identifier for this execution
        """
        agent_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_executions
                (agent_id, agent_name, parent_agent_id, parent_agent_name, started_at, completed_at, call_mode, project_dir)
                VALUES (?, ?, ?, ?, ?, NULL, ?, ?)
            """, (agent_id, agent_name, parent_agent_id, parent_agent_name, started_at, call_mode, project_dir))
            conn.commit()

        return agent_id

    def complete_agent_execution(self, agent_id: str):
        """
        Mark an agent execution as completed.

        Args:
            agent_id: ID of the agent execution to complete
        """
        completed_at = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_executions
                SET completed_at = ?, current_state = 'completed'
                WHERE agent_id = ?
            """, (completed_at, agent_id))
            conn.commit()

    def update_log_file(self, agent_id: str, log_file: str):
        """
        Update the log file path for an agent execution.

        Args:
            agent_id: ID of the agent execution
            log_file: Path to the log file
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_executions
                SET log_file = ?
                WHERE agent_id = ?
            """, (log_file, agent_id))
            conn.commit()

    def get_agent_execution(self, agent_id: str) -> Optional[dict]:
        """
        Get agent execution details.

        Args:
            agent_id: ID of the agent execution

        Returns:
            Dictionary with execution details or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_id, agent_name, parent_agent_id, parent_agent_name,
                       started_at, completed_at, log_file, project_dir
                FROM agent_executions
                WHERE agent_id = ?
            """, (agent_id,))
            row = cursor.fetchone()

            if row:
                return {
                    'agent_id': row[0],
                    'agent_name': row[1],
                    'parent_agent_id': row[2],
                    'parent_agent_name': row[3],
                    'started_at': row[4],
                    'completed_at': row[5],
                    'log_file': row[6],
                    'project_dir': row[7] if len(row) > 7 else 'default'
                }
            return None

    def get_all_executions(self, project_dir: Optional[str] = None) -> List[Dict]:
        """
        Get all agent executions, optionally filtered by project.

        Args:
            project_dir: Optional project directory to filter by

        Returns:
            List of agent execution dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if project_dir:
                cursor.execute("""
                    SELECT agent_id, agent_name, parent_agent_id, parent_agent_name,
                           started_at, completed_at, current_state, call_mode, log_file, project_dir
                    FROM agent_executions
                    WHERE project_dir = ?
                    ORDER BY started_at DESC
                """, (project_dir,))
            else:
                cursor.execute("""
                    SELECT agent_id, agent_name, parent_agent_id, parent_agent_name,
                           started_at, completed_at, current_state, call_mode, log_file, project_dir
                    FROM agent_executions
                    ORDER BY started_at DESC
                """)

            rows = cursor.fetchall()

            return [
                {
                    'agent_id': row[0],
                    'agent_name': row[1],
                    'parent_agent_id': row[2],
                    'parent_agent_name': row[3],
                    'started_at': row[4],
                    'completed_at': row[5],
                    'current_state': row[6] if len(row) > 6 else 'generating',
                    'call_mode': row[7] if len(row) > 7 else 'synchronous',
                    'log_file': row[8] if len(row) > 8 else None,
                    'project_dir': row[9] if len(row) > 9 else 'default'
                }
                for row in rows
            ]

    def update_agent_state(self, agent_id: str, state: str):
        """
        Update agent's current state.

        Args:
            agent_id: ID of the agent
            state: New state ('generating', 'waiting', 'executing_tool')
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE agent_executions
                SET current_state = ?
                WHERE agent_id = ?
            """, (state, agent_id))
            conn.commit()

    def create_tool_execution(
        self,
        agent_id: str,
        tool_name: str,
        parameters: dict,
        call_mode: str = 'synchronous'
    ) -> str:
        """
        Create a new tool execution record.

        Args:
            agent_id: ID of the agent executing the tool
            tool_name: Name of the tool being executed
            parameters: Tool parameters as dict
            call_mode: Execution mode ('synchronous' or 'asynchronous')

        Returns:
            tool_execution_id: Unique identifier for this tool execution
        """
        import json
        tool_execution_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()
        parameters_json = json.dumps(parameters, ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tool_executions
                (tool_execution_id, agent_id, tool_name, parameters, call_mode, started_at, completed_at, result)
                VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
            """, (tool_execution_id, agent_id, tool_name, parameters_json, call_mode, started_at))
            conn.commit()

        return tool_execution_id

    def complete_tool_execution(self, tool_execution_id: str, result: str):
        """
        Mark a tool execution as completed.

        Args:
            tool_execution_id: ID of the tool execution
            result: Result of the tool execution
        """
        completed_at = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tool_executions
                SET completed_at = ?, result = ?
                WHERE tool_execution_id = ?
            """, (completed_at, result, tool_execution_id))
            conn.commit()

    def get_tool_executions(self, agent_id: str) -> List[Dict]:
        """
        Get all tool executions for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            List of tool execution dictionaries
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tool_execution_id, tool_name, parameters, call_mode, started_at, completed_at, result
                FROM tool_executions
                WHERE agent_id = ?
                ORDER BY started_at ASC
            """, (agent_id,))
            rows = cursor.fetchall()

            return [
                {
                    'tool_execution_id': row[0],
                    'tool_name': row[1],
                    'parameters': json.loads(row[2]) if row[2] else {},
                    'call_mode': row[3] if len(row) > 3 and row[3] else 'synchronous',
                    'started_at': row[4] if len(row) > 4 else row[3],
                    'completed_at': row[5] if len(row) > 5 else row[4],
                    'result': row[6] if len(row) > 6 else row[5],
                    'is_running': (row[5] if len(row) > 5 else row[4]) is None
                }
                for row in rows
            ]

    def create_project(self, project_name: str, project_dir: str) -> None:
        """
        Create a new project.

        Args:
            project_name: Display name of the project
            project_dir: Directory name for the project

        Raises:
            ValueError: If project already exists
        """
        created_at = datetime.now().isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO projects (project_name, project_dir, created_at)
                    VALUES (?, ?, ?)
                """, (project_name, project_dir, created_at))
                conn.commit()
        except sqlite3.IntegrityError as e:
            raise ValueError(f"Project '{project_name}' or directory '{project_dir}' already exists") from e

    def get_all_projects(self) -> List[Dict]:
        """
        Get all projects.

        Returns:
            List of project dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT project_name, project_dir, created_at
                FROM projects
                ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()

            return [
                {
                    'project_name': row[0],
                    'project_dir': row[1],
                    'created_at': row[2]
                }
                for row in rows
            ]

    def get_project_by_name(self, project_name: str) -> Optional[Dict]:
        """
        Get a project by name.

        Args:
            project_name: Name of the project

        Returns:
            Project dictionary or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT project_name, project_dir, created_at
                FROM projects
                WHERE project_name = ?
            """, (project_name,))
            row = cursor.fetchone()

            if row:
                return {
                    'project_name': row[0],
                    'project_dir': row[1],
                    'created_at': row[2]
                }
            return None

    def delete_project(self, project_name: str) -> None:
        """
        Delete a project.

        Args:
            project_name: Name of the project to delete

        Raises:
            ValueError: If trying to delete the default project or project not found
        """
        if project_name == "default":
            raise ValueError("Cannot delete the default project")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM projects
                WHERE project_name = ?
            """, (project_name,))

            if cursor.rowcount == 0:
                raise ValueError(f"Project '{project_name}' not found")

            conn.commit()

    def create_schedule(
        self,
        name: str,
        project_dir: str,
        agent_name: str,
        message: str,
        schedule_type: str,
        interval_value: int,
        start_from: Optional[str] = None,
        enabled: bool = True
    ) -> dict:
        """
        Create a new schedule.

        Args:
            name: Name of the schedule
            project_dir: Project directory
            agent_name: Name of the agent to run
            message: Message to send to the agent
            schedule_type: Type of schedule ('minutes', 'hours', 'weeks')
            interval_value: Interval value (how many minutes/hours/weeks)
            start_from: ISO datetime to start from (None = now)
            enabled: Whether schedule is enabled

        Returns:
            Dictionary with created schedule details
        """
        schedule_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Calculate next run time
        next_run_at = self._calculate_next_run(
            schedule_type, interval_value, start_from, None, now
        )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO schedules
                (schedule_id, name, project_dir, agent_name, message, schedule_type,
                 interval_value, start_from, enabled, last_run_at, next_run_at,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
            """, (
                schedule_id, name, project_dir, agent_name, message, schedule_type,
                interval_value, start_from, 1 if enabled else 0, next_run_at, now, now
            ))
            conn.commit()

        return self.get_schedule(schedule_id)

    def get_schedule(self, schedule_id: str) -> Optional[dict]:
        """
        Get a schedule by ID.

        Args:
            schedule_id: ID of the schedule

        Returns:
            Dictionary with schedule details or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT schedule_id, name, project_dir, agent_name, message,
                       schedule_type, interval_value, start_from, enabled,
                       last_run_at, next_run_at, created_at, updated_at
                FROM schedules
                WHERE schedule_id = ?
            """, (schedule_id,))
            row = cursor.fetchone()

            if row:
                return {
                    'schedule_id': row[0],
                    'name': row[1],
                    'project_dir': row[2],
                    'agent_name': row[3],
                    'message': row[4],
                    'schedule_type': row[5],
                    'interval_value': row[6],
                    'start_from': row[7],
                    'enabled': bool(row[8]),
                    'last_run_at': row[9],
                    'next_run_at': row[10],
                    'created_at': row[11],
                    'updated_at': row[12]
                }
            return None

    def get_all_schedules(self, project_dir: Optional[str] = None) -> List[dict]:
        """
        Get all schedules, optionally filtered by project.

        Args:
            project_dir: Optional project directory to filter by

        Returns:
            List of schedule dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if project_dir:
                cursor.execute("""
                    SELECT schedule_id, name, project_dir, agent_name, message,
                           schedule_type, interval_value, start_from, enabled,
                           last_run_at, next_run_at, created_at, updated_at
                    FROM schedules
                    WHERE project_dir = ?
                    ORDER BY created_at DESC
                """, (project_dir,))
            else:
                cursor.execute("""
                    SELECT schedule_id, name, project_dir, agent_name, message,
                           schedule_type, interval_value, start_from, enabled,
                           last_run_at, next_run_at, created_at, updated_at
                    FROM schedules
                    ORDER BY created_at DESC
                """)

            rows = cursor.fetchall()

            return [
                {
                    'schedule_id': row[0],
                    'name': row[1],
                    'project_dir': row[2],
                    'agent_name': row[3],
                    'message': row[4],
                    'schedule_type': row[5],
                    'interval_value': row[6],
                    'start_from': row[7],
                    'enabled': bool(row[8]),
                    'last_run_at': row[9],
                    'next_run_at': row[10],
                    'created_at': row[11],
                    'updated_at': row[12]
                }
                for row in rows
            ]

    def update_schedule(self, schedule_id: str, **fields) -> Optional[dict]:
        """
        Update a schedule.

        Args:
            schedule_id: ID of the schedule
            **fields: Fields to update (name, agent_name, message, schedule_type,
                     interval_value, start_from, enabled)

        Returns:
            Updated schedule dictionary or None if not found
        """
        # Get current schedule
        current = self.get_schedule(schedule_id)
        if not current:
            return None

        # Update fields
        allowed_fields = {
            'name', 'agent_name', 'message', 'schedule_type',
            'interval_value', 'start_from', 'enabled'
        }
        updates = {k: v for k, v in fields.items() if k in allowed_fields}

        if not updates:
            return current

        # If schedule timing changed, recalculate next_run_at
        timing_changed = any(k in updates for k in ['schedule_type', 'interval_value', 'start_from'])
        if timing_changed:
            schedule_type = updates.get('schedule_type', current['schedule_type'])
            interval_value = updates.get('interval_value', current['interval_value'])
            start_from = updates.get('start_from', current['start_from'])

            next_run_at = self._calculate_next_run(
                schedule_type, interval_value, start_from,
                current['last_run_at'], current['created_at']
            )
            updates['next_run_at'] = next_run_at

        # Handle enabled field conversion
        if 'enabled' in updates:
            updates['enabled'] = 1 if updates['enabled'] else 0

        updates['updated_at'] = datetime.now().isoformat()

        # Build UPDATE query
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [schedule_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE schedules
                SET {set_clause}
                WHERE schedule_id = ?
            """, values)
            conn.commit()

        return self.get_schedule(schedule_id)

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: ID of the schedule

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM schedules
                WHERE schedule_id = ?
            """, (schedule_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def delete_schedules_for_project(self, project_dir: str) -> int:
        """
        Delete all schedules for a project.

        Args:
            project_dir: Project directory

        Returns:
            Number of schedules deleted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM schedules
                WHERE project_dir = ?
            """, (project_dir,))
            count = cursor.rowcount
            conn.commit()
            return count

    def get_due_schedules(self) -> List[dict]:
        """
        Get all schedules that are due to run.

        Returns:
            List of schedule dictionaries that should run now
        """
        now = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT schedule_id, name, project_dir, agent_name, message,
                       schedule_type, interval_value, start_from, enabled,
                       last_run_at, next_run_at, created_at, updated_at
                FROM schedules
                WHERE enabled = 1 AND next_run_at <= ?
                ORDER BY next_run_at ASC
            """, (now,))

            rows = cursor.fetchall()

            return [
                {
                    'schedule_id': row[0],
                    'name': row[1],
                    'project_dir': row[2],
                    'agent_name': row[3],
                    'message': row[4],
                    'schedule_type': row[5],
                    'interval_value': row[6],
                    'start_from': row[7],
                    'enabled': bool(row[8]),
                    'last_run_at': row[9],
                    'next_run_at': row[10],
                    'created_at': row[11],
                    'updated_at': row[12]
                }
                for row in rows
            ]

    def mark_schedule_run(self, schedule_id: str) -> None:
        """
        Mark a schedule as run and calculate next run time.

        Args:
            schedule_id: ID of the schedule
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return

        now = datetime.now().isoformat()
        next_run_at = self._calculate_next_run(
            schedule['schedule_type'],
            schedule['interval_value'],
            schedule['start_from'],
            now,  # Use current time as last_run_at
            schedule['created_at']
        )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE schedules
                SET last_run_at = ?, next_run_at = ?, updated_at = ?
                WHERE schedule_id = ?
            """, (now, next_run_at, now, schedule_id))
            conn.commit()

    def _calculate_next_run(
        self,
        schedule_type: str,
        interval_value: int,
        start_from: Optional[str],
        last_run_at: Optional[str],
        created_at: str
    ) -> str:
        """
        Calculate the next run time for a schedule.

        Args:
            schedule_type: Type of schedule ('minutes', 'hours', 'weeks')
            interval_value: Interval value
            start_from: Optional start time (ISO datetime)
            last_run_at: Optional last run time (ISO datetime)
            created_at: Creation time (ISO datetime)

        Returns:
            ISO datetime string for next run
        """
        from datetime import timedelta

        # Determine the interval delta
        if schedule_type == 'minutes':
            delta = timedelta(minutes=interval_value)
        elif schedule_type == 'hours':
            delta = timedelta(hours=interval_value)
        elif schedule_type == 'weeks':
            delta = timedelta(weeks=interval_value)
        else:
            raise ValueError(f"Invalid schedule_type: {schedule_type}")

        now = datetime.now()

        # If we have a last run time, simply add the delta
        if last_run_at:
            last_run = datetime.fromisoformat(last_run_at)
            next_run = last_run + delta
            return next_run.isoformat()

        # Otherwise, calculate from anchor (start_from or created_at)
        anchor_str = start_from if start_from else created_at
        anchor = datetime.fromisoformat(anchor_str)

        # Find the first occurrence >= now
        next_run = anchor
        while next_run < now:
            next_run += delta

        return next_run.isoformat()


# Global database instance
_db_instance = None


def get_database() -> AgentDatabase:
    """Get or create global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = AgentDatabase()
    return _db_instance

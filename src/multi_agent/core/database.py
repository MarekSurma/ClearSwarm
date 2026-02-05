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
        call_mode: str = "synchronous"
    ) -> str:
        """
        Create a new agent execution record.

        Args:
            agent_name: Name of the agent being executed
            parent_agent_id: ID of parent agent (None if root)
            parent_agent_name: Name of parent agent ("root" if no parent)
            call_mode: Execution mode ('synchronous' or 'asynchronous')

        Returns:
            agent_id: Unique identifier for this execution
        """
        agent_id = str(uuid.uuid4())
        started_at = datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_executions
                (agent_id, agent_name, parent_agent_id, parent_agent_name, started_at, completed_at, call_mode)
                VALUES (?, ?, ?, ?, ?, NULL, ?)
            """, (agent_id, agent_name, parent_agent_id, parent_agent_name, started_at, call_mode))
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
                       started_at, completed_at, log_file
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
                    'log_file': row[6]
                }
            return None

    def get_all_executions(self) -> List[Dict]:
        """Get all agent executions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_id, agent_name, parent_agent_id, parent_agent_name,
                       started_at, completed_at, current_state, call_mode, log_file
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
                    'log_file': row[8] if len(row) > 8 else None
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


# Global database instance
_db_instance = None


def get_database() -> AgentDatabase:
    """Get or create global database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = AgentDatabase()
    return _db_instance

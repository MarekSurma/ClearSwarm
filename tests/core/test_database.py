"""Tests for database module."""
import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime

from multi_agent.core.database import AgentDatabase, get_database


class TestAgentDatabase:
    """Test cases for AgentDatabase class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        db = AgentDatabase(db_path=db_path)
        yield db

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    def test_database_initialization(self, temp_db):
        """Test that database tables are created correctly."""
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()

            # Check agent_executions table exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='agent_executions'
            """)
            assert cursor.fetchone() is not None

            # Check tool_executions table exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='tool_executions'
            """)
            assert cursor.fetchone() is not None

    def test_create_agent_execution(self, temp_db):
        """Test creating an agent execution record."""
        agent_id = temp_db.create_agent_execution(
            agent_name="test_agent",
            parent_agent_id=None,
            parent_agent_name="root",
            call_mode="synchronous"
        )

        assert agent_id is not None
        assert isinstance(agent_id, str)
        assert len(agent_id) > 0

        # Verify it was inserted
        execution = temp_db.get_agent_execution(agent_id)
        assert execution is not None
        assert execution['agent_name'] == 'test_agent'
        assert execution['parent_agent_id'] is None
        assert execution['parent_agent_name'] == 'root'
        assert execution['completed_at'] is None

    def test_create_agent_execution_with_parent(self, temp_db):
        """Test creating a child agent execution."""
        # Create parent
        parent_id = temp_db.create_agent_execution(
            agent_name="parent_agent",
            parent_agent_id=None,
            parent_agent_name="root"
        )

        # Create child
        child_id = temp_db.create_agent_execution(
            agent_name="child_agent",
            parent_agent_id=parent_id,
            parent_agent_name="parent_agent",
            call_mode="asynchronous"
        )

        child_execution = temp_db.get_agent_execution(child_id)
        assert child_execution['parent_agent_id'] == parent_id
        assert child_execution['parent_agent_name'] == 'parent_agent'

    def test_complete_agent_execution(self, temp_db):
        """Test completing an agent execution."""
        agent_id = temp_db.create_agent_execution(
            agent_name="test_agent",
            parent_agent_id=None,
            parent_agent_name="root"
        )

        # Initially should not be completed
        execution = temp_db.get_agent_execution(agent_id)
        assert execution['completed_at'] is None

        # Complete it
        temp_db.complete_agent_execution(agent_id)

        # Now should have completion timestamp
        execution = temp_db.get_agent_execution(agent_id)
        assert execution['completed_at'] is not None

        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(execution['completed_at'])

    def test_get_agent_execution_not_found(self, temp_db):
        """Test getting a non-existent agent execution."""
        result = temp_db.get_agent_execution("nonexistent-id")
        assert result is None

    def test_get_all_executions(self, temp_db):
        """Test retrieving all agent executions."""
        # Create multiple executions
        agent_ids = []
        for i in range(3):
            agent_id = temp_db.create_agent_execution(
                agent_name=f"agent_{i}",
                parent_agent_id=None,
                parent_agent_name="root"
            )
            agent_ids.append(agent_id)

        # Get all executions
        executions = temp_db.get_all_executions()

        assert len(executions) >= 3
        agent_names = [e['agent_name'] for e in executions]
        assert 'agent_0' in agent_names
        assert 'agent_1' in agent_names
        assert 'agent_2' in agent_names

    def test_get_all_executions_ordered_by_started_at(self, temp_db):
        """Test that get_all_executions returns results ordered by started_at DESC."""
        # Create executions
        first_id = temp_db.create_agent_execution("first_agent", None, "root")
        second_id = temp_db.create_agent_execution("second_agent", None, "root")

        executions = temp_db.get_all_executions()

        # Should be ordered DESC (newest first)
        assert executions[0]['agent_name'] == 'second_agent'
        assert executions[1]['agent_name'] == 'first_agent'

    def test_update_agent_state(self, temp_db):
        """Test updating agent state."""
        agent_id = temp_db.create_agent_execution(
            agent_name="test_agent",
            parent_agent_id=None,
            parent_agent_name="root"
        )

        # Update state
        temp_db.update_agent_state(agent_id, 'waiting')

        # Verify state was updated
        executions = temp_db.get_all_executions()
        agent_exec = next(e for e in executions if e['agent_id'] == agent_id)
        assert agent_exec['current_state'] == 'waiting'

    def test_create_tool_execution(self, temp_db):
        """Test creating a tool execution record."""
        # Create agent first
        agent_id = temp_db.create_agent_execution(
            agent_name="test_agent",
            parent_agent_id=None,
            parent_agent_name="root"
        )

        # Create tool execution
        tool_execution_id = temp_db.create_tool_execution(
            agent_id=agent_id,
            tool_name="calculator",
            parameters={"operation": "add", "a": 5, "b": 3},
            call_mode="synchronous"
        )

        assert tool_execution_id is not None
        assert isinstance(tool_execution_id, str)

    def test_complete_tool_execution(self, temp_db):
        """Test completing a tool execution."""
        # Create agent and tool execution
        agent_id = temp_db.create_agent_execution("test_agent", None, "root")
        tool_execution_id = temp_db.create_tool_execution(
            agent_id=agent_id,
            tool_name="calculator",
            parameters={"operation": "add", "a": 5, "b": 3}
        )

        # Complete tool execution
        result = "Result: 8"
        temp_db.complete_tool_execution(tool_execution_id, result)

        # Verify it was completed
        tool_executions = temp_db.get_tool_executions(agent_id)
        assert len(tool_executions) == 1
        assert tool_executions[0]['result'] == result
        assert tool_executions[0]['completed_at'] is not None

    def test_get_tool_executions(self, temp_db):
        """Test retrieving tool executions for an agent."""
        # Create agent
        agent_id = temp_db.create_agent_execution("test_agent", None, "root")

        # Create multiple tool executions
        tool_id_1 = temp_db.create_tool_execution(
            agent_id=agent_id,
            tool_name="calculator",
            parameters={"operation": "add"},
            call_mode="synchronous"
        )
        tool_id_2 = temp_db.create_tool_execution(
            agent_id=agent_id,
            tool_name="text_analyzer",
            parameters={"text": "hello"},
            call_mode="asynchronous"
        )

        # Get tool executions
        tool_executions = temp_db.get_tool_executions(agent_id)

        assert len(tool_executions) == 2
        assert tool_executions[0]['tool_name'] == 'calculator'
        assert tool_executions[1]['tool_name'] == 'text_analyzer'
        assert tool_executions[0]['call_mode'] == 'synchronous'
        assert tool_executions[1]['call_mode'] == 'asynchronous'
        assert tool_executions[0]['parameters'] == {"operation": "add"}
        assert tool_executions[1]['parameters'] == {"text": "hello"}

    def test_get_tool_executions_empty(self, temp_db):
        """Test getting tool executions when none exist."""
        agent_id = temp_db.create_agent_execution("test_agent", None, "root")
        tool_executions = temp_db.get_tool_executions(agent_id)
        assert tool_executions == []

    def test_tool_execution_is_running_flag(self, temp_db):
        """Test that is_running flag is set correctly for tool executions."""
        agent_id = temp_db.create_agent_execution("test_agent", None, "root")
        tool_id = temp_db.create_tool_execution(
            agent_id=agent_id,
            tool_name="calculator",
            parameters={"operation": "add"}
        )

        # Should be running initially
        tool_executions = temp_db.get_tool_executions(agent_id)
        assert tool_executions[0]['is_running'] is True

        # Complete it
        temp_db.complete_tool_execution(tool_id, "Result: 8")

        # Should not be running anymore
        tool_executions = temp_db.get_tool_executions(agent_id)
        assert tool_executions[0]['is_running'] is False

    def test_context_manager_connection(self, temp_db):
        """Test that connection context manager works correctly."""
        with temp_db._get_connection() as conn:
            assert isinstance(conn, sqlite3.Connection)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone() == (1,)

    def test_database_migration_columns(self, temp_db):
        """Test that migration adds missing columns."""
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()

            # Check current_state column exists
            cursor.execute("PRAGMA table_info(agent_executions)")
            columns = [col[1] for col in cursor.fetchall()]
            assert 'current_state' in columns

            # Check call_mode column exists in both tables
            cursor.execute("PRAGMA table_info(agent_executions)")
            agent_columns = [col[1] for col in cursor.fetchall()]
            assert 'call_mode' in agent_columns

            cursor.execute("PRAGMA table_info(tool_executions)")
            tool_columns = [col[1] for col in cursor.fetchall()]
            assert 'call_mode' in tool_columns


class TestGetDatabase:
    """Test cases for get_database() singleton function."""

    def test_get_database_singleton(self):
        """Test that get_database returns the same instance."""
        # Note: This will use the global instance
        db1 = get_database()
        db2 = get_database()

        assert db1 is db2

    def test_get_database_returns_agent_database(self):
        """Test that get_database returns an AgentDatabase instance."""
        db = get_database()
        assert isinstance(db, AgentDatabase)

"""
WebSocket API for real-time updates.
"""
import asyncio
import json
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pathlib import Path

from ...core.database import get_database

router = APIRouter()

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept and register new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)

    async def send_personal(self, message: dict, websocket: WebSocket):
        """Send message to specific connection."""
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        # Remove closed connections
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)

        # Clean up dead connections
        for connection in dead_connections:
            self.active_connections.discard(connection)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/updates")
async def websocket_updates(websocket: WebSocket):
    """
    WebSocket endpoint for real-time execution updates.
    Sends periodic updates about running agents and their status.
    """
    await manager.connect(websocket)

    try:
        # Send initial state
        db = get_database()
        executions = db.get_all_executions()

        await manager.send_personal({
            "type": "initial_state",
            "executions": [
                {
                    "agent_id": exec['agent_id'],
                    "agent_name": exec['agent_name'],
                    "parent_agent_id": exec['parent_agent_id'],
                    "started_at": exec['started_at'],
                    "completed_at": exec['completed_at'],
                    "current_state": exec.get('current_state', 'generating'),
                    "is_running": exec['completed_at'] is None
                }
                for exec in executions
            ]
        }, websocket)

        # Keep connection alive and send updates periodically
        last_execution_snapshot = {
            e['agent_id']: (e['completed_at'], e.get('current_state', 'generating'))
            for e in executions
        }

        while True:
            try:
                # Wait for a short period or receive ping from client
                await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            except asyncio.TimeoutError:
                # Timeout is expected - send update
                pass

            # Get current state
            current_executions = db.get_all_executions()

            # Build current snapshot for comparison
            current_snapshot = {
                e['agent_id']: (e['completed_at'], e.get('current_state', 'generating'))
                for e in current_executions
            }

            # Check if there are new executions or status changes
            if current_snapshot != last_execution_snapshot:
                last_execution_snapshot = current_snapshot

                # Send update
                await manager.send_personal({
                    "type": "executions_update",
                    "executions": [
                        {
                            "agent_id": exec['agent_id'],
                            "agent_name": exec['agent_name'],
                            "parent_agent_id": exec['parent_agent_id'],
                            "started_at": exec['started_at'],
                            "completed_at": exec['completed_at'],
                            "current_state": exec.get('current_state', 'generating'),
                            "is_running": exec['completed_at'] is None
                        }
                        for exec in current_executions
                    ]
                }, websocket)

            # Also check for running agents and send their status
            running_agents = [e for e in current_executions if e['completed_at'] is None]
            if running_agents:
                await manager.send_personal({
                    "type": "running_agents",
                    "count": len(running_agents),
                    "agents": [
                        {
                            "agent_id": e['agent_id'],
                            "agent_name": e['agent_name'],
                            "current_state": e.get('current_state', 'generating')
                        }
                        for e in running_agents
                    ]
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/agent/{agent_id}")
async def websocket_agent_detail(websocket: WebSocket, agent_id: str):
    """
    WebSocket endpoint for monitoring specific agent execution.
    Sends real-time updates about agent's progress, tool calls, etc.
    """
    await manager.connect(websocket)
    db = get_database()

    try:
        # Verify agent exists
        execution = db.get_agent_execution(agent_id)
        if not execution:
            await manager.send_personal({
                "type": "error",
                "message": f"Agent execution '{agent_id}' not found"
            }, websocket)
            return

        # Send initial agent state
        tool_execs = db.get_tool_executions(agent_id)

        await manager.send_personal({
            "type": "agent_state",
            "agent_id": agent_id,
            "agent_name": execution['agent_name'],
            "started_at": execution['started_at'],
            "completed_at": execution['completed_at'],
            "is_running": execution['completed_at'] is None,
            "tools": [
                {
                    "tool_execution_id": tool['tool_execution_id'],
                    "tool_name": tool['tool_name'],
                    "parameters": tool['parameters'],
                    "started_at": tool['started_at'],
                    "completed_at": tool['completed_at'],
                    "is_running": tool['is_running']
                }
                for tool in tool_execs
            ]
        }, websocket)

        # Monitor for changes
        last_tool_count = len(tool_execs)
        last_completed = execution['completed_at']

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass

            # Check for updates
            execution = db.get_agent_execution(agent_id)
            tool_execs = db.get_tool_executions(agent_id)

            # Check if tool count changed or agent completed
            if len(tool_execs) != last_tool_count or execution['completed_at'] != last_completed:
                last_tool_count = len(tool_execs)
                last_completed = execution['completed_at']

                await manager.send_personal({
                    "type": "agent_update",
                    "agent_id": agent_id,
                    "completed_at": execution['completed_at'],
                    "is_running": execution['completed_at'] is None,
                    "tools": [
                        {
                            "tool_execution_id": tool['tool_execution_id'],
                            "tool_name": tool['tool_name'],
                            "parameters": tool['parameters'],
                            "started_at": tool['started_at'],
                            "completed_at": tool['completed_at'],
                            "is_running": tool['is_running']
                        }
                        for tool in tool_execs
                    ]
                }, websocket)

                # If agent completed, try to send final log
                if execution['completed_at'] is not None:
                    log_file_path = execution.get('log_file')
                    if log_file_path:
                        log_file = Path(log_file_path)
                        if log_file.exists():
                            try:
                                with open(log_file, 'r', encoding='utf-8') as f:
                                    log_data = json.load(f)

                                await manager.send_personal({
                                    "type": "agent_completed",
                                    "agent_id": agent_id,
                                    "final_response": log_data.get('final_response', ''),
                                    "total_iterations": log_data.get('total_iterations', 0)
                                }, websocket)

                                # Close connection after sending final state
                                break
                            except Exception as e:
                                print(f"Error reading log file: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
    finally:
        manager.disconnect(websocket)

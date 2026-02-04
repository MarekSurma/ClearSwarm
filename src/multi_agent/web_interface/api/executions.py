"""
Execution history API endpoints.
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.database import get_database

router = APIRouter()


class AgentExecution(BaseModel):
    """Agent execution model."""
    agent_id: str
    agent_name: str
    parent_agent_id: Optional[str]
    parent_agent_name: str
    started_at: str
    completed_at: Optional[str]
    current_state: str
    call_mode: str
    is_running: bool
    log_file: Optional[str]


class ToolExecution(BaseModel):
    """Tool execution model."""
    tool_execution_id: str
    tool_name: str
    parameters: Dict
    call_mode: str
    started_at: str
    completed_at: Optional[str]
    result: Optional[str]
    is_running: bool


class ExecutionTree(BaseModel):
    """Execution tree model."""
    agent_id: str
    agent_name: str
    parent_agent_id: Optional[str]
    started_at: str
    completed_at: Optional[str]
    current_state: str
    is_running: bool
    children: List['ExecutionTree']
    tools: List[ToolExecution]


class ExecutionLog(BaseModel):
    """Execution log model."""
    agent_id: str
    agent_name: str
    parent_agent_id: Optional[str]
    parent_agent_name: str
    started_at: str
    completed_at: Optional[str]
    final_response: Optional[str]
    total_iterations: Optional[int]
    session_ended_explicitly: Optional[bool]
    interactions: List[Dict]


@router.get("/executions", response_model=List[AgentExecution])
async def list_executions():
    """List all agent executions."""
    db = get_database()
    executions = db.get_all_executions()

    return [
        AgentExecution(
            agent_id=exec['agent_id'],
            agent_name=exec['agent_name'],
            parent_agent_id=exec['parent_agent_id'],
            parent_agent_name=exec['parent_agent_name'],
            started_at=exec['started_at'],
            completed_at=exec['completed_at'],
            current_state=exec.get('current_state', 'generating'),
            call_mode=exec.get('call_mode', 'synchronous'),
            is_running=exec['completed_at'] is None,
            log_file=exec.get('log_file')
        )
        for exec in executions
    ]


@router.get("/executions/roots", response_model=List[AgentExecution])
async def list_root_executions():
    """List only root-level agent executions."""
    db = get_database()
    executions = db.get_all_executions()

    # Filter only root executions (no parent)
    root_executions = [
        AgentExecution(
            agent_id=exec['agent_id'],
            agent_name=exec['agent_name'],
            parent_agent_id=exec['parent_agent_id'],
            parent_agent_name=exec['parent_agent_name'],
            started_at=exec['started_at'],
            completed_at=exec['completed_at'],
            current_state=exec.get('current_state', 'generating'),
            call_mode=exec.get('call_mode', 'synchronous'),
            is_running=exec['completed_at'] is None,
            log_file=exec.get('log_file')
        )
        for exec in executions
        if exec['parent_agent_id'] is None
    ]

    return root_executions


@router.get("/executions/{agent_id}", response_model=AgentExecution)
async def get_execution(agent_id: str):
    """Get details of a specific execution."""
    db = get_database()
    execution = db.get_agent_execution(agent_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution '{agent_id}' not found")

    # Get additional info from all_executions to get current_state
    all_execs = db.get_all_executions()
    exec_info = next((e for e in all_execs if e['agent_id'] == agent_id), None)

    return AgentExecution(
        agent_id=execution['agent_id'],
        agent_name=execution['agent_name'],
        parent_agent_id=execution['parent_agent_id'],
        parent_agent_name=execution['parent_agent_name'],
        started_at=execution['started_at'],
        completed_at=execution['completed_at'],
        current_state=exec_info.get('current_state', 'generating') if exec_info else 'generating',
        call_mode=exec_info.get('call_mode', 'synchronous') if exec_info else 'synchronous',
        is_running=execution['completed_at'] is None,
        log_file=execution.get('log_file')
    )


@router.get("/executions/{agent_id}/tree", response_model=ExecutionTree)
async def get_execution_tree(agent_id: str):
    """Get execution tree for an agent (including all children)."""
    db = get_database()

    def build_tree(agent_id: str) -> ExecutionTree:
        """Recursively build execution tree."""
        execution = db.get_agent_execution(agent_id)
        if not execution:
            raise HTTPException(status_code=404, detail=f"Execution '{agent_id}' not found")

        # Get all executions to find children
        all_execs = db.get_all_executions()
        children_execs = [e for e in all_execs if e['parent_agent_id'] == agent_id]

        # Get tool executions
        tool_execs = db.get_tool_executions(agent_id)

        # Get current state
        exec_info = next((e for e in all_execs if e['agent_id'] == agent_id), None)
        current_state = exec_info.get('current_state', 'generating') if exec_info else 'generating'

        return ExecutionTree(
            agent_id=execution['agent_id'],
            agent_name=execution['agent_name'],
            parent_agent_id=execution['parent_agent_id'],
            started_at=execution['started_at'],
            completed_at=execution['completed_at'],
            current_state=current_state,
            is_running=execution['completed_at'] is None,
            children=[build_tree(child['agent_id']) for child in children_execs],
            tools=[
                ToolExecution(
                    tool_execution_id=tool['tool_execution_id'],
                    tool_name=tool['tool_name'],
                    parameters=tool['parameters'],
                    call_mode=tool.get('call_mode', 'synchronous'),
                    started_at=tool['started_at'],
                    completed_at=tool['completed_at'],
                    result=tool['result'],
                    is_running=tool['is_running']
                )
                for tool in tool_execs
            ]
        )

    return build_tree(agent_id)


@router.get("/executions/{agent_id}/log", response_model=ExecutionLog)
async def get_execution_log(agent_id: str):
    """Get detailed execution log from JSON file."""
    db = get_database()
    execution = db.get_agent_execution(agent_id)

    if not execution:
        raise HTTPException(
            status_code=404,
            detail=f"Execution '{agent_id}' not found"
        )

    log_file_path = execution.get('log_file')
    if not log_file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Log file for execution '{agent_id}' not found"
        )

    log_file = Path(log_file_path)
    if not log_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Log file for execution '{agent_id}' not found"
        )

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

        return ExecutionLog(**log_data)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load log file: {str(e)}"
        )


@router.get("/executions/{agent_id}/tools", response_model=List[ToolExecution])
async def get_execution_tools(agent_id: str):
    """Get all tool executions for an agent."""
    db = get_database()

    # Verify agent exists
    execution = db.get_agent_execution(agent_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution '{agent_id}' not found")

    tool_execs = db.get_tool_executions(agent_id)

    return [
        ToolExecution(
            tool_execution_id=tool['tool_execution_id'],
            tool_name=tool['tool_name'],
            parameters=tool['parameters'],
            call_mode=tool.get('call_mode', 'synchronous'),
            started_at=tool['started_at'],
            completed_at=tool['completed_at'],
            result=tool['result'],
            is_running=tool['is_running']
        )
        for tool in tool_execs
    ]


class GraphNode(BaseModel):
    """Graph node model for vis-network."""
    id: str
    label: str
    group: str  # 'root', 'agent', 'tool'
    color: str
    shape: str
    size: int
    is_running: bool
    current_state: Optional[str]


class GraphEdge(BaseModel):
    """Graph edge model for vis-network."""
    id: str
    from_node: str  # renamed from 'from' to avoid Python keyword
    to_node: str    # renamed from 'to' to avoid Python keyword
    dashes: bool
    call_mode: str  # 'synchronous' or 'asynchronous'


class GraphData(BaseModel):
    """Complete graph data for visualization."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


@router.get("/executions/{agent_id}/graph", response_model=GraphData)
async def get_execution_graph(agent_id: str):
    """Get execution graph data for vis-network visualization."""
    db = get_database()

    # Verify root agent exists
    execution = db.get_agent_execution(agent_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution '{agent_id}' not found")

    nodes = []
    edges = []
    node_counter = 0

    # Get all executions for state information
    all_execs = db.get_all_executions()
    exec_states = {e['agent_id']: e for e in all_execs}

    def add_agent_and_children(agent_id: str, is_root: bool = False):
        """Recursively add agent nodes and their children."""
        nonlocal node_counter

        exec_data = db.get_agent_execution(agent_id)
        if not exec_data:
            return

        exec_state = exec_states.get(agent_id, {})
        current_state = exec_state.get('current_state', 'generating')
        is_running = exec_data['completed_at'] is None

        # Determine node properties based on type
        if is_root:
            group = 'root'
            color = '#FFD700'  # Gold
            size = 30
            shape = 'dot'
        else:
            group = 'agent'
            color = '#97C2FC' if is_running else '#6c757d'  # Blue if running, gray if completed
            size = 20
            shape = 'dot'

        # Create label with agent name and short ID
        label = f"{exec_data['agent_name']}\n[{agent_id[:8]}]"

        # Add node
        nodes.append(GraphNode(
            id=agent_id,
            label=label,
            group=group,
            color=color,
            shape=shape,
            size=size,
            is_running=is_running,
            current_state=current_state
        ))

        # Add edge from parent (if not root)
        if not is_root and exec_data['parent_agent_id']:
            # Get call mode from execution data
            agent_call_mode = exec_state.get('call_mode', 'synchronous')

            edges.append(GraphEdge(
                id=f"edge_{exec_data['parent_agent_id']}_{agent_id}",
                from_node=exec_data['parent_agent_id'],
                to_node=agent_id,
                dashes=(agent_call_mode == 'asynchronous'),  # Dashed for async
                call_mode=agent_call_mode
            ))

        # Add child agents first to get their names
        all_execs_list = db.get_all_executions()
        children = [e for e in all_execs_list if e['parent_agent_id'] == agent_id]
        child_agent_names = {child['agent_name'] for child in children}

        # Add tool executions (but skip tools that are actually agents)
        tool_execs = db.get_tool_executions(agent_id)
        for tool in tool_execs:
            tool_name = tool['tool_name']

            # Skip if this tool is actually an agent (will be shown as agent node)
            if tool_name in child_agent_names:
                continue

            tool_id = tool['tool_execution_id']
            tool_running = tool['is_running']

            # Tool node
            nodes.append(GraphNode(
                id=tool_id,
                label=tool_name,
                group='tool',
                color='#FB7E81' if tool_running else '#999',  # Red if running, gray if completed
                shape='diamond',
                size=15,
                is_running=tool_running,
                current_state=None
            ))

            # Tool edge - dashed if async, solid if sync
            tool_call_mode = tool.get('call_mode', 'synchronous')
            edges.append(GraphEdge(
                id=f"edge_{agent_id}_{tool_id}",
                from_node=agent_id,
                to_node=tool_id,
                dashes=(tool_call_mode == 'asynchronous'),  # Dashed for async, solid for sync
                call_mode=tool_call_mode
            ))

        # Add child agents (already retrieved above)
        for child in children:
            add_agent_and_children(child['agent_id'], is_root=False)

    # Build graph starting from root
    add_agent_and_children(agent_id, is_root=True)

    return GraphData(nodes=nodes, edges=edges)

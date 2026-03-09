"""
Execution history API endpoints.
"""
import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
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
async def list_executions(project: str = Query("default")):
    """List all agent executions for a project."""
    db = get_database()
    executions = db.get_all_executions(project_dir=project)

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
async def list_root_executions(project: str = Query("default")):
    """List only root-level agent executions for a project."""
    db = get_database()
    executions = db.get_all_executions(project_dir=project)

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
    error_count: int = 0


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


def _is_error_result(result: str) -> bool:
    """Check if a tool execution result indicates an error."""
    if not result:
        return False
    return (
        result.startswith("Error: ") or
        result.startswith("Error ") or
        result.startswith("SECURITY ERROR") or
        (result.startswith("Tool or agent") and "not found" in result)
    )


# In-memory cache for graph responses: agent_id -> (etag, json_bytes, timestamp)
_graph_cache: Dict[str, tuple] = {}
_GRAPH_CACHE_TTL = 0.5  # seconds


@router.get("/executions/{agent_id}/graph")
async def get_execution_graph(agent_id: str, request: Request):
    """Get execution graph data for vis-network visualization."""

    # Check cache first
    cached = _graph_cache.get(agent_id)
    if cached:
        etag, json_bytes, ts = cached
        if time.time() - ts < _GRAPH_CACHE_TTL:
            if request.headers.get("if-none-match") == etag:
                return Response(status_code=304)
            return Response(
                content=json_bytes,
                media_type="application/json",
                headers={"ETag": etag, "Cache-Control": "no-cache"},
            )

    db = get_database()

    # Verify root agent exists
    execution = db.get_agent_execution(agent_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution '{agent_id}' not found")

    # Fetch ALL data in exactly 2 queries (instead of N+1)
    all_execs = db.get_all_executions()
    all_tools = db.get_all_tool_executions()

    # Build lookup dictionaries in memory
    exec_by_id: Dict[str, dict] = {e['agent_id']: e for e in all_execs}
    children_by_parent: Dict[str, list] = defaultdict(list)
    for e in all_execs:
        if e.get('parent_agent_id'):
            children_by_parent[e['parent_agent_id']].append(e)
    tools_by_agent: Dict[str, list] = defaultdict(list)
    for t in all_tools:
        tools_by_agent[t['agent_id']].append(t)

    nodes = []
    edges = []

    def add_agent_and_children(aid: str, is_root: bool = False):
        """Recursively add agent nodes and their children (zero DB queries)."""
        exec_data = exec_by_id.get(aid)
        if not exec_data:
            return

        current_state = exec_data.get('current_state', 'generating')
        is_running = exec_data['completed_at'] is None

        if is_root:
            group = 'root'
            color = '#f0d8b0'
            size = 30
        else:
            group = 'agent'
            color = '#c86840' if is_running else '#5c2818'
            size = 20

        label = f"{exec_data['agent_name'].replace('_', ' ')}\n[{aid[:8]}]"

        # Count errors from pre-fetched tool executions
        agent_tools = tools_by_agent.get(aid, [])
        agent_error_count = sum(
            1 for t in agent_tools
            if _is_error_result(t.get('result', '') or '')
        )

        nodes.append(GraphNode(
            id=aid,
            label=label,
            group=group,
            color=color,
            shape='dot',
            size=size,
            is_running=is_running,
            current_state=current_state,
            error_count=agent_error_count
        ))

        if not is_root and exec_data.get('parent_agent_id'):
            agent_call_mode = exec_data.get('call_mode', 'synchronous')
            edges.append(GraphEdge(
                id=f"edge_{exec_data['parent_agent_id']}_{aid}",
                from_node=exec_data['parent_agent_id'],
                to_node=aid,
                dashes=(agent_call_mode == 'asynchronous'),
                call_mode=agent_call_mode
            ))

        # Get children from pre-built lookup
        children = children_by_parent.get(aid, [])
        child_agent_names = {child['agent_name'] for child in children}

        # Add tool nodes (skip tools that are actually sub-agents)
        for tool in agent_tools:
            tool_name = tool['tool_name']
            if tool_name in child_agent_names:
                continue

            tool_id = tool['tool_execution_id']
            tool_running = tool['is_running']
            tool_has_error = _is_error_result(tool.get('result', '') or '')

            nodes.append(GraphNode(
                id=tool_id,
                label=tool_name.replace('_', ' '),
                group='tool',
                color='#b8a048' if tool_running else '#4a3820',
                shape='diamond',
                size=15,
                is_running=tool_running,
                current_state=None,
                error_count=1 if tool_has_error else 0
            ))

            tool_call_mode = tool.get('call_mode', 'synchronous')
            edges.append(GraphEdge(
                id=f"edge_{aid}_{tool_id}",
                from_node=aid,
                to_node=tool_id,
                dashes=(tool_call_mode == 'asynchronous'),
                call_mode=tool_call_mode
            ))

        for child in children:
            add_agent_and_children(child['agent_id'], is_root=False)

    # Build graph starting from root (all data already in memory)
    add_agent_and_children(agent_id, is_root=True)

    graph_data = GraphData(nodes=nodes, edges=edges)

    # Serialize, compute ETag, cache
    json_bytes = graph_data.model_dump_json().encode()
    etag = hashlib.md5(json_bytes).hexdigest()

    if request.headers.get("if-none-match") == etag:
        _graph_cache[agent_id] = (etag, json_bytes, time.time())
        return Response(status_code=304)

    _graph_cache[agent_id] = (etag, json_bytes, time.time())

    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={"ETag": etag, "Cache-Control": "no-cache"},
    )

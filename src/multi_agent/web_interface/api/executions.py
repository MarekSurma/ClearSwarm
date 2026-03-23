"""
Execution history API endpoints.
"""
import hashlib
import json
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
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
def list_executions(project: str = Query("default"), limit: int = Query(500, ge=1, le=10000)):
    """List agent executions for a project with a limit. Roots and running are always included."""
    db = get_database()
    all_executions = db.get_all_executions(project_dir=project)

    if len(all_executions) <= limit:
        executions = all_executions
    else:
        # Always include root executions and running ones, fill rest with most recent
        roots_and_running = [e for e in all_executions if e['parent_agent_id'] is None or e['completed_at'] is None]
        rest = [e for e in all_executions if e['parent_agent_id'] is not None and e['completed_at'] is not None]
        rest.sort(key=lambda e: e['started_at'], reverse=True)
        remaining = max(0, limit - len(roots_and_running))
        executions = roots_and_running + rest[:remaining]

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
def list_root_executions(project: str = Query("default")):
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
def get_execution(agent_id: str):
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
def get_execution_tree(agent_id: str):
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
def get_execution_log(agent_id: str):
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
def get_execution_tools(agent_id: str):
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


@dataclass
class GraphChange:
    """A single recorded change in the graph."""
    sequence: int
    timestamp: float
    change_type: str   # node_add, node_update, node_remove, edge_add, edge_update, edge_remove
    entity_id: str
    data: Optional[dict]


class GraphChangeLog:
    """In-memory delta cache per agent_id. DB is the source of truth, not this."""

    def __init__(self, max_changes: int = 5000, max_age_seconds: float = 300.0):
        self._logs: Dict[str, List[GraphChange]] = {}
        self._sequences: Dict[str, int] = {}
        self._prev_graphs: Dict[str, GraphData] = {}
        self._lock = threading.Lock()
        self.max_changes = max_changes
        self.max_age_seconds = max_age_seconds

    def update(self, agent_id: str, new_graph: GraphData) -> None:
        """Compare new graph with previous, record changes."""
        with self._lock:
            old_graph = self._prev_graphs.get(agent_id)
            if old_graph is None:
                self._prev_graphs[agent_id] = new_graph
                self._sequences.setdefault(agent_id, 1)
                return

            changes = self._compute_diff(old_graph, new_graph)
            if not changes:
                return

            seq = self._sequences.get(agent_id, 0)
            now = time.time()
            log = self._logs.setdefault(agent_id, [])
            for change_type, entity_id, data in changes:
                seq += 1
                log.append(GraphChange(
                    sequence=seq, timestamp=now,
                    change_type=change_type, entity_id=entity_id, data=data,
                ))
            self._sequences[agent_id] = seq
            self._prev_graphs[agent_id] = new_graph
            self._gc(agent_id)

    def get_changes_since(self, agent_id: str, since_seq: int) -> Optional[List[GraphChange]]:
        """Return changes since sequence, or None if changelog can't cover the range."""
        with self._lock:
            log = self._logs.get(agent_id, [])
            if not log:
                return None
            if log[0].sequence > since_seq + 1:
                return None
            result = [c for c in log if c.sequence > since_seq]
            return result if result else None

    def get_current_sequence(self, agent_id: str) -> int:
        with self._lock:
            return self._sequences.get(agent_id, 0)

    def clear(self, agent_id: str) -> None:
        """Clear changelog for an agent (safe — full snapshot always from DB)."""
        with self._lock:
            self._logs.pop(agent_id, None)
            self._prev_graphs.pop(agent_id, None)

    def _compute_diff(self, old_graph: GraphData, new_graph: GraphData) -> list:
        """Compare two graphs, return list of (change_type, entity_id, data) tuples."""
        changes = []
        old_nodes = {n.id: n for n in old_graph.nodes}
        new_nodes = {n.id: n for n in new_graph.nodes}
        for nid, node in new_nodes.items():
            if nid not in old_nodes:
                changes.append(('node_add', nid, node.model_dump()))
            elif node != old_nodes[nid]:
                changes.append(('node_update', nid, node.model_dump()))
        for nid in old_nodes:
            if nid not in new_nodes:
                changes.append(('node_remove', nid, None))

        old_edges = {e.id: e for e in old_graph.edges}
        new_edges = {e.id: e for e in new_graph.edges}
        for eid, edge in new_edges.items():
            if eid not in old_edges:
                changes.append(('edge_add', eid, edge.model_dump()))
            elif edge != old_edges[eid]:
                changes.append(('edge_update', eid, edge.model_dump()))
        for eid in old_edges:
            if eid not in new_edges:
                changes.append(('edge_remove', eid, None))
        return changes

    def _gc(self, agent_id: str) -> None:
        """Garbage collect old changelog entries."""
        log = self._logs.get(agent_id)
        if not log:
            return
        cutoff = time.time() - self.max_age_seconds
        while log and log[0].timestamp < cutoff:
            log.pop(0)
        if len(log) > self.max_changes:
            log[:] = log[-self.max_changes:]


# Graph build cache: agent_id -> (GraphData, json_bytes, etag, timestamp)
_graph_build_cache: Dict[str, tuple] = {}
_GRAPH_CACHE_TTL = 0.5  # seconds
_changelog = GraphChangeLog()


def _build_graph(agent_id: str) -> Optional[GraphData]:
    """Build execution graph from database with caching."""
    cached = _graph_build_cache.get(agent_id)
    if cached:
        graph_data, _, _, ts = cached
        if time.time() - ts < _GRAPH_CACHE_TTL:
            return graph_data

    db = get_database()
    execution = db.get_agent_execution(agent_id)
    if not execution:
        return None

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
            group, color, size = 'root', '#f0d8b0', 30
        else:
            group = 'agent'
            color = '#c86840' if is_running else '#5c2818'
            size = 20

        label = f"{exec_data['agent_name'].replace('_', ' ')}\n[{aid[:8]}]"

        agent_tools = tools_by_agent.get(aid, [])
        agent_error_count = sum(
            1 for t in agent_tools
            if _is_error_result(t.get('result', '') or '')
        )

        nodes.append(GraphNode(
            id=aid, label=label, group=group, color=color,
            shape='dot', size=size, is_running=is_running,
            current_state=current_state, error_count=agent_error_count,
        ))

        if not is_root and exec_data.get('parent_agent_id'):
            call_mode = exec_data.get('call_mode', 'synchronous')
            edges.append(GraphEdge(
                id=f"edge_{exec_data['parent_agent_id']}_{aid}",
                from_node=exec_data['parent_agent_id'], to_node=aid,
                dashes=(call_mode == 'asynchronous'), call_mode=call_mode,
            ))

        children = children_by_parent.get(aid, [])
        child_agent_names = {c['agent_name'] for c in children}

        for tool in agent_tools:
            if tool['tool_name'] in child_agent_names:
                continue
            tid = tool['tool_execution_id']
            t_running = tool['is_running']
            t_error = _is_error_result(tool.get('result', '') or '')
            nodes.append(GraphNode(
                id=tid, label=tool['tool_name'].replace('_', ' '),
                group='tool', color='#b8a048' if t_running else '#4a3820',
                shape='diamond', size=15, is_running=t_running,
                current_state=None, error_count=1 if t_error else 0,
            ))
            t_call_mode = tool.get('call_mode', 'synchronous')
            edges.append(GraphEdge(
                id=f"edge_{aid}_{tid}", from_node=aid, to_node=tid,
                dashes=(t_call_mode == 'asynchronous'), call_mode=t_call_mode,
            ))

        for child in children:
            add_agent_and_children(child['agent_id'], is_root=False)

    add_agent_and_children(agent_id, is_root=True)
    graph_data = GraphData(nodes=nodes, edges=edges)

    json_bytes = graph_data.model_dump_json().encode()
    etag = hashlib.md5(json_bytes).hexdigest()
    _graph_build_cache[agent_id] = (graph_data, json_bytes, etag, time.time())
    return graph_data


@router.get("/executions/{agent_id}/graph")
def get_execution_graph(agent_id: str, request: Request):
    """Get execution graph data for vis-network visualization."""
    graph_data = _build_graph(agent_id)
    if graph_data is None:
        raise HTTPException(status_code=404, detail=f"Execution '{agent_id}' not found")

    _, json_bytes, etag, _ = _graph_build_cache[agent_id]
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)
    return Response(
        content=json_bytes, media_type="application/json",
        headers={"ETag": etag, "Cache-Control": "no-cache"},
    )


@router.get("/executions/{agent_id}/graph/delta")
def get_graph_delta(agent_id: str, since: int = Query(0, ge=0)):
    """Get incremental graph updates. Returns delta if possible, full snapshot otherwise.
    Full snapshot is always generated from the database (source of truth), not from in-memory cache."""
    graph_data = _build_graph(agent_id)
    if graph_data is None:
        raise HTTPException(status_code=404, detail=f"Execution '{agent_id}' not found")

    _changelog.update(agent_id, graph_data)
    current_seq = _changelog.get_current_sequence(agent_id)

    # Client has prior state — try delta
    if since > 0:
        if since == current_seq:
            return Response(status_code=304)
        changes = _changelog.get_changes_since(agent_id, since)
        if changes:
            return {
                "type": "delta",
                "current_sequence": current_seq,
                "changes": [
                    {"sequence": c.sequence, "change_type": c.change_type,
                     "entity_id": c.entity_id, "data": c.data}
                    for c in changes
                ],
            }

    # Full snapshot from DB (since=0, gap too large, or changelog empty)
    return {
        "type": "snapshot",
        "current_sequence": current_seq,
        "nodes": [n.model_dump() for n in graph_data.nodes],
        "edges": [e.model_dump() for e in graph_data.edges],
    }

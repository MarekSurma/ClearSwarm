"""
Agent management API endpoints.
"""
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.agent import AgentLoader
from ...tools.loader import ToolLoader

router = APIRouter()

# Track running agent tasks for cancellation
_running_tasks: Dict[str, asyncio.Task] = {}
_tasks_lock = asyncio.Lock()


async def _track_task(agent_id: str, task: asyncio.Task):
    """Track a running task."""
    async with _tasks_lock:
        _running_tasks[agent_id] = task


async def _untrack_task(agent_id: str):
    """Remove a task from tracking."""
    async with _tasks_lock:
        _running_tasks.pop(agent_id, None)


async def _get_running_tasks() -> Dict[str, asyncio.Task]:
    """Get all running tasks."""
    async with _tasks_lock:
        return dict(_running_tasks)


def get_agents_dir() -> Path:
    """Get the user agents directory path."""
    current_dir = Path.cwd()
    if (current_dir / "user" / "agents").exists():
        return current_dir / "user" / "agents"
    elif (current_dir.parent / "user" / "agents").exists():
        return current_dir.parent / "user" / "agents"
    return current_dir / "user" / "agents"

# Initialize loaders (lazy loading)
_tool_loader: Optional[ToolLoader] = None
_agent_loader: Optional[AgentLoader] = None


def get_loaders():
    """Get or initialize tool and agent loaders."""
    global _tool_loader, _agent_loader

    if _tool_loader is None:
        # Find project root (where user/ directory is)
        # When running from src/, go up one level
        current_dir = Path.cwd()

        # Try to find user/tools directory
        if (current_dir / "user" / "tools").exists():
            tools_dir = str(current_dir / "user" / "tools")
        elif (current_dir.parent / "user" / "tools").exists():
            tools_dir = str(current_dir.parent / "user" / "tools")
        else:
            tools_dir = "user/tools"  # fallback

        _tool_loader = ToolLoader(tools_dir=tools_dir)
        _tool_loader.load_tools()

    if _agent_loader is None:
        # Find agents directory
        current_dir = Path.cwd()

        if (current_dir / "user" / "agents").exists():
            agents_dir = str(current_dir / "user" / "agents")
        elif (current_dir.parent / "user" / "agents").exists():
            agents_dir = str(current_dir.parent / "user" / "agents")
        else:
            agents_dir = "user/agents"  # fallback

        _agent_loader = AgentLoader(agents_dir=agents_dir, tool_loader=_tool_loader)

    return _tool_loader, _agent_loader


class AgentInfo(BaseModel):
    """Agent information model."""
    name: str
    description: str
    tools: List[str]


class AgentDetail(BaseModel):
    """Detailed agent information for editing."""
    name: str
    description: str
    system_prompt: str
    tools: List[str]


class CreateAgentRequest(BaseModel):
    """Request model for creating an agent."""
    name: str
    description: str
    system_prompt: str
    tools: List[str]


class UpdateAgentRequest(BaseModel):
    """Request model for updating an agent."""
    description: str
    system_prompt: str
    tools: List[str]


class RunAgentRequest(BaseModel):
    """Request model for running an agent."""
    agent_name: str
    message: str


class RunAgentResponse(BaseModel):
    """Response model for agent execution."""
    agent_id: str
    agent_name: str
    status: str
    message: str


@router.get("/agents", response_model=List[AgentInfo])
async def list_agents():
    """List all available agents."""
    # Reset loaders to discover newly added agents from filesystem
    reset_loaders()
    _, agent_loader = get_loaders()

    agents = []
    for agent_name in agent_loader.get_available_agents():
        config = agent_loader.get_agent_config(agent_name)
        agents.append(AgentInfo(
            name=agent_name,
            description=config.description,
            tools=config.tools
        ))

    # Sort agents alphabetically by name
    agents.sort(key=lambda a: a.name.lower())

    return agents


@router.get("/agents/{agent_name}", response_model=AgentInfo)
async def get_agent(agent_name: str):
    """Get information about a specific agent."""
    _, agent_loader = get_loaders()

    if not agent_loader.has_agent(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    config = agent_loader.get_agent_config(agent_name)
    return AgentInfo(
        name=agent_name,
        description=config.description,
        tools=config.tools
    )


@router.post("/agents/run", response_model=RunAgentResponse)
async def run_agent(request: RunAgentRequest):
    """
    Run an agent with a message.
    This starts the agent execution in the background.
    """
    _, agent_loader = get_loaders()

    if not agent_loader.has_agent(request.agent_name):
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{request.agent_name}' not found"
        )

    try:
        # Create agent instance
        agent = agent_loader.create_agent(request.agent_name)

        async def run_and_cleanup():
            """Run agent and clean up tracking when done."""
            try:
                await agent.run(request.message)
            finally:
                await _untrack_task(agent.agent_id)

        # Start agent execution in background (don't wait for completion)
        task = asyncio.create_task(run_and_cleanup())
        await _track_task(agent.agent_id, task)

        return RunAgentResponse(
            agent_id=agent.agent_id,
            agent_name=request.agent_name,
            status="started",
            message=f"Agent '{request.agent_name}' started successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start agent: {str(e)}"
        )


class StopAllResponse(BaseModel):
    """Response model for stop all agents."""
    stopped_count: int
    agent_ids: List[str]
    message: str


@router.post("/agents/stop-all", response_model=StopAllResponse)
async def stop_all_agents():
    """
    Stop all running agents.
    Cancels all tracked asyncio tasks and marks agents as completed in the database.
    """
    from ...core.database import get_database

    running_tasks = await _get_running_tasks()
    stopped_ids = []

    for agent_id, task in running_tasks.items():
        if not task.done():
            task.cancel()
            stopped_ids.append(agent_id)

    # Also mark any running agents in database as completed
    db = get_database()
    all_executions = db.get_all_executions()

    for exec_info in all_executions:
        if exec_info['completed_at'] is None:
            db.complete_agent_execution(exec_info['agent_id'])
            if exec_info['agent_id'] not in stopped_ids:
                stopped_ids.append(exec_info['agent_id'])

    # Clear tracking
    async with _tasks_lock:
        _running_tasks.clear()

    return StopAllResponse(
        stopped_count=len(stopped_ids),
        agent_ids=stopped_ids,
        message=f"Stopped {len(stopped_ids)} agent(s)"
    )


@router.post("/agents/stop/{root_id}", response_model=StopAllResponse)
async def stop_agents_by_root(root_id: str):
    """
    Stop all agents belonging to a specific execution tree (root and all children).

    Args:
        root_id: The root agent ID of the execution tree to stop
    """
    from ...core.database import get_database

    db = get_database()
    all_executions = db.get_all_executions()

    # Find all agent IDs that belong to this root (root + all descendants)
    def get_all_descendants(agent_id: str, executions: list) -> set:
        """Recursively get all descendant agent IDs."""
        descendants = {agent_id}
        children = [e for e in executions if e['parent_agent_id'] == agent_id]
        for child in children:
            descendants.update(get_all_descendants(child['agent_id'], executions))
        return descendants

    # Get all agents in this tree
    tree_agent_ids = get_all_descendants(root_id, all_executions)

    running_tasks = await _get_running_tasks()
    stopped_ids = []

    # Cancel tasks that belong to this tree
    for agent_id, task in running_tasks.items():
        if agent_id in tree_agent_ids and not task.done():
            task.cancel()
            stopped_ids.append(agent_id)

    # Mark running agents in this tree as completed in database
    for exec_info in all_executions:
        if exec_info['agent_id'] in tree_agent_ids and exec_info['completed_at'] is None:
            db.complete_agent_execution(exec_info['agent_id'])
            if exec_info['agent_id'] not in stopped_ids:
                stopped_ids.append(exec_info['agent_id'])

    # Remove stopped tasks from tracking
    async with _tasks_lock:
        for agent_id in stopped_ids:
            _running_tasks.pop(agent_id, None)

    return StopAllResponse(
        stopped_count=len(stopped_ids),
        agent_ids=stopped_ids,
        message=f"Stopped {len(stopped_ids)} agent(s) in execution tree"
    )


@router.get("/tools")
async def list_tools():
    """List all available tools."""
    tool_loader, _ = get_loaders()

    tools = []
    for tool_name, tool in tool_loader.get_all_tools().items():
        tools.append({
            "name": tool_name,
            "description": tool.description
        })

    return tools


def reset_loaders():
    """Reset loaders to force reload of agents/tools."""
    global _tool_loader, _agent_loader
    _tool_loader = None
    _agent_loader = None


@router.get("/agents/{agent_name}/detail", response_model=AgentDetail)
async def get_agent_detail(agent_name: str):
    """Get detailed information about an agent including system prompt."""
    agents_dir = get_agents_dir()
    agent_dir = agents_dir / agent_name

    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    description_file = agent_dir / "description.txt"
    system_prompt_file = agent_dir / "system_prompt.txt"
    tools_file = agent_dir / "tools.txt"

    description = description_file.read_text(encoding='utf-8').strip() if description_file.exists() else ""
    system_prompt = system_prompt_file.read_text(encoding='utf-8') if system_prompt_file.exists() else ""
    tools = []
    if tools_file.exists():
        tools = [line.strip() for line in tools_file.read_text(encoding='utf-8').splitlines() if line.strip()]

    return AgentDetail(
        name=agent_name,
        description=description,
        system_prompt=system_prompt,
        tools=tools
    )


@router.post("/agents", response_model=AgentDetail)
async def create_agent(request: CreateAgentRequest):
    """Create a new agent."""
    agents_dir = get_agents_dir()
    agent_dir = agents_dir / request.name

    if agent_dir.exists():
        raise HTTPException(status_code=400, detail=f"Agent '{request.name}' already exists")

    # Validate agent name (alphanumeric and underscores only)
    if not request.name.replace('_', '').replace('-', '').isalnum():
        raise HTTPException(status_code=400, detail="Agent name can only contain letters, numbers, underscores and hyphens")

    try:
        agent_dir.mkdir(parents=True, exist_ok=True)

        (agent_dir / "description.txt").write_text(request.description, encoding='utf-8')
        (agent_dir / "system_prompt.txt").write_text(request.system_prompt, encoding='utf-8')
        (agent_dir / "tools.txt").write_text('\n'.join(request.tools), encoding='utf-8')

        # Reset loaders to pick up new agent
        reset_loaders()

        return AgentDetail(
            name=request.name,
            description=request.description,
            system_prompt=request.system_prompt,
            tools=request.tools
        )
    except Exception as e:
        # Clean up on failure
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.put("/agents/{agent_name}", response_model=AgentDetail)
async def update_agent(agent_name: str, request: UpdateAgentRequest):
    """Update an existing agent."""
    agents_dir = get_agents_dir()
    agent_dir = agents_dir / agent_name

    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    try:
        (agent_dir / "description.txt").write_text(request.description, encoding='utf-8')
        (agent_dir / "system_prompt.txt").write_text(request.system_prompt, encoding='utf-8')
        (agent_dir / "tools.txt").write_text('\n'.join(request.tools), encoding='utf-8')

        # Reset loaders to pick up changes
        reset_loaders()

        return AgentDetail(
            name=agent_name,
            description=request.description,
            system_prompt=request.system_prompt,
            tools=request.tools
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")


@router.delete("/agents/{agent_name}")
async def delete_agent(agent_name: str):
    """Delete an agent."""
    agents_dir = get_agents_dir()
    agent_dir = agents_dir / agent_name

    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    try:
        shutil.rmtree(agent_dir)

        # Reset loaders to reflect deletion
        reset_loaders()

        return {"message": f"Agent '{agent_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")

"""
Agent management API endpoints.
"""
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...core.agent import AgentLoader
from ...core.database import get_database
from ...core.project import ProjectManager
from ...core.prompts import PromptLoader
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


# Per-project loader cache
_project_loaders: Dict[str, Tuple[ToolLoader, AgentLoader, PromptLoader]] = {}


def get_project_manager() -> ProjectManager:
    """Get ProjectManager instance."""
    current_dir = Path.cwd()

    # Find user directory
    if (current_dir / "user").exists():
        user_dir = current_dir / "user"
    elif (current_dir.parent / "user").exists():
        user_dir = current_dir.parent / "user"
    else:
        user_dir = current_dir / "user"

    db = get_database()
    return ProjectManager(user_dir, db)


def get_agents_dir(project_dir: str = "default") -> Path:
    """
    Get the agents directory path for a project.

    Args:
        project_dir: Project directory name

    Returns:
        Path to agents directory
    """
    pm = get_project_manager()
    return pm.get_agents_dir(project_dir)


def get_loaders(project_dir: str = "default") -> Tuple[ToolLoader, AgentLoader, PromptLoader]:
    """
    Get or initialize loaders for a specific project.

    Args:
        project_dir: Project directory name

    Returns:
        Tuple of (ToolLoader, AgentLoader, PromptLoader)
    """
    global _project_loaders

    # Return cached loaders if available
    if project_dir in _project_loaders:
        return _project_loaders[project_dir]

    # Create new loaders for this project
    pm = get_project_manager()

    # Get project-specific directories (with fallback for tools/prompts)
    tools_dir = str(pm.get_tools_dir(project_dir))
    agents_dir = str(pm.get_agents_dir(project_dir))
    prompts_dir = str(pm.get_prompts_dir(project_dir))

    # Create loaders
    tool_loader = ToolLoader(tools_dir=tools_dir)
    tool_loader.load_tools()

    prompt_loader = PromptLoader(prompts_dir=prompts_dir)

    agent_loader = AgentLoader(
        agents_dir=agents_dir,
        tool_loader=tool_loader,
        prompt_loader=prompt_loader,
        project_dir=project_dir
    )

    # Cache and return
    _project_loaders[project_dir] = (tool_loader, agent_loader, prompt_loader)
    return tool_loader, agent_loader, prompt_loader


def reset_loaders(project_dir: Optional[str] = None):
    """
    Clear loader cache for a project or all projects.

    Args:
        project_dir: Specific project to reset, or None to reset all
    """
    global _project_loaders

    if project_dir is None:
        # Clear all cached loaders
        _project_loaders.clear()
    else:
        # Clear specific project cache
        _project_loaders.pop(project_dir, None)


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
async def list_agents(project: str = Query("default")):
    """List all available agents for a project."""
    # Reset loaders to discover newly added agents from filesystem
    reset_loaders(project)
    _, agent_loader, _ = get_loaders(project)

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
async def get_agent(agent_name: str, project: str = Query("default")):
    """Get information about a specific agent."""
    _, agent_loader, _ = get_loaders(project)

    if not agent_loader.has_agent(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    config = agent_loader.get_agent_config(agent_name)
    return AgentInfo(
        name=agent_name,
        description=config.description,
        tools=config.tools
    )


@router.post("/agents/run", response_model=RunAgentResponse)
async def run_agent(request: RunAgentRequest, project: str = Query("default")):
    """
    Run an agent with a message.
    This starts the agent execution in the background.
    """
    _, agent_loader, _ = get_loaders(project)

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
async def stop_all_agents(project: str = Query("default")):
    """
    Stop all running agents in a project.
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
    all_executions = db.get_all_executions(project_dir=project)

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
async def stop_agents_by_root(root_id: str, project: str = Query("default")):
    """
    Stop all agents belonging to a specific execution tree (root and all children).

    Args:
        root_id: The root agent ID of the execution tree to stop
        project: Project directory (optional, for filtering)
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
async def list_tools(project: str = Query("default")):
    """List all available tools for a project."""
    tool_loader, _, _ = get_loaders(project)

    tools = []
    for tool_name, tool in tool_loader.get_all_tools().items():
        tools.append({
            "name": tool_name,
            "description": tool.description
        })

    return tools


@router.get("/agents/{agent_name}/detail", response_model=AgentDetail)
async def get_agent_detail(agent_name: str, project: str = Query("default")):
    """Get detailed information about an agent including system prompt."""
    agents_dir = get_agents_dir(project)
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
async def create_agent(request: CreateAgentRequest, project: str = Query("default")):
    """Create a new agent in a project."""
    agents_dir = get_agents_dir(project)
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
        reset_loaders(project)

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
async def update_agent(agent_name: str, request: UpdateAgentRequest, project: str = Query("default")):
    """Update an existing agent in a project."""
    agents_dir = get_agents_dir(project)
    agent_dir = agents_dir / agent_name

    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    try:
        (agent_dir / "description.txt").write_text(request.description, encoding='utf-8')
        (agent_dir / "system_prompt.txt").write_text(request.system_prompt, encoding='utf-8')
        (agent_dir / "tools.txt").write_text('\n'.join(request.tools), encoding='utf-8')

        # Reset loaders to pick up changes
        reset_loaders(project)

        return AgentDetail(
            name=agent_name,
            description=request.description,
            system_prompt=request.system_prompt,
            tools=request.tools
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")


@router.delete("/agents/{agent_name}")
async def delete_agent(agent_name: str, project: str = Query("default")):
    """Delete an agent from a project."""
    agents_dir = get_agents_dir(project)
    agent_dir = agents_dir / agent_name

    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    try:
        shutil.rmtree(agent_dir)

        # Reset loaders to reflect deletion
        reset_loaders(project)

        return {"message": f"Agent '{agent_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")

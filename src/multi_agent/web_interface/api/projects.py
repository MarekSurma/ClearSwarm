"""
Project management API endpoints.
"""
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...core.database import get_database
from ...core.project import ProjectManager


router = APIRouter()


class CreateProjectRequest(BaseModel):
    """Request model for creating a new project."""
    name: str
    create_tools: bool = False
    create_prompts: bool = False


class CloneProjectRequest(BaseModel):
    """Request model for cloning a project."""
    source_project_dir: str
    new_name: str
    clone_tools: bool = False
    clone_prompts: bool = False


class ProjectInfo(BaseModel):
    """Project information response model."""
    project_name: str
    project_dir: str
    created_at: str


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


@router.get("/projects", response_model=List[ProjectInfo])
async def list_projects():
    """
    Get all projects.

    Returns:
        List of project information
    """
    try:
        pm = get_project_manager()
        projects = pm.list_projects()
        return projects
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing projects: {str(e)}"
        )


@router.post("/projects", response_model=ProjectInfo, status_code=status.HTTP_201_CREATED)
async def create_project(request: CreateProjectRequest):
    """
    Create a new project.

    Args:
        request: Project creation request with name and options

    Returns:
        Created project information

    Raises:
        400: If project already exists
        500: For other errors
    """
    try:
        pm = get_project_manager()
        project = pm.create_project(
            name=request.name,
            create_tools=request.create_tools,
            create_prompts=request.create_prompts
        )
        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating project: {str(e)}"
        )


@router.post("/projects/clone", response_model=ProjectInfo, status_code=status.HTTP_201_CREATED)
async def clone_project(request: CloneProjectRequest):
    """
    Clone an existing project.

    Args:
        request: Project clone request with source and new name

    Returns:
        Created project information

    Raises:
        400: If source doesn't exist or new project already exists
        500: For other errors
    """
    try:
        pm = get_project_manager()
        project = pm.clone_project(
            source_dir=request.source_project_dir,
            new_name=request.new_name,
            clone_tools=request.clone_tools,
            clone_prompts=request.clone_prompts
        )
        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cloning project: {str(e)}"
        )


@router.delete("/projects/{project_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_name: str):
    """
    Delete a project.

    Args:
        project_name: Name of the project to delete

    Raises:
        400: If trying to delete default project or project not found
        500: For other errors
    """
    try:
        pm = get_project_manager()
        pm.delete_project(project_name)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting project: {str(e)}"
        )

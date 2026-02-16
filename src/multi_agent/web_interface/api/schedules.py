"""
REST API endpoints for schedule management.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

from ...core.database import get_database

router = APIRouter()


# Pydantic models
class CreateScheduleRequest(BaseModel):
    """Request model for creating a schedule."""
    name: str = Field(..., description="Name of the schedule")
    agent_name: str = Field(..., description="Name of the agent to run")
    message: str = Field(default="", description="Message to send to the agent")
    schedule_type: Literal['minutes', 'hours', 'weeks'] = Field(
        ..., description="Type of schedule interval"
    )
    interval_value: int = Field(..., ge=1, description="Interval value (must be >= 1)")
    start_from: Optional[str] = Field(
        None, description="ISO datetime to start from (None = now)"
    )
    enabled: bool = Field(default=True, description="Whether schedule is enabled")


class UpdateScheduleRequest(BaseModel):
    """Request model for updating a schedule."""
    name: Optional[str] = None
    agent_name: Optional[str] = None
    message: Optional[str] = None
    schedule_type: Optional[Literal['minutes', 'hours', 'weeks']] = None
    interval_value: Optional[int] = Field(None, ge=1)
    start_from: Optional[str] = None
    enabled: Optional[bool] = None


class ScheduleInfo(BaseModel):
    """Response model for schedule information."""
    schedule_id: str
    name: str
    project_dir: str
    agent_name: str
    message: str
    schedule_type: str
    interval_value: int
    start_from: Optional[str]
    enabled: bool
    last_run_at: Optional[str]
    next_run_at: Optional[str]
    created_at: str
    updated_at: str


@router.get("/schedules", response_model=List[ScheduleInfo])
async def get_schedules(
    project: str = Query(default="default", description="Project directory")
):
    """Get all schedules for a project."""
    db = get_database()
    schedules = db.get_all_schedules(project_dir=project)
    return schedules


@router.get("/schedules/{schedule_id}", response_model=ScheduleInfo)
async def get_schedule(schedule_id: str):
    """Get a specific schedule by ID."""
    db = get_database()
    schedule = db.get_schedule(schedule_id)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return schedule


@router.post("/schedules", response_model=ScheduleInfo)
async def create_schedule(
    request: CreateScheduleRequest,
    project: str = Query(default="default", description="Project directory")
):
    """Create a new schedule."""
    db = get_database()

    try:
        schedule = db.create_schedule(
            name=request.name,
            project_dir=project,
            agent_name=request.agent_name,
            message=request.message,
            schedule_type=request.schedule_type,
            interval_value=request.interval_value,
            start_from=request.start_from,
            enabled=request.enabled
        )
        return schedule
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/schedules/{schedule_id}", response_model=ScheduleInfo)
async def update_schedule(schedule_id: str, request: UpdateScheduleRequest):
    """Update a schedule."""
    db = get_database()

    # Convert request to dict, excluding None values
    updates = request.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        schedule = db.update_schedule(schedule_id, **updates)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return schedule
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """Delete a schedule."""
    db = get_database()
    deleted = db.delete_schedule(schedule_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return {"status": "deleted", "schedule_id": schedule_id}


@router.post("/schedules/{schedule_id}/toggle", response_model=ScheduleInfo)
async def toggle_schedule(schedule_id: str):
    """Toggle a schedule's enabled status."""
    db = get_database()

    schedule = db.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Toggle enabled status
    updated = db.update_schedule(schedule_id, enabled=not schedule['enabled'])
    return updated

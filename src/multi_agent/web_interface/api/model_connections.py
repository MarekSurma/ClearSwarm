"""
REST API endpoints for model connection management.

Model connections are global (system-wide), OpenAI-API-compatible provider
definitions. Each holds a name, base URL, model, and an API key. The API key is
write-only: it is stored encrypted and never returned by any endpoint.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from openai import OpenAI

from ...core.database import get_database

router = APIRouter()


# Pydantic models
class CreateModelConnectionRequest(BaseModel):
    """Request model for creating a connection."""
    name: str = Field(..., description="Unique connection name")
    base_url: str = Field(..., description="OpenAI-compatible base URL")
    model: str = Field(default="", description="Model identifier")
    api_key: str = Field(default="", description="API key (stored encrypted, write-only)")


class UpdateModelConnectionRequest(BaseModel):
    """Request model for updating a connection. Omitted/blank api_key keeps the current key."""
    name: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


class CloneModelConnectionRequest(BaseModel):
    """Request model for cloning a connection."""
    new_name: str = Field(..., description="Name for the cloned connection")


class ListModelsRequest(BaseModel):
    """Request to list available models from a provider.

    Provide either ``connection_id`` (use the stored key) or an inline
    ``api_key`` + ``base_url`` (for a connection that isn't saved yet).
    """
    connection_id: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class ModelConnectionInfo(BaseModel):
    """Response model for a connection (never includes the API key)."""
    connection_id: str
    name: str
    base_url: str
    model: str
    has_api_key: bool
    created_at: str
    updated_at: str


class ListModelsResponse(BaseModel):
    models: List[str]


@router.get("/model-connections", response_model=List[ModelConnectionInfo])
async def get_model_connections():
    """Get all model connections."""
    db = get_database()
    return db.get_all_model_connections()


@router.get("/model-connections/{connection_id}", response_model=ModelConnectionInfo)
async def get_model_connection(connection_id: str):
    """Get a specific model connection by ID."""
    db = get_database()
    connection = db.get_model_connection(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection


@router.post("/model-connections", response_model=ModelConnectionInfo)
async def create_model_connection(request: CreateModelConnectionRequest):
    """Create a new model connection."""
    db = get_database()
    try:
        return db.create_model_connection(
            name=request.name,
            base_url=request.base_url,
            model=request.model,
            api_key=request.api_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/model-connections/{connection_id}", response_model=ModelConnectionInfo)
async def update_model_connection(
    connection_id: str, request: UpdateModelConnectionRequest
):
    """Update a model connection. A blank api_key keeps the existing key."""
    db = get_database()

    updates = request.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        connection = db.update_model_connection(connection_id, **updates)
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        return connection
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/model-connections/{connection_id}")
async def delete_model_connection(connection_id: str):
    """Delete a model connection."""
    db = get_database()
    deleted = db.delete_model_connection(connection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"status": "deleted", "connection_id": connection_id}


@router.post("/model-connections/{connection_id}/clone", response_model=ModelConnectionInfo)
async def clone_model_connection(
    connection_id: str, request: CloneModelConnectionRequest
):
    """Clone a connection under a new name, preserving the API key."""
    db = get_database()
    try:
        connection = db.clone_model_connection(connection_id, request.new_name)
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        return connection
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/model-connections/list-models", response_model=ListModelsResponse)
async def list_models(request: ListModelsRequest):
    """List available models from a provider, testing the credentials."""
    db = get_database()

    api_key = request.api_key
    base_url = request.base_url

    # When a saved connection is referenced, use its stored (decrypted) key and URL.
    if request.connection_id:
        connection = db.get_model_connection(request.connection_id)
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        if not base_url:
            base_url = connection["base_url"]
        if not api_key:
            api_key = db.get_model_connection_api_key(request.connection_id)

    if not base_url:
        raise HTTPException(status_code=400, detail="base_url is required")

    try:
        client = OpenAI(api_key=api_key or "", base_url=base_url)
        models = client.models.list()
        model_ids = sorted(m.id for m in models.data)
        return {"models": model_ids}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not list models: {e}")

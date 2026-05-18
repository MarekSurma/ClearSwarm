"""
Per-project graph layout persistence.

Stores vis-network node positions on disk so the visualizer can restore
a stabilized layout instantly instead of re-running physics every time.
"""
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from .projects import get_project_manager


router = APIRouter()


ALLOWED_LAYOUTS = {"physics", "hierarchical"}
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-:.]+$")


class Position(BaseModel):
    x: float
    y: float


class GraphLayoutBody(BaseModel):
    positions: Dict[str, Position] = Field(default_factory=dict)


class GraphLayoutResponse(BaseModel):
    positions: Dict[str, Position] = Field(default_factory=dict)


def _layout_dir(project_dir: str) -> Path:
    pm = get_project_manager()
    base = pm.get_project_base_dir(project_dir).resolve()
    if not base.exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_dir}' not found")
    return base / ".graph-layouts"


def _layout_file(project_dir: str, agent_id: str, layout: str) -> Path:
    if layout not in ALLOWED_LAYOUTS:
        raise HTTPException(status_code=400, detail=f"Invalid layout '{layout}'")
    if not _SAFE_NAME_RE.match(agent_id):
        raise HTTPException(status_code=400, detail="Invalid agent_id")
    if not _SAFE_NAME_RE.match(project_dir):
        raise HTTPException(status_code=400, detail="Invalid project")
    return _layout_dir(project_dir) / f"{agent_id}__{layout}.json"


@router.get(
    "/executions/{agent_id}/graph/layout",
    response_model=GraphLayoutResponse,
)
def get_graph_layout(
    agent_id: str,
    project: str = Query(...),
    layout: str = Query(...),
):
    path = _layout_file(project, agent_id, layout)
    if not path.exists():
        return GraphLayoutResponse(positions={})
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return GraphLayoutResponse(positions={})
    raw = data.get("positions", {}) if isinstance(data, dict) else {}
    positions: Dict[str, Position] = {}
    for node_id, pos in raw.items():
        if isinstance(pos, dict) and "x" in pos and "y" in pos:
            try:
                positions[node_id] = Position(x=float(pos["x"]), y=float(pos["y"]))
            except (TypeError, ValueError):
                continue
    return GraphLayoutResponse(positions=positions)


@router.put(
    "/executions/{agent_id}/graph/layout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def put_graph_layout(
    agent_id: str,
    body: GraphLayoutBody,
    project: str = Query(...),
    layout: str = Query(...),
):
    path = _layout_file(project, agent_id, layout)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "positions": {nid: {"x": p.x, "y": p.y} for nid, p in body.positions.items()},
    }

    # Atomic write: tmp file in same dir, then os.replace.
    fd, tmp_name = tempfile.mkstemp(prefix=".layout-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return None


@router.delete(
    "/executions/{agent_id}/graph/layout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_graph_layout(
    agent_id: str,
    project: str = Query(...),
    layout: Optional[str] = Query(None),
):
    # If layout is omitted, drop both variants.
    layouts = [layout] if layout else list(ALLOWED_LAYOUTS)
    for lay in layouts:
        path = _layout_file(project, agent_id, lay)
        try:
            path.unlink()
        except FileNotFoundError:
            continue
    return None

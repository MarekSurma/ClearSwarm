"""
Project files API endpoints.

Each project has its own files directory at <repo_root>/output/<project_dir>/.
Exposes listing, uploading, downloading, and deleting files within that root.
"""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .projects import get_project_manager


router = APIRouter()


class FileEntry(BaseModel):
    name: str
    path: str  # relative path from project root, posix-style
    is_dir: bool
    size: int  # bytes; 0 for directories


class ListResponse(BaseModel):
    project_dir: str
    path: str  # relative path that was listed
    entries: List[FileEntry]


class DeleteRequest(BaseModel):
    paths: List[str]


def _project_files_root(project_dir: str) -> Path:
    """Return the root directory for a given project's files (output/<project_dir>)."""
    pm = get_project_manager()
    # output/ sits at the repo root, next to user/
    repo_root = pm.user_dir.parent
    root = (repo_root / "output" / project_dir).resolve()
    # Make sure the project exists in the DB
    projects = pm.db.get_all_projects()
    valid_dirs = {p["project_dir"] for p in projects}
    if project_dir not in valid_dirs:
        raise HTTPException(status_code=404, detail=f"Project '{project_dir}' not found")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_safe(root: Path, rel_path: str) -> Path:
    """Resolve rel_path against root, ensuring the result stays inside root."""
    rel_path = (rel_path or "").strip().lstrip("/")
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path (outside project directory)")
    return candidate


@router.get("/projects/{project_dir}/files", response_model=ListResponse)
async def list_project_files(project_dir: str, path: str = Query("")):
    """List files and directories under the given relative path inside the project."""
    root = _project_files_root(project_dir)
    target = _resolve_safe(root, path)

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {path}")

    entries: List[FileEntry] = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        try:
            rel = child.resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        is_dir = child.is_dir()
        size = 0
        if not is_dir:
            try:
                size = child.stat().st_size
            except OSError:
                size = 0
        entries.append(FileEntry(name=child.name, path=rel, is_dir=is_dir, size=size))

    rel_listed = "" if target == root else target.resolve().relative_to(root).as_posix()
    return ListResponse(project_dir=project_dir, path=rel_listed, entries=entries)


@router.post("/projects/{project_dir}/files/upload", status_code=status.HTTP_201_CREATED)
async def upload_project_file(
    project_dir: str,
    path: str = Form(""),
    file: UploadFile = File(...),
):
    """Upload a file into the given relative directory of the project."""
    root = _project_files_root(project_dir)
    target_dir = _resolve_safe(root, path)
    target_dir.mkdir(parents=True, exist_ok=True)
    if not target_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {path}")

    filename = Path(file.filename or "upload").name
    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    dest = _resolve_safe(root, (Path(path) / filename).as_posix() if path else filename)
    contents = await file.read()
    dest.write_bytes(contents)
    return {"path": dest.resolve().relative_to(root).as_posix(), "size": len(contents)}


_PREVIEW_MAX_BYTES = 2 * 1024 * 1024  # 2 MB safety cap for text preview


@router.get("/projects/{project_dir}/files/content")
async def get_project_file_content(project_dir: str, path: str = Query(...)):
    """Return text content for a file under the project (for preview)."""
    root = _project_files_root(project_dir)
    target = _resolve_safe(root, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if target.is_dir():
        raise HTTPException(status_code=400, detail="Cannot preview a directory")

    size = target.stat().st_size
    truncated = False
    read_size = size
    if size > _PREVIEW_MAX_BYTES:
        read_size = _PREVIEW_MAX_BYTES
        truncated = True

    try:
        with target.open("rb") as fh:
            raw = fh.read(read_size)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")

    return {
        "path": target.resolve().relative_to(root).as_posix(),
        "name": target.name,
        "size": size,
        "truncated": truncated,
        "content": text,
    }


@router.get("/projects/{project_dir}/files/download")
async def download_project_file(project_dir: str, path: str = Query(...)):
    """Download a single file from the project."""
    root = _project_files_root(project_dir)
    target = _resolve_safe(root, path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if target.is_dir():
        raise HTTPException(status_code=400, detail="Cannot download a directory")
    return FileResponse(path=target, filename=target.name, media_type="application/octet-stream")


@router.post("/projects/{project_dir}/files/delete")
async def delete_project_files(project_dir: str, request: DeleteRequest):
    """Delete one or more files/directories from the project."""
    import shutil

    root = _project_files_root(project_dir)
    deleted: List[str] = []
    errors: List[dict] = []

    for rel in request.paths:
        try:
            target = _resolve_safe(root, rel)
            if target == root:
                errors.append({"path": rel, "error": "Cannot delete project root"})
                continue
            if not target.exists():
                errors.append({"path": rel, "error": "Not found"})
                continue
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            deleted.append(rel)
        except HTTPException as e:
            errors.append({"path": rel, "error": e.detail})
        except Exception as e:
            errors.append({"path": rel, "error": str(e)})

    return {"deleted": deleted, "errors": errors}

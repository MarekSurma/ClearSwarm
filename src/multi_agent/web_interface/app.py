"""
FastAPI application for multi-agent web interface.
Provides REST API and WebSocket endpoints for agent management and monitoring.
"""
import asyncio
import signal
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from .api import agents, executions, websocket, projects
from ..core.llm_client import request_shutdown, reset_shutdown
from ..core.database import get_database
from ..core.project import ProjectManager

# Determine which directory to serve frontend from
# Priority: dist/ (Vue build output) > static/ (legacy vanilla JS)
_DIST_DIR = Path(__file__).parent / "dist"
_STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR = _DIST_DIR if _DIST_DIR.exists() else _STATIC_DIR


def _signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM by requesting LLM shutdown."""
    print("\n[Received shutdown signal, stopping LLM streams...]")
    request_shutdown()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Startup
    print("Starting multi-agent web interface...")
    print(f"Static files directory: {STATIC_DIR}")

    # Validate default project exists
    current_dir = Path.cwd()
    if (current_dir / "user").exists():
        user_dir = current_dir / "user"
    elif (current_dir.parent / "user").exists():
        user_dir = current_dir.parent / "user"
    else:
        user_dir = current_dir / "user"

    db = get_database()
    pm = ProjectManager(user_dir, db)

    try:
        pm.validate_default_exists()
        print("Default project validated successfully")
    except ValueError as e:
        print(f"WARNING: {e}")

    # Reset shutdown flag on startup
    reset_shutdown()

    # Register signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    yield

    # Shutdown
    print("Shutting down web interface...")
    request_shutdown()


# Create FastAPI app
app = FastAPI(
    title="ClearSwarm Web Interface",
    description="Web interface for managing and monitoring multi-agent system",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routers
app.include_router(agents.router, prefix="/api", tags=["agents"])
app.include_router(executions.router, prefix="/api", tags=["executions"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main HTML page."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding='utf-8')
    return "<h1>ClearSwarm Web Interface</h1><p>index.html not found</p>"


@app.get("/visual-editor", response_class=HTMLResponse)
async def visual_editor_spa():
    """SPA catch-all for Vue Router /visual-editor route."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding='utf-8')
    return "<h1>ClearSwarm Web Interface</h1><p>index.html not found</p>"


@app.get("/health")
async def health_check():
    """Health check endpoint with debug info."""
    import os

    cwd = Path.cwd()

    return {
        "status": "healthy",
        "service": "multi-agent-web-interface",
        "debug": {
            "cwd": str(cwd),
            "user_agents_exists": (cwd / "user" / "agents").exists(),
            "user_tools_exists": (cwd / "user" / "tools").exists(),
            "agents_db_exists": (cwd / "agents.db").exists(),
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

#!/bin/bash

# Start script for Multi-Agent Web Interface

echo "=========================================="
echo "  ClearSwarm - Web Interface"
echo "=========================================="
echo ""
echo "TIP: For frontend development with hot-reload:"
echo "  1. Run this script for the API server"
echo "  2. In another terminal: make frontend-dev"
echo "  3. Open http://localhost:5173 (Vite dev server)"
echo ""

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "⚠️  FastAPI not found. Installing dependencies..."
    pip install -r requirements.txt
    echo ""
fi

# Default values
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-true}"

echo "Starting web interface..."
echo "Host: $HOST"
echo "Port: $PORT"
echo "Reload: $RELOAD"
echo ""
echo "Open in browser: http://localhost:$PORT"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Get script directory to ensure we're in the right place
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Start the server from project root (not src/)
# This ensures user/agents and user/tools are accessible
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH}"

if [ "$RELOAD" = "true" ]; then
    uvicorn multi_agent.web_interface.app:app --reload --host "$HOST" --port "$PORT"
else
    uvicorn multi_agent.web_interface.app:app --host "$HOST" --port "$PORT"
fi

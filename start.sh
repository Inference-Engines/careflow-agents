#!/bin/bash
# start.sh — CareFlow single-container startup
# Runs two processes inside one Cloud Run container:
#   1. adk api_server  — the ADK agent runtime   (port 8000, internal only)
#   2. uvicorn server  — FastAPI proxy + React UI (port $PORT, Cloud Run entry)

set -e

echo "========================================="
echo " CareFlow AI — Single Container Startup"
echo "========================================="

# ── 0. Start MCP SSE Server in background ────────────────────────────────────
echo "[0/3] Starting MCP SSE Server on 127.0.0.1:9000 ..."
PORT=9000 python /app/mcp_server/server.py &
MCP_PID=$!
sleep 2
export MCP_SERVER_URL=http://localhost:9000/sse

# ── 1. Start ADK agent server in background ──────────────────────────────────
echo "[1/3] Starting ADK api_server on 127.0.0.1:8000 ..."
adk api_server --host 127.0.0.1 --port 8000 /app &
ADK_PID=$!

# ── 2. Wait for ADK to be ready (max 60 s) ───────────────────────────────────
echo "Waiting for ADK server to initialize (max 60 s)..."
for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8000/list-apps > /dev/null 2>&1; then
        echo "ADK server is ready (attempt $i)."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: ADK server did not become ready within 60 s. Aborting."
        kill "$ADK_PID" 2>/dev/null || true
        exit 1
    fi
    sleep 2
done

# ── 3. Start FastAPI proxy / static UI server ────────────────────────────────
echo "[2/3] Starting FastAPI proxy + React UI on 0.0.0.0:${PORT:-8080} ..."
cd /app
export PYTHONPATH=/app:${PYTHONPATH}
exec uvicorn ui.server:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --log-level info

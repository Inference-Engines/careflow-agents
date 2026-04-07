#!/bin/bash
# ============================================================================
# CareFlow — 로컬 개발 서버 통합 시작 / Local Dev Startup
# ============================================================================
# 사용법: bash start-local.sh       (시작)
#         bash start-local.sh stop  (종료)
# ============================================================================

cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"

if [ -f .env ]; then
    set -a; source .env; set +a
fi

stop_all() {
    echo "Stopping all CareFlow servers..."
    pkill -f "adk web" 2>/dev/null
    pkill -f "uvicorn ui.server" 2>/dev/null
    pkill -f "mcp_server/server.py" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    sleep 2
    echo "All stopped."
}

[ "$1" = "stop" ] && { stop_all; exit 0; }

stop_all
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

echo ""
echo "============================================"
echo "  CareFlow — Starting All Servers"
echo "============================================"

# 1. MCP SSE Server (9000)
echo "[1/4] MCP SSE Server..."
python mcp_server/server.py &
sleep 2
curl -s http://localhost:9000/health > /dev/null && echo "  OK: MCP (9000)" || echo "  FAIL: MCP"

# 2. ADK Server (8000)
echo "[2/4] ADK Server..."
adk web --port 8000 &
sleep 6
curl -s http://localhost:8000/list-apps > /dev/null && echo "  OK: ADK (8000)" || echo "  FAIL: ADK"

# 3. FastAPI Proxy (8001)
echo "[3/4] FastAPI Proxy..."
python -m uvicorn ui.server:app --host 0.0.0.0 --port 8001 --log-level warning &
sleep 3
curl -s http://localhost:8001/api/health > /dev/null && echo "  OK: Proxy (8001)" || echo "  FAIL: Proxy"

# 4. Vite UI (3000)
echo "[4/4] Vite UI..."
cd ui && npm run dev &
cd ..
sleep 4
curl -s http://localhost:3000/ > /dev/null && echo "  OK: Vite (3000)" || echo "  FAIL: Vite"

echo ""
echo "============================================"
echo "  http://localhost:3000"
echo "  Stop: bash start-local.sh stop"
echo "============================================"

wait

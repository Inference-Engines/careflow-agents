"""
server.py — CareFlow FastAPI Proxy Server

Responsibilities:
  1. Proxy /api/session  →  ADK server POST session creation
  2. Proxy /api/run      →  ADK server SSE streaming run endpoint
  3. Serve Vite build (dist/) as static files (production)

Environment variables:
  ADK_BASE_URL  — ADK server address  (default: http://localhost:8000)
  APP_NAME      — ADK app name        (default: careflow)
  PORT          — port to listen on   (default: 8001)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

ADK_BASE_URL = os.getenv("ADK_BASE_URL", "http://localhost:8000")
APP_NAME = os.getenv("APP_NAME", "careflow")

# ─────────────────────────────────────────────────────────────────────────────
# Shared async HTTP client (reused across requests for connection pooling)
# ─────────────────────────────────────────────────────────────────────────────

http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    global http_client
    http_client = httpx.AsyncClient(base_url=ADK_BASE_URL, timeout=120.0)
    yield
    await http_client.aclose()


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="CareFlow Proxy", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production to your Cloud Run frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────────────────────────────────────


@app.post("/api/session")
async def create_session(request: Request):
    """Create an ADK session.

    Body: { app_name, user_id, session_id }
    ADK endpoint: POST /apps/{app_name}/users/{user_id}/sessions/{session_id}
    """
    assert http_client is not None

    body = await request.json()
    app_name = body.get("app_name", APP_NAME)
    user_id = body.get("user_id", "default-user")
    session_id = body.get("session_id", "default-session")

    adk_url = f"/apps/{app_name}/users/{user_id}/sessions/{session_id}"

    resp = await http_client.post(adk_url, json={})
    return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.post("/api/run")
async def run_agent(request: Request):
    """Proxy an agent run request, streaming back SSE events.

    Body follows ADK RunRequest schema:
      { app_name, user_id, session_id, new_message, streaming }
    """
    assert http_client is not None

    body = await request.json()

    async def event_stream():
        async with http_client.stream("POST", "/run", json=body) as adk_resp:
            async for chunk in adk_resp.aiter_bytes():
                yield chunk

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering on Cloud Run
        },
    )


@app.get("/api/health")
async def health():
    """Health check — also forwards to ADK to verify connectivity."""
    assert http_client is not None
    try:
        resp = await http_client.get("/list-apps", timeout=5.0)
        return {"status": "ok", "adk_apps": resp.json()}
    except Exception as exc:
        return JSONResponse({"status": "degraded", "error": str(exc)}, status_code=503)


# ─────────────────────────────────────────────────────────────────────────────
# Static frontend (production only — dist/ built by `npm run build`)
# ─────────────────────────────────────────────────────────────────────────────

_dist = os.path.join(os.path.dirname(__file__), "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")

# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# CareFlow AI -- Single Container Dockerfile (Cloud Run)
#
# Architecture inside the container:
#   Port 8000 (internal) <- adk api_server  (CareFlow multi-agent system)
#   Port 8080 (Cloud Run) <- uvicorn server.py  (FastAPI proxy + React UI)
#
# Build & push:
#   gcloud builds submit --tag gcr.io/agent-testing-adk-002/careflow
#
# Run locally:
#   docker run -p 8080:8080 \
#     -e GOOGLE_GENAI_USE_VERTEXAI=TRUE \
#     -e GOOGLE_CLOUD_PROJECT=agent-testing-adk-002 \
#     -e GOOGLE_CLOUD_LOCATION=us-central1 \
#     gcr.io/agent-testing-adk-002/careflow
# ---------------------------------------------------------------------------

# == Stage 1: Build React / Vite frontend ==================================
FROM node:20-slim AS frontend-builder

WORKDIR /build

# Install deps first (layer-cached unless package.json changes)
COPY ui/package.json ui/package-lock.json ./
RUN npm ci --prefer-offline

# Copy source and build
COPY ui/ ./
RUN npm run build
# Output: /build/dist/


# == Stage 2: Python runtime ================================================
FROM python:3.11-slim

WORKDIR /app

# System packages:
#   curl -- used by start.sh to health-check ADK before starting uvicorn
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# -- Python dependencies ----------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -- Application source ------------------------------------------------------
# Agent packages (all sub-agents, db, mcp, schemas, etc.)
COPY careflow/ careflow/

# MCP Toolbox tool definitions (referenced by agent tools at runtime)
COPY tools.yaml .

# OAuth credentials for Gmail / Google Calendar MCP integrations
# These are baked into the image for the hackathon demo.
# In production, use Cloud Run secrets or Secret Manager instead.
COPY oauth_token.json .
COPY client_secret.json .

# FastAPI proxy server (ui/server.py)
# server.py uses __file__ to locate ui/dist/, so keep it inside ui/
COPY ui/server.py ui/server.py

# Built React app (from Stage 1) -> ui/dist/  (server.py mounts this as static)
COPY --from=frontend-builder /build/dist/ ui/dist/

# Startup script (runs ADK + uvicorn)
COPY start.sh .
RUN chmod +x start.sh

# -- Environment defaults ----------------------------------------------------
# ADK_BASE_URL   : server.py proxies /api/* here (ADK runs internally)
# APP_NAME       : ADK app name -- must match the Python package found by ADK
# PORT           : Cloud Run injects this; uvicorn binds to it
# PYTHONPATH     : ensures `import careflow` works from anywhere
ENV ADK_BASE_URL=http://localhost:8000 \
    APP_NAME=careflow \
    PORT=8080 \
    PYTHONPATH=/app

# Cloud Run requirement: must listen on $PORT
EXPOSE 8080

# -- Health check ------------------------------------------------------------
# /api/health checks both FastAPI and forwarding to ADK
HEALTHCHECK --interval=15s --timeout=10s --start-period=45s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/api/health || exit 1

# -- Entrypoint --------------------------------------------------------------
CMD ["/app/start.sh"]

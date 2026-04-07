# CareFlow Cloud Run Deployment Guide

Single-container deployment: ADK agent server (port 8000, internal) + FastAPI proxy with React UI (port 8080, Cloud Run).

## Prerequisites

- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- Project: **agent-testing-adk-002**
- Region: **us-central1**
- Docker is NOT required locally (Cloud Build handles it)

## Step 1: Set the active project

```bash
gcloud config set project agent-testing-adk-002
```

## Step 2: Enable required APIs (first time only)

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com
```

## Step 3: Build and push the container image

From the `careflow-agents/` directory:

```bash
gcloud builds submit --tag gcr.io/agent-testing-adk-002/careflow
```

This runs the multi-stage Dockerfile in Cloud Build:
1. Builds the React UI with Vite (node:20-slim)
2. Installs Python deps + copies agent code (python:3.11-slim)
3. Pushes the final image to GCR

Typical build time: 3-5 minutes.

## Step 4: Deploy to Cloud Run

```bash
gcloud run deploy careflow \
  --image gcr.io/agent-testing-adk-002/careflow \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --timeout=300 \
  --min-instances=0 \
  --max-instances=3 \
  --set-env-vars="\
GOOGLE_GENAI_USE_VERTEXAI=True,\
GOOGLE_CLOUD_PROJECT=agent-testing-adk-002,\
GOOGLE_CLOUD_LOCATION=us-central1,\
ALLOYDB_CONN_URI=<ALLOYDB_CONN_URI_FROM_ENV>,\
DB_HOST=<DB_HOST>,\
DB_NAME=careflow,\
DB_USER=postgres,\
DB_PASSWORD=<DB_PASSWORD>,\
USDA_API_KEY=DEMO_KEY,\
CAREFLOW_ROOT_MODEL=gemini-2.5-flash"
```

> **Note on secrets**: For a production deployment, use `--set-secrets` with
> Google Secret Manager instead of `--set-env-vars` for DB passwords and API
> keys. For the hackathon demo, plain env vars are acceptable.

## Step 5: Get the deployed URL

```bash
gcloud run services describe careflow \
  --region us-central1 \
  --format='value(status.url)'
```

The URL will look like: `https://careflow-XXXXX-uc.a.run.app`

## Step 6: Verify deployment

```bash
# Health check (tests both FastAPI and ADK connectivity)
curl https://careflow-XXXXX-uc.a.run.app/api/health

# Open the UI in your browser
open https://careflow-XXXXX-uc.a.run.app
```

## Redeploying after code changes

Just repeat Steps 3 and 4:

```bash
gcloud builds submit --tag gcr.io/agent-testing-adk-002/careflow
gcloud run deploy careflow \
  --image gcr.io/agent-testing-adk-002/careflow \
  --platform managed \
  --region us-central1
```

Cloud Run keeps existing env vars on redeployment, so you only need `--set-env-vars` on the first deploy (or when changing them).

## Troubleshooting

### Container fails to start

```bash
# Check Cloud Run logs
gcloud run services logs read careflow --region us-central1 --limit=50
```

Common issues:
- **ADK server timeout**: The start.sh script waits 60s for ADK. If it times out, increase `--memory` to 4Gi.
- **Module not found**: Ensure `PYTHONPATH=/app` is set (already in the Dockerfile).
- **AlloyDB connection refused**: The AlloyDB instance must allow connections from Cloud Run's egress IP. For the hackathon, the public IP (34.136.180.82) should work.

### Slow cold starts

Cloud Run cold starts can take 30-60s because ADK needs to initialize. Mitigation:
- Set `--min-instances=1` to keep one instance warm (costs ~$15/month).
- The `--timeout=300` flag gives the container 5 minutes to respond to the first request.

### View real-time logs

```bash
gcloud run services logs tail careflow --region us-central1
```

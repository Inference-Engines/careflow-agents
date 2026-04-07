#!/usr/bin/env bash
# ============================================================================
# Deploy CareFlow MCP SSE Server to Cloud Run
# Cloud Run에 CareFlow MCP SSE 서버를 배포하는 스크립트
# ============================================================================
#
# Usage:
#   cd mcp_server
#   bash deploy_cloudrun.sh
#
# Prerequisites:
#   - gcloud CLI authenticated
#   - GCP project set (gcloud config set project PROJECT_ID)
#   - oauth_token.json available in parent directory

set -euo pipefail

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
REGION="${GCP_REGION:-asia-northeast3}"
SERVICE_NAME="careflow-mcp-server"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=== CareFlow MCP Server — Cloud Run Deploy ==="
echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Service:  ${SERVICE_NAME}"
echo ""

# Copy oauth_token.json into build context
cp ../oauth_token.json ./oauth_token.json 2>/dev/null || {
    echo "ERROR: oauth_token.json not found in parent directory."
    echo "Run oauth_setup.py first."
    exit 1
}

# Build and push
echo ">>> Building container image..."
gcloud builds submit --tag "${IMAGE}" .

# Deploy
echo ">>> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --timeout 300

# Get URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region "${REGION}" \
    --format "value(status.url)")

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: ${SERVICE_URL}"
echo "SSE endpoint: ${SERVICE_URL}/sse"
echo "Health check: ${SERVICE_URL}/health"
echo ""
echo "Set this in your .env:"
echo "  MCP_SERVER_URL=${SERVICE_URL}/sse"

# Cleanup
rm -f ./oauth_token.json

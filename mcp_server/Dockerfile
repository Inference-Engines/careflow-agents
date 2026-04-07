FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .

# Copy OAuth token from parent directory during build
# For Cloud Run, prefer Secret Manager — this is for quick hackathon deploy
COPY oauth_token.json ./oauth_token.json

# Cloud Run provides PORT=8080 by default
ENV PORT=8080
ENV OAUTH_TOKEN_PATH=/app/oauth_token.json

EXPOSE 8080

CMD ["python", "server.py"]

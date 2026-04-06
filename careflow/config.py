"""
CareFlow — Centralized Configuration
Loads settings from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # ─── Google Cloud ───
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1")

    # ─── MCP Toolbox ───
    TOOLBOX_SERVER_URL: str = os.getenv("TOOLBOX_SERVER_URL", "http://127.0.0.1:5000")

    # ─── Vertex AI Embedding ───
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-005")
    EMBEDDING_DIMENSION: int = 768  # must match vector(768) in schema

    # ─── Agent Model ───
    AGENT_MODEL: str = os.getenv("AGENT_MODEL", "gemini-2.5-flash")

    # ─── Toolsets (must match toolbox/tools.yaml) ───
    TASK_AGENT_TOOLSET: str = "careflow_task_tools"
    MEDICAL_INFO_AGENT_TOOLSET: str = "careflow_medical_info_tools"

    # ─── Cloud Run ───
    PORT: int = int(os.getenv("PORT", "8080"))


config = Config()

# ============================================================================
# CareFlow Central Configuration / CareFlow 중앙 설정
# ============================================================================
# 모든 에이전트와 도구에서 참조하는 환경 설정 상수.
# Environment constants referenced by all agents and tools.
#
# .env 파일이 있으면 자동 로드하여 os.environ에 반영한다.
# Automatically loads .env file into os.environ if present.
# ============================================================================

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# dotenv 로드 / Load .env file
# ---------------------------------------------------------------------------
# python-dotenv가 설치되어 있으면 프로젝트 루트의 .env를 자동 로드.
# If python-dotenv is installed, auto-load .env from the project root.
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv 미설치 시 무시 / skip if not installed

# ---------------------------------------------------------------------------
# Google Cloud / Google Cloud 설정
# ---------------------------------------------------------------------------
GOOGLE_CLOUD_PROJECT: str = os.getenv(
    "GOOGLE_CLOUD_PROJECT", "reference-yen-492413-h8"
)
GOOGLE_CLOUD_LOCATION: str = os.getenv(
    "GOOGLE_CLOUD_LOCATION", "us-central1"
)

# ---------------------------------------------------------------------------
# Embedding / 임베딩 설정
# ---------------------------------------------------------------------------
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-005")
EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))

# ---------------------------------------------------------------------------
# Agent LLM / 에이전트 모델 설정
# ---------------------------------------------------------------------------
AGENT_MODEL: str = os.getenv("AGENT_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# MCP Toolbox Server / MCP 도구 서버
# ---------------------------------------------------------------------------
TOOLBOX_SERVER_URL: str = os.getenv(
    "TOOLBOX_SERVER_URL", "http://127.0.0.1:5000"
)

# ---------------------------------------------------------------------------
# Default Patient / 기본 환자 설정
# ---------------------------------------------------------------------------
# Rajesh Sharma 시드 환자 UUID / Seed patient (Rajesh Sharma) UUID
DEFAULT_PATIENT_ID: str = os.getenv(
    "DEFAULT_PATIENT_ID", "11111111-1111-1111-1111-111111111111"
)

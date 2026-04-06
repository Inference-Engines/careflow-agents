# ============================================================================
# CareFlow Test Fixtures / CareFlow 테스트 공통 픽스처
# ============================================================================
# pytest 공통 fixtures: mock DB, mock ToolContext 등.
# Shared pytest fixtures: mock DB, mock ToolContext, etc.
#
# 모든 테스트는 외부 API 호출 없이 mock 만으로 동작한다.
# All tests run with mocks only — no external API calls.
# ============================================================================

from __future__ import annotations

from typing import Any

import pytest


# ---------------------------------------------------------------------------
# 환자 상수 / Patient constants
# ---------------------------------------------------------------------------
PATIENT_UUID = "11111111-1111-1111-1111-111111111111"
CAREGIVER_UUID = "22222222-2222-2222-2222-222222222222"
PATIENT_NAME = "Rajesh Sharma"
CAREGIVER_NAME = "Priya Sharma"


# ---------------------------------------------------------------------------
# FakeCtx — ADK ToolContext를 모사하는 경량 클래스
# Lightweight mock that mimics ADK ToolContext's state dict.
# ---------------------------------------------------------------------------
class FakeCtx:
    """ToolContext mock — .state dict만 제공.
    Provides only the .state dict that tools need.
    """

    def __init__(self, state: dict[str, Any] | None = None):
        self.state: dict[str, Any] = state or {}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_tool_context() -> FakeCtx:
    """ADK ToolContext mock — 기본 환자 세션 상태 포함.
    Returns a FakeCtx pre-loaded with default patient session state.
    """
    return FakeCtx(state={
        "current_patient_id": PATIENT_UUID,
    })


@pytest.fixture()
def mock_db() -> dict[str, Any]:
    """Rajesh Sharma 환자의 mock DB 데이터.
    Mock DB data for patient Rajesh Sharma.

    포함 항목 / Contains:
      - patient: 환자 정보 / patient info
      - caregiver: 보호자 정보 / caregiver info
      - medications: 5개 약물 / 5 medications
      - visits: 3개 방문 기록 / 3 visit records
    """
    return {
        "patient": {
            "patient_id": PATIENT_UUID,
            "name": PATIENT_NAME,
            "age": 58,
            "conditions": ["Type 2 Diabetes", "Hypertension"],
            "doctor": "Dr. Mehta",
            "clinic": "Apollo Clinic",
            "city": "Mumbai",
        },
        "caregiver": {
            "caregiver_id": CAREGIVER_UUID,
            "name": CAREGIVER_NAME,
            "relationship": "daughter",
        },
        "medications": [
            {"name": "Metformin", "dosage": "1000mg", "frequency": "twice_daily"},
            {"name": "Amlodipine", "dosage": "5mg", "frequency": "once_daily"},
            {"name": "Aspirin", "dosage": "75mg", "frequency": "once_daily"},
            {"name": "Atorvastatin", "dosage": "20mg", "frequency": "once_daily"},
            {"name": "Lisinopril", "dosage": "10mg", "frequency": "once_daily"},
        ],
        "visits": [
            {
                "visit_id": "VIS-001",
                "visit_date": "2026-04-03",
                "doctor_name": "Dr. Sharma",
                "summary": "Routine diabetes follow-up. HbA1c 7.2%.",
            },
            {
                "visit_id": "VIS-002",
                "visit_date": "2026-03-15",
                "doctor_name": "Dr. Patel",
                "summary": "Endocrinology consult. Started Amlodipine 5mg.",
            },
            {
                "visit_id": "VIS-003",
                "visit_date": "2026-02-10",
                "doctor_name": "Dr. Sharma",
                "summary": "Routine follow-up. Started Aspirin 75mg.",
            },
        ],
    }

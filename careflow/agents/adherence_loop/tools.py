"""
Medication Adherence Loop Tools — 약물 순응도 모니터링 도구
Tools for the LoopAgent-based medication adherence monitor.

설계 문서 Pattern 6 참조:
  Step 1: 약물 복용 시간 확인 / Check medication schedule
  Step 2: 순응도 확인 → 복용=로그 / 미복용=리마인더
           Check adherence → taken=log / missed=reminder
  Step 3: 2회 연속 미복용 → 보호자 에스컬레이션
           2 consecutive misses → caregiver escalation
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


# =============================================================================
# Tool 1: 약물 복용 시간 확인 / Check medication schedule
# =============================================================================

def check_medication_time(patient_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """환자의 현재 복용 예정 약물을 확인한다.
    Check which medications are currently due for the patient.

    Args:
        patient_id: 환자 고유 ID / Patient unique identifier
        tool_context: ADK ToolContext — 세션 상태 접근용 (ADK 패턴 통일)
                      ADK ToolContext — for session state access (consistent ADK pattern)

    Returns:
        dict: 복용 예정 약물 목록과 시간 정보
              Scheduled medications and timing info
    """
    # TODO: AlloyDB 연동 시 실제 쿼리로 교체
    # TODO: Replace with actual AlloyDB query during integration
    now = datetime.now(timezone.utc)
    hour = now.hour

    # 시간대별 복용 스케줄 시뮬레이션 — Rajesh Sharma 기준
    # Time-based medication schedule simulation — based on Rajesh Sharma
    schedule = {
        "morning": {  # 08:00 IST
            "window": (2, 5),  # UTC 02:30-05:30 ≈ IST 08:00-11:00
            "medications": [
                {"name": "Metformin", "dosage": "1000mg", "with_food": True},
                {"name": "Amlodipine", "dosage": "5mg", "with_food": False},
                {"name": "Aspirin", "dosage": "75mg", "with_food": True},
            ],
        },
        "evening": {  # 20:00 IST
            "window": (14, 17),  # UTC 14:30-17:30 ≈ IST 20:00-23:00
            "medications": [
                {"name": "Metformin", "dosage": "500mg", "with_food": True},
                {"name": "Atorvastatin", "dosage": "20mg", "with_food": False},
                {"name": "Lisinopril", "dosage": "10mg", "with_food": False},
            ],
        },
    }

    due_medications = []
    current_slot = None
    for slot_name, slot_info in schedule.items():
        low, high = slot_info["window"]
        if low <= hour <= high:
            current_slot = slot_name
            due_medications = slot_info["medications"]
            break

    result = {
        "patient_id": patient_id,
        "check_time_utc": now.isoformat(),
        "current_slot": current_slot,
        "due_medications": due_medications,
        "has_due_medications": len(due_medications) > 0,
    }

    # 세션 상태에 마지막 스케줄 체크 기록
    # Record last schedule check in session state
    if tool_context is not None:
        tool_context.state["last_schedule_check"] = {
            "patient_id": patient_id,
            "timestamp": now.isoformat(),
            "slot": current_slot,
            "due_count": len(due_medications),
        }

    logger.info(
        "[AdherenceLoop] Medication check: patient=%s, slot=%s, due=%d",
        patient_id, current_slot, len(due_medications),
    )
    return result


# =============================================================================
# Tool 2: 순응도 확인 / Check adherence status
# =============================================================================

def check_adherence(patient_id: str, medication_name: str, tool_context: ToolContext) -> dict[str, Any]:
    """특정 약물의 복용 여부를 확인한다.
    Check whether a specific medication has been taken.

    Args:
        patient_id: 환자 고유 ID / Patient unique identifier
        medication_name: 약물명 / Medication name
        tool_context: ADK ToolContext — 세션 상태 접근용 (ADK 패턴 통일)
                      ADK ToolContext — for session state access (consistent ADK pattern)

    Returns:
        dict: 복용 상태, 연속 미복용 횟수
              Adherence status, consecutive miss count
    """
    # TODO: AlloyDB 연동 시 실제 adherence 레코드 조회로 교체
    # TODO: Replace with actual adherence record lookup during integration
    #
    # 시뮬레이션: Metformin은 간헐적 미복용, 나머지는 복용 완료
    # Simulation: Metformin has intermittent misses, others are taken

    simulated_data = {
        "Metformin": {"taken": False, "consecutive_misses": 2},
        "Amlodipine": {"taken": True, "consecutive_misses": 0},
        "Aspirin": {"taken": True, "consecutive_misses": 0},
        "Atorvastatin": {"taken": True, "consecutive_misses": 0},
        "Lisinopril": {"taken": False, "consecutive_misses": 1},
    }

    med_status = simulated_data.get(medication_name, {
        "taken": False, "consecutive_misses": 0,
    })

    result = {
        "patient_id": patient_id,
        "medication_name": medication_name,
        "taken": med_status["taken"],
        "consecutive_misses": med_status["consecutive_misses"],
        # 에스컬레이션 트리거: 2회 연속 미복용
        # Escalation trigger: 2 consecutive misses
        "needs_escalation": med_status["consecutive_misses"] >= 2,
    }

    if med_status["taken"]:
        logger.info(
            "[AdherenceLoop] Adherence confirmed: patient=%s, med=%s",
            patient_id, medication_name,
        )
    else:
        logger.warning(
            "[AdherenceLoop] Medication missed: patient=%s, med=%s, "
            "consecutive_misses=%d",
            patient_id, medication_name, med_status["consecutive_misses"],
        )

    return result


# =============================================================================
# Tool 3: 리마인더 전송 / Send reminder
# =============================================================================

def send_reminder(
    patient_id: str,
    medication_name: str,
    reminder_type: str = "patient",
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """약물 복용 리마인더를 전송한다.
    Send a medication adherence reminder.

    Args:
        patient_id: 환자 고유 ID / Patient unique identifier
        medication_name: 약물명 / Medication name
        reminder_type: 리마인더 대상 — "patient" 또는 "caregiver"
                       Reminder target — "patient" or "caregiver"
        tool_context: ADK ToolContext — 세션 상태 접근용 (ADK 패턴 통일)
                      ADK ToolContext — for session state access (consistent ADK pattern)

    Returns:
        dict: 리마인더 전송 결과
              Reminder delivery result
    """
    now = datetime.now(timezone.utc)

    if reminder_type == "caregiver":
        # 보호자 에스컬레이션 — 2회 연속 미복용 시 발동
        # Caregiver escalation — triggered after 2 consecutive misses
        message = (
            f"⚠️ [CareFlow Alert] Patient {patient_id} has missed "
            f"{medication_name} for 2+ consecutive doses. "
            f"Please check on the patient. Time: {now.isoformat()}"
        )
        logger.warning(
            "[AdherenceLoop] Caregiver escalation sent: patient=%s, med=%s",
            patient_id, medication_name,
        )
    else:
        # 환자 리마인더 — 일반 복용 알림
        # Patient reminder — standard medication notification
        message = (
            f"💊 Reminder: It's time to take your {medication_name}. "
            f"Please take it now and confirm when done."
        )
        logger.info(
            "[AdherenceLoop] Patient reminder sent: patient=%s, med=%s",
            patient_id, medication_name,
        )

    # TODO: 실제 알림 채널 연동 (FCM, SMS, Gmail MCP 등)
    # TODO: Integrate actual notification channel (FCM, SMS, Gmail MCP, etc.)
    result = {
        "patient_id": patient_id,
        "medication_name": medication_name,
        "reminder_type": reminder_type,
        "message": message,
        "sent_at_utc": now.isoformat(),
        "status": "sent",
    }

    return result

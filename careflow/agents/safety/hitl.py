# Copyright 2026 CareFlow Team
#
# CareFlow HITL (Human-in-the-Loop) — 고위험 액션 확인 게이트
# Human-in-the-Loop gate for high-risk action confirmation.
#
# 설계 문서 참조 / Design doc reference:
#   CareFlow_System_Design_EN_somi.md — Section 3-11 HITL
#
# HITL Escalation Matrix / HITL 에스컬레이션 매트릭스:
#   LOW  (자동):     약물 리마인더, 정기 방문 기록, 보호자 정기 업데이트
#   MED  (확인):     새 약물 기록 추가
#   HIGH (필수 확인): 약물 상호작용 경고, 긴급 증상 알림, 약물 정보 수정/삭제
#   CRITICAL (필수 확인): ER 방문 권고

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# 리스크 레벨 정의 / Risk level definitions
# =============================================================================

class RiskLevel(str, Enum):
    """HITL 리스크 레벨 / HITL risk levels."""
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# 액션 타입 → 리스크 레벨 매핑 / Action type → risk level mapping
# 설계 문서 HITL Escalation Matrix 기반 / Based on design doc HITL Escalation Matrix
_ACTION_RISK_MAP: dict[str, RiskLevel] = {
    # LOW — 자동 통과 / auto-pass
    "medication_reminder": RiskLevel.LOW,
    "routine_visit_record": RiskLevel.LOW,
    "caregiver_regular_update": RiskLevel.LOW,
    "save_visit_record": RiskLevel.LOW,
    "search_medical_history": RiskLevel.LOW,
    "get_health_metrics": RiskLevel.LOW,
    "get_medications": RiskLevel.LOW,
    "get_appointments": RiskLevel.LOW,
    "save_health_insight": RiskLevel.LOW,
    "create_task": RiskLevel.LOW,
    # MED — 확인 권장 / confirmation recommended
    "add_new_medication": RiskLevel.MED,
    "add_medication": RiskLevel.MED,
    "book_appointment": RiskLevel.MED,
    "send_caregiver_notification": RiskLevel.MED,
    # HIGH — 필수 확인 / must confirm
    "drug_interaction_warning": RiskLevel.HIGH,
    "urgent_symptom_alert": RiskLevel.HIGH,
    "modify_medication": RiskLevel.HIGH,
    "update_medication": RiskLevel.HIGH,
    "delete_medication": RiskLevel.HIGH,
    "discontinue_medication": RiskLevel.HIGH,
    # CRITICAL — 필수 확인 / must confirm
    "recommend_er_visit": RiskLevel.CRITICAL,
    "escalate_to_doctor": RiskLevel.CRITICAL,
}

# 확인이 필요한 리스크 레벨 / Risk levels that require confirmation
_REQUIRES_CONFIRMATION = {RiskLevel.HIGH, RiskLevel.CRITICAL}

# MED 레벨은 컨텍스트에 따라 확인이 필요할 수 있음
# MED level may require confirmation depending on context
_MAY_REQUIRE_CONFIRMATION = {RiskLevel.MED}


# =============================================================================
# 리스크 레벨 판정 / Risk level assessment
# =============================================================================

def assess_risk_level(action_type: str, context: dict | None = None) -> RiskLevel:
    """액션의 리스크 레벨을 판정한다.
    Assess the risk level of a given action.

    Args:
        action_type: 액션 타입 문자열 (예: "drug_interaction_warning")
                     Action type string (e.g., "drug_interaction_warning")
        context: 추가 컨텍스트 정보 (환자 상태, 약물 수 등)
                 Additional context (patient state, medication count, etc.)

    Returns:
        RiskLevel: 판정된 리스크 레벨 / Assessed risk level
    """
    context = context or {}

    # 매핑 테이블에서 기본 리스크 레벨 조회
    # Look up base risk level from mapping table
    base_level = _ACTION_RISK_MAP.get(action_type, RiskLevel.MED)

    # 컨텍스트 기반 리스크 상승 / Context-based risk escalation
    # 다중 약물 환자의 경우 MED → HIGH로 상승
    # Escalate MED → HIGH for patients with multiple medications
    if base_level == RiskLevel.MED:
        medication_count = context.get("medication_count", 0)
        if medication_count >= 5:
            logger.info(
                "[HITL] Risk escalated MED → HIGH: patient has %d medications",
                medication_count,
            )
            return RiskLevel.HIGH

    # 긴급 증상의 심각도가 높으면 HIGH → CRITICAL로 상승
    # Escalate HIGH → CRITICAL for severe symptom urgency
    if base_level == RiskLevel.HIGH:
        urgency = context.get("urgency", "").upper()
        if urgency == "CRITICAL":
            logger.info("[HITL] Risk escalated HIGH → CRITICAL: urgency=%s", urgency)
            return RiskLevel.CRITICAL

    return base_level


# =============================================================================
# HITL 확인 요청 / HITL confirmation request
# =============================================================================

async def request_human_confirmation(
    action: dict,
    risk_level: RiskLevel,
) -> dict:
    """사용자에게 고위험 액션 확인을 요청한다.
    Request user confirmation for a high-risk action.

    ADK 세션 상태를 통해 확인 요청을 기록하고,
    사용자에게 확인 메시지를 표시한다.
    Records the confirmation request via ADK session state
    and displays a confirmation message to the user.

    Args:
        action: 확인이 필요한 액션 정보
                Action details requiring confirmation
                Expected keys: "type", "description", "details" (optional)
        risk_level: 리스크 레벨 / Risk level

    Returns:
        dict: 확인 요청 결과
              {
                "status": "pending_confirmation",
                "confirmation_id": str,
                "message": str,       # 사용자에게 표시할 메시지 / Message to display
                "risk_level": str,
                "action": dict,
              }
    """
    confirmation_id = f"hitl-{int(time.time() * 1000)}"

    # 리스크 레벨에 따른 경고 아이콘 / Warning icon based on risk level
    icon = "🔴" if risk_level == RiskLevel.CRITICAL else "⚠️"

    # 확인 메시지 구성 / Build confirmation message
    action_desc = action.get("description", action.get("type", "Unknown action"))
    details = action.get("details", "")

    message_lines = [
        f"{icon} **[{risk_level.value}] 확인이 필요합니다 / Confirmation Required**",
        "",
        f"다음 액션을 수행하시겠습니까? / Do you want to proceed with this action?",
        f"  **액션 / Action:** {action_desc}",
    ]
    if details:
        message_lines.append(f"  **상세 / Details:** {details}")

    message_lines.extend([
        "",
        "👉 **'예' 또는 'yes'**로 승인 / Approve with 'yes'",
        "👉 **'아니오' 또는 'no'**로 거부 / Decline with 'no'",
    ])

    confirmation_message = "\n".join(message_lines)

    logger.info(
        "[HITL] Confirmation requested: id=%s, risk=%s, action=%s",
        confirmation_id,
        risk_level.value,
        action.get("type"),
    )

    return {
        "status": "pending_confirmation",
        "confirmation_id": confirmation_id,
        "message": confirmation_message,
        "risk_level": risk_level.value,
        "action": action,
    }


# =============================================================================
# HITL 게이트 — 메인 진입점 / HITL gate — main entry point
# =============================================================================

async def hitl_gate(
    action_type: str,
    action_details: dict | None = None,
    context: dict | None = None,
) -> dict:
    """HITL 게이트 — 리스크 레벨에 따라 통과 또는 확인 요청.
    HITL gate — pass through or request confirmation based on risk level.

    LOW/MED는 자동 통과, HIGH/CRITICAL은 사용자 확인 필요.
    LOW/MED auto-pass, HIGH/CRITICAL require user confirmation.

    이 함수는 before_tool_callback이나 after_model_callback에서 호출된다.
    Called from before_tool_callback or after_model_callback.

    Args:
        action_type: 액션 타입 (예: "drug_interaction_warning")
                     Action type (e.g., "drug_interaction_warning")
        action_details: 액션 상세 정보 (설명, 관련 데이터 등)
                        Action details (description, related data, etc.)
        context: 세션/환자 컨텍스트 / Session/patient context

    Returns:
        dict: 게이트 결과 / Gate result
              - {"status": "approved", "risk_level": ...}  — 자동 통과 / auto-pass
              - {"status": "pending_confirmation", ...}     — 확인 필요 / needs confirmation
    """
    action_details = action_details or {}
    context = context or {}

    # 1. 리스크 레벨 판정 / Assess risk level
    risk_level = assess_risk_level(action_type, context)

    logger.info(
        "[HITL] Gate check: action=%s, risk=%s",
        action_type,
        risk_level.value,
    )

    # 2. LOW — 자동 통과 / auto-pass
    if risk_level == RiskLevel.LOW:
        return {
            "status": "approved",
            "risk_level": risk_level.value,
            "action_type": action_type,
            "auto_approved": True,
        }

    # 3. MED — 기본적으로 자동 통과, 로그 기록
    #    MED — auto-pass by default, with logging
    if risk_level == RiskLevel.MED:
        logger.info(
            "[HITL] MED-risk action auto-approved with logging: %s",
            action_type,
        )
        return {
            "status": "approved",
            "risk_level": risk_level.value,
            "action_type": action_type,
            "auto_approved": True,
            "logged": True,
        }

    # 4. HIGH / CRITICAL — 사용자 확인 필요 / requires user confirmation
    action = {
        "type": action_type,
        **action_details,
    }
    return await request_human_confirmation(action, risk_level)


# =============================================================================
# 응답 텍스트 기반 리스크 감지 / Response text-based risk detection
# =============================================================================

# 응답 텍스트에서 고위험 액션을 감지하기 위한 키워드 매핑
# Keyword mapping for detecting high-risk actions in response text
_RESPONSE_RISK_KEYWORDS: list[tuple[str, str]] = [
    # (키워드 패턴, 액션 타입) / (keyword pattern, action type)
    ("drug interaction", "drug_interaction_warning"),
    ("약물 상호작용", "drug_interaction_warning"),
    ("medication interaction", "drug_interaction_warning"),
    ("emergency room", "recommend_er_visit"),
    ("ER visit", "recommend_er_visit"),
    ("응급실", "recommend_er_visit"),
    ("call 911", "recommend_er_visit"),
    ("call ambulance", "recommend_er_visit"),
    ("urgent symptom", "urgent_symptom_alert"),
    ("긴급 증상", "urgent_symptom_alert"),
    ("immediately contact", "urgent_symptom_alert"),
    ("즉시 연락", "urgent_symptom_alert"),
]


# =============================================================================
# HITL 사용자 승인 응답 처리 / HITL user confirmation response processing
# =============================================================================

# 승인 키워드 / Approval keywords
_APPROVE_KEYWORDS = {"yes", "confirm", "ok", "예", "네", "승인", "확인", "y"}
# 거부 키워드 / Denial keywords
_DENY_KEYWORDS = {"no", "cancel", "deny", "아니오", "아니", "거부", "취소", "n"}


def process_confirmation_response(user_input: str, pending: dict) -> dict:
    """사용자 승인/거부 응답을 처리한다.
    Process user approval/denial response for a pending HITL confirmation.

    session state의 pending_confirmation과 사용자 입력을 비교하여
    승인/거부/재확인 요청 중 하나를 반환한다.
    Compares user input against the pending_confirmation in session state
    and returns one of: approved / denied / re-ask.

    Args:
        user_input: 사용자 입력 텍스트 (예: "yes", "no")
                    User input text (e.g., "yes", "no")
        pending: session state에 저장된 pending_confirmation dict
                 pending_confirmation dict stored in session state
                 Expected keys: "confirmation_id", "action", "risk_level"

    Returns:
        dict: 처리 결과 / Processing result
              - {"status": "approved", ...}    — 승인됨 / approved
              - {"status": "denied", ...}      — 거부됨 / denied
              - {"status": "re_ask", ...}      — 재확인 요청 / re-ask
    """
    normalized = user_input.strip().lower()
    confirmation_id = pending.get("confirmation_id", "unknown")
    action = pending.get("action", {})
    risk_level = pending.get("risk_level", "UNKNOWN")

    # 승인 처리 / Handle approval
    if normalized in _APPROVE_KEYWORDS:
        logger.info(
            "[HITL] Confirmation approved: id=%s, action=%s",
            confirmation_id,
            action.get("type", "unknown"),
        )
        return {
            "status": "approved",
            "confirmation_id": confirmation_id,
            "action": action,
            "risk_level": risk_level,
            "user_response": normalized,
        }

    # 거부 처리 / Handle denial
    if normalized in _DENY_KEYWORDS:
        logger.info(
            "[HITL] Confirmation denied: id=%s, action=%s",
            confirmation_id,
            action.get("type", "unknown"),
        )
        return {
            "status": "denied",
            "confirmation_id": confirmation_id,
            "action": action,
            "risk_level": risk_level,
            "user_response": normalized,
            "message": (
                "Action has been cancelled as requested. "
                "액션이 요청에 따라 취소되었습니다."
            ),
        }

    # 재확인 요청 — 인식할 수 없는 응답 / Re-ask — unrecognized response
    logger.info(
        "[HITL] Unrecognized confirmation response: id=%s, input='%s'",
        confirmation_id,
        normalized,
    )
    return {
        "status": "re_ask",
        "confirmation_id": confirmation_id,
        "action": action,
        "risk_level": risk_level,
        "user_response": normalized,
        "message": (
            "Please respond with 'yes' to approve or 'no' to cancel.\n"
            "'예' 또는 'yes'로 승인, '아니오' 또는 'no'로 거부해 주세요."
        ),
    }


# =============================================================================
# HITL 타임아웃 처리 / HITL timeout handling
# =============================================================================

# 확인 요청 기본 타임아웃 (초) / Default confirmation timeout in seconds
CONFIRMATION_TIMEOUT_SECONDS: int = 300  # 5분 / 5 minutes

def check_confirmation_timeout(pending: dict, timeout: int = CONFIRMATION_TIMEOUT_SECONDS) -> bool:
    """pending confirmation이 타임아웃되었는지 확인한다.
    Check whether a pending confirmation has timed out.

    confirmation_id에 포함된 타임스탬프를 기준으로 경과 시간을 계산.
    Uses the timestamp embedded in the confirmation_id.

    Args:
        pending: session state의 pending_confirmation dict
                 pending_confirmation dict from session state
        timeout: 타임아웃 초 / timeout in seconds

    Returns:
        bool: True이면 타임아웃됨 / True if timed out
    """
    confirmation_id = pending.get("confirmation_id", "")
    try:
        # hitl-{timestamp_ms} 에서 타임스탬프 추출 / Extract timestamp from id
        ts_str = confirmation_id.split("-", 1)[1]
        created_ms = int(ts_str)
        elapsed = (time.time() * 1000) - created_ms
        if elapsed > timeout * 1000:
            logger.info(
                "[HITL] Confirmation timed out: id=%s, elapsed=%.1fs",
                confirmation_id,
                elapsed / 1000,
            )
            return True
    except (IndexError, ValueError):
        pass
    return False


def detect_risk_in_response(response_text: str) -> tuple[str | None, RiskLevel | None]:
    """응답 텍스트에서 고위험 액션 키워드를 감지한다.
    Detect high-risk action keywords in response text.

    Args:
        response_text: LLM 응답 텍스트 / LLM response text

    Returns:
        tuple: (액션 타입, 리스크 레벨) 또는 (None, None)
               (action_type, risk_level) or (None, None) if no risk detected
    """
    if not response_text:
        return None, None

    text_lower = response_text.lower()
    for keyword, action_type in _RESPONSE_RISK_KEYWORDS:
        if keyword.lower() in text_lower:
            risk_level = assess_risk_level(action_type)
            if risk_level in _REQUIRES_CONFIRMATION:
                logger.info(
                    "[HITL] Risk detected in response: keyword='%s', action=%s, risk=%s",
                    keyword,
                    action_type,
                    risk_level.value,
                )
                return action_type, risk_level

    return None, None

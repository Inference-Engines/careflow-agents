# ============================================================================
# Patient ID resolution utility
# LLM이 생성하는 placeholder ID ("patient_001")를 실제 UUID로 교정
# ============================================================================

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Rajesh Sharma — 시드 환자의 실제 UUID.
# Default patient UUID for the demo persona (Rajesh Sharma).
DEFAULT_PATIENT_UUID = "11111111-1111-1111-1111-111111111111"

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def resolve_patient_id(patient_id: str, tool_context=None) -> str:
    """LLM이 넘긴 patient_id가 유효 UUID가 아니면 session state에서 교정.

    LLM은 "patient_001" 같은 placeholder를 보내기도 하고 실제 UUID를 보내기도 한다.
    DB columns은 uuid 타입이므로 non-UUID가 들어오면 쿼리가 터진다. 이 함수에서:
      1. 정상 UUID → 그대로 통과
      2. 비정상 → session state의 current_patient_id 사용
      3. state도 없으면 → Rajesh 기본값 (DEFAULT_PATIENT_UUID)
    """
    if _UUID_RE.match(patient_id or ""):
        return patient_id

    # session state에서 가져오기
    state_pid = ""
    if tool_context is not None:
        state_pid = tool_context.state.get("current_patient_id", "") or ""
    if _UUID_RE.match(state_pid):
        logger.info("resolve_patient_id: %r → state %s", patient_id, state_pid)
        return state_pid

    logger.info("resolve_patient_id: %r → default %s", patient_id, DEFAULT_PATIENT_UUID)
    return DEFAULT_PATIENT_UUID

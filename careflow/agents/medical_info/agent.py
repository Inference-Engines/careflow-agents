# ============================================================================
# CareFlow Medical Info Agent — Agent Assembly
# 의료 정보 에이전트 조립 및 콜백 정의
# ============================================================================
# LlmAgent 기반 의료 기록 구조화 + 시맨틱 검색 (RAG) + 건강 지표 추세 분석 +
# 사전방문 요약 + 보호자 알림 에이전트.
#
# LlmAgent-based medical record structuring + semantic search (RAG) +
# health metric trend analysis + pre-visit summaries + caregiver notifications.
# ============================================================================

import json
import logging
from copy import deepcopy
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

from careflow.agents.safety.plugin import (
    before_model_callback as safety_before_model_callback,
    after_model_callback as safety_after_model_callback,
)
from .prompt import MEDICAL_INFO_INSTRUCTION
from .tools import (
    store_visit_record,
    search_medical_history,
    get_upcoming_appointments,
    get_health_metrics,
    get_health_metrics_by_type,
    save_health_insight,
    send_caregiver_notification,
    get_caregiver_info,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Callbacks (before_model / after_model)
# 모델 호출 전후 가드레일 및 후처리 콜백
# Pre/post model-call guardrails and post-processing callbacks
# ---------------------------------------------------------------------------

# 금지 키워드 목록 — 진단/처방 행위 차단
# Blocked keywords — prevents diagnostic/prescriptive behavior
_BLOCKED_KEYWORDS = [
    "prescribe",
    "diagnose",
    "you have",
    "you are suffering from",
    "take this medication",
    "stop taking",
    "increase your dose",
    "decrease your dose",
]

# 의료 정보 면책 조항 — 모든 응답에 자동 첨부
# Medical info disclaimer — automatically appended to every response
_MEDICAL_INFO_DISCLAIMER = (
    "This information is based on recorded data and does not constitute "
    "medical advice. Please discuss findings with your healthcare provider."
)


async def _before_model_guard(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """Pre-model guardrail: SafetyPlugin + 입력 검증 + 환자 컨텍스트 주입.

    0. SafetyPlugin 핵심 검사 (PII, cross-patient, prompt injection) 실행.
    1. 사용자 입력에 부적절한 의료 요청이 포함되었는지 확인.
    2. session state에서 patient_id를 시스템 인스트럭션에 주입.

    0. Run SafetyPlugin core checks (PII, cross-patient, prompt injection).
    1. Check if user input contains inappropriate medical requests.
    2. Inject patient_id from session state into system instruction.

    Returns:
        LlmResponse if blocked, None to proceed normally.
    """
    # ── Step 0: SafetyPlugin 공통 검사 / SafetyPlugin shared checks ──
    safety_result = await safety_before_model_callback(callback_context, llm_request)
    if safety_result is not None:
        logger.warning("[MedicalInfo] Request blocked by SafetyPlugin")
        return safety_result

    # --- 사용자 입력 검사 / Inspect user input ---
    last_user_text = ""
    if llm_request.contents and llm_request.contents[-1].role == "user":
        parts = llm_request.contents[-1].parts
        if parts and parts[0].text:
            last_user_text = parts[0].text.lower()

    for keyword in _BLOCKED_KEYWORDS:
        if keyword in last_user_text:
            logger.warning(
                "[MedicalInfo] Blocked request containing '%s' from agent '%s'",
                keyword,
                callback_context.agent_name,
            )
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=json.dumps(
                                {
                                    "action": "error",
                                    "message": (
                                        "I can only help with retrieving, structuring, and "
                                        "summarizing medical records. For medical diagnoses "
                                        "or medication decisions, please consult your "
                                        "healthcare provider."
                                    ),
                                    "disclaimer": _MEDICAL_INFO_DISCLAIMER,
                                },
                                ensure_ascii=False,
                            )
                        )
                    ],
                )
            )

    # --- state에서 환자 컨텍스트 주입 / Inject patient context from state ---
    patient_id = callback_context.state.get("current_patient_id")
    if patient_id:
        logger.info("[MedicalInfo] Injecting patient context: %s", patient_id)
        sys_instr = llm_request.config.system_instruction
        if sys_instr and isinstance(sys_instr, types.Content) and sys_instr.parts:
            ctx_note = f"\n\n[Session Context] Current patient_id: {patient_id}"
            sys_instr.parts[0].text = (sys_instr.parts[0].text or "") + ctx_note

    return None


async def _after_model_postprocess(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Post-model processing: SafetyPlugin + 응답 검증 + 면책 조항 첨부.

    0. SafetyPlugin 출력 검사 (PII 마스킹, HITL 게이트, 면책조항).
    1. JSON 응답에 disclaimer 필드 자동 삽입.
    2. 진단/처방 키워드가 포함된 응답 차단.

    0. Run SafetyPlugin output checks (PII masking, HITL gate, disclaimer).
    1. Auto-inject disclaimer field in JSON responses.
    2. Block responses containing diagnostic/prescriptive keywords.

    Returns:
        Modified LlmResponse if changes needed, None to pass through.
    """
    # ── Step 0: SafetyPlugin 출력 검사 / SafetyPlugin output checks ──
    safety_result = await safety_after_model_callback(callback_context, llm_response)
    if safety_result is not None:
        llm_response = safety_result

    # function_call 응답은 수정하지 않음 / Don't modify tool-call responses
    if not llm_response.content or not llm_response.content.parts:
        return None
    first_part = llm_response.content.parts[0]
    if first_part.function_call:
        return None
    if not first_part.text:
        return None

    response_text = first_part.text

    # --- 진단/처방 키워드 사후 검사 / Post-hoc diagnostic keyword check ---
    response_lower = response_text.lower()
    for keyword in _BLOCKED_KEYWORDS:
        if keyword in response_lower:
            logger.warning(
                "[MedicalInfo] Post-model filter caught '%s' in response",
                keyword,
            )
            blocked_response = {
                "action": "error",
                "message": (
                    "The generated response was filtered because it contained "
                    "language outside the scope of medical records retrieval. "
                    "Please rephrase your query focusing on historical records."
                ),
                "disclaimer": _MEDICAL_INFO_DISCLAIMER,
            }
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=json.dumps(blocked_response, ensure_ascii=False))],
                )
            )

    # --- JSON 응답 후처리 / JSON response post-processing ---
    try:
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            clean_text = "\n".join(lines)

        parsed = json.loads(clean_text)

        # disclaimer 자동 삽입 / Auto-inject disclaimer
        if isinstance(parsed, dict):
            parsed["disclaimer"] = _MEDICAL_INFO_DISCLAIMER

        modified_text = json.dumps(parsed, ensure_ascii=False, indent=2)
        modified_parts = [deepcopy(part) for part in llm_response.content.parts]
        modified_parts[0].text = modified_text

        return LlmResponse(
            content=types.Content(role="model", parts=modified_parts),
            grounding_metadata=llm_response.grounding_metadata,
        )

    except (json.JSONDecodeError, ValueError):
        logger.debug("[MedicalInfo] Response is not JSON; appending disclaimer as text.")
        modified_parts = [deepcopy(part) for part in llm_response.content.parts]
        modified_parts[0].text = response_text + f"\n\n{_MEDICAL_INFO_DISCLAIMER}"
        return LlmResponse(
            content=types.Content(role="model", parts=modified_parts),
            grounding_metadata=llm_response.grounding_metadata,
        )


# ---------------------------------------------------------------------------
# Factory function — ADK single-parent 제약 대응
# Factory function — work around ADK single-parent constraint
#
# ADK는 각 에이전트 인스턴스가 단일 부모만 가질 수 있으므로, 동일 에이전트를
# 여러 워크플로우 + root standalone에 등록하려면 매번 새 인스턴스를 만들어야 함.
# ADK enforces single-parent ownership per instance, so we build a fresh
# instance whenever the same agent needs to be wired under multiple parents.
# ---------------------------------------------------------------------------
def build_medical_info_agent(suffix: str = "") -> LlmAgent:
    """Medical Info Agent 인스턴스 생성 / Build a new Medical Info Agent instance.

    Args:
        suffix: name 충돌 방지용 접미사. 기본값 ""은 backward-compat용.
                Suffix appended to the agent name to avoid collisions.
    """
    return LlmAgent(
        name=f"medical_info_agent{suffix}",
        model="gemini-2.5-flash",
        instruction=MEDICAL_INFO_INSTRUCTION,
        tools=[
            store_visit_record,
            search_medical_history,
            get_upcoming_appointments,
            get_health_metrics,
            get_health_metrics_by_type,
            save_health_insight,
            send_caregiver_notification,
            get_caregiver_info,
        ],
        output_key="medical_info_result",
        description=(
            "Structures medical visit records, performs keyword-based search over "
            "patient history, tracks health metric trends, compiles pre-visit summaries, "
            "and sends notifications to caregivers. Handles queries about past visits, "
            "medical history, health trends, and appointment preparation."
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,  # 낮은 temperature → 일관성 있는 기록 검색 / Low temp → consistent retrieval
            response_mime_type="application/json",
        ),
        before_model_callback=_before_model_guard,
        after_model_callback=_after_model_postprocess,
    )


# Backward-compat default export — 기존 임포트 호환용 기본 인스턴스
# Default instance kept for backward compatibility with existing imports.
medical_info_agent = build_medical_info_agent()

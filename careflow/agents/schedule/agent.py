# ============================================================================
# CareFlow Schedule Agent - Agent Assembly
# 일정 관리 에이전트 조립 및 콜백 정의
# ============================================================================
# LlmAgent 기반 Google Calendar 연동 예약 관리 에이전트.
# 예약 생성/취소, 충돌 감지, 공복 검사 자동 배정, 약물 리마인더 관리.
#
# LlmAgent-based appointment management agent with Google Calendar integration.
# Handles booking/cancellation, conflict detection, fasting-test auto-scheduling,
# and medication reminder management.
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
from careflow.mcp import get_calendar_tools

from .prompt import SCHEDULE_INSTRUCTION
from .tools import (
    check_availability,
    book_appointment,
    list_appointments,
    cancel_appointment,
    check_conflicts,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Callbacks (before_model / after_model)
# 모델 호출 전후 가드레일 및 후처리 콜백
# Pre/post model-call guardrails and post-processing callbacks
# ---------------------------------------------------------------------------

# 금지 키워드 목록 -- 스케줄 에이전트 범위를 벗어난 의료 행위 차단
# Blocked keywords -- prevents out-of-scope medical actions
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

# 일정 면책 조항 -- 모든 응답에 자동 첨부
# Schedule disclaimer -- automatically appended to every response
_SCHEDULE_DISCLAIMER = (
    "Please confirm all appointment details with your healthcare provider's office."
)


async def _before_model_guard(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """Pre-model guardrail: SafetyPlugin 검사 + 입력 검증 + 환자 컨텍스트 주입.

    0. SafetyPlugin 핵심 검사 (PII scan, cross-patient, prompt injection) 먼저 실행.
    1. 사용자 입력에 부적절한 의료 요청(진단/처방)이 포함되었는지 확인.
    2. session state에서 patient_id를 시스템 인스트럭션에 주입.

    0. Run SafetyPlugin core checks (PII scan, cross-patient, prompt injection) first.
    1. Checks if user input contains inappropriate medical requests.
    2. Injects patient_id from session state into the system instruction.

    Returns:
        LlmResponse if the request should be blocked, None to proceed normally.
    """
    # ── Step 0: SafetyPlugin 공통 검사 / SafetyPlugin shared checks ──
    # PII 스캔, cross-patient 차단, 프롬프트 인젝션 탐지를 먼저 수행
    # Run PII scan, cross-patient blocking, prompt injection detection first
    safety_result = await safety_before_model_callback(callback_context, llm_request)
    if safety_result is not None:
        # SafetyPlugin이 차단 → 즉시 반환 / SafetyPlugin blocked → return immediately
        logger.warning("[Schedule] Request blocked by SafetyPlugin")
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
                "[Schedule] Blocked request containing '%s' from agent '%s'",
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
                                        "I can only help with scheduling and appointment management. "
                                        "For medical questions, please consult your healthcare provider."
                                    ),
                                    "disclaimer": _SCHEDULE_DISCLAIMER,
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
        logger.info("[Schedule] Injecting patient context: %s", patient_id)
        # 시스템 인스트럭션에 환자 ID 컨텍스트 추가
        # Append patient ID context to system instruction
        sys_instr = llm_request.config.system_instruction
        if sys_instr and isinstance(sys_instr, types.Content) and sys_instr.parts:
            ctx_note = f"\n\n[Session Context] Current patient_id: {patient_id}"
            sys_instr.parts[0].text = (sys_instr.parts[0].text or "") + ctx_note

    # None 반환 -> 정상적으로 LLM 호출 진행
    # Return None -> proceed with LLM call normally
    return None


async def _after_model_postprocess(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Post-model processing: SafetyPlugin 검사 + 응답 검증 + 면책 조항 첨부.

    0. SafetyPlugin 출력 검사 (PII 마스킹, HITL 게이트, 면책조항) 먼저 실행.
    1. 응답이 JSON인 경우 면책 조항(disclaimer) 필드 자동 삽입.
    2. 진단/처방 키워드가 포함된 응답을 차단.

    0. Run SafetyPlugin output checks (PII masking, HITL gate, disclaimer) first.
    1. Auto-injects disclaimer field if response is valid JSON.
    2. Blocks responses containing diagnostic/prescriptive keywords.

    Returns:
        Modified LlmResponse if changes are needed, None to pass through as-is.
    """
    # ── Step 0: SafetyPlugin 출력 검사 / SafetyPlugin output checks ──
    # PII 마스킹, HITL 게이트, 의료 면책조항 삽입
    # PII masking, HITL gate, medical disclaimer injection
    safety_result = await safety_after_model_callback(callback_context, llm_response)
    if safety_result is not None:
        # SafetyPlugin이 응답 수정 → 수정된 응답으로 계속 진행
        # SafetyPlugin modified response → continue with modified response
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
                "[Schedule] Post-model filter caught '%s' in response",
                keyword,
            )
            blocked_response = {
                "action": "error",
                "message": (
                    "The generated response was filtered because it contained "
                    "language outside the scope of scheduling. "
                    "Please rephrase your query focusing on appointments or reminders."
                ),
                "disclaimer": _SCHEDULE_DISCLAIMER,
            }
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=json.dumps(blocked_response, ensure_ascii=False))],
                )
            )

    # --- JSON 응답 후처리 / JSON response post-processing ---
    try:
        # JSON 파싱 시도: 코드블록 래핑 제거
        # Attempt JSON parse, stripping markdown code fences if present
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
            lines = lines[1:]  # 첫 줄 (```json) 제거
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # 마지막 줄 (```) 제거
            clean_text = "\n".join(lines)

        parsed = json.loads(clean_text)

        # disclaimer 자동 삽입 / Auto-inject disclaimer
        if isinstance(parsed, dict):
            parsed["disclaimer"] = _SCHEDULE_DISCLAIMER

        modified_text = json.dumps(parsed, ensure_ascii=False, indent=2)
        modified_parts = [deepcopy(part) for part in llm_response.content.parts]
        modified_parts[0].text = modified_text

        return LlmResponse(
            content=types.Content(role="model", parts=modified_parts),
            grounding_metadata=llm_response.grounding_metadata,
        )

    except (json.JSONDecodeError, ValueError):
        # JSON이 아닌 텍스트 응답 -> 면책 조항만 append
        # Non-JSON text response -> just append disclaimer
        logger.debug("[Schedule] Response is not JSON; appending disclaimer as text.")
        modified_parts = [deepcopy(part) for part in llm_response.content.parts]
        modified_parts[0].text = response_text + f"\n\n{_SCHEDULE_DISCLAIMER}"
        return LlmResponse(
            content=types.Content(role="model", parts=modified_parts),
            grounding_metadata=llm_response.grounding_metadata,
        )


# ---------------------------------------------------------------------------
# Agent Definition
# 에이전트 정의 -- LlmAgent 조립
# Agent assembly -- wiring prompt, tools, callbacks, and generation config
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Factory function — ADK single-parent 제약 대응
# Factory function — work around ADK single-parent constraint
#
# ADK는 각 에이전트 인스턴스가 단일 부모만 가질 수 있으므로, 동일 에이전트를
# 여러 워크플로우 + root standalone에 등록하려면 매번 새 인스턴스를 만들어야 함.
# ADK enforces single-parent ownership per instance, so we build a fresh
# instance whenever the same agent needs to be wired under multiple parents.
# ---------------------------------------------------------------------------
def build_schedule_agent(suffix: str = "") -> LlmAgent:
    """Schedule Agent 인스턴스 생성 / Build a new Schedule Agent instance.

    Args:
        suffix: name 충돌 방지용 접미사. 기본값 ""은 backward-compat용.
                Suffix appended to the agent name to avoid collisions.
    """
    return LlmAgent(
        name=f"schedule_agent{suffix}",
        model="gemini-2.5-flash",
        instruction=SCHEDULE_INSTRUCTION,
        tools=[
            check_availability,
            book_appointment,
            list_appointments,
            cancel_appointment,
            check_conflicts,
            # MCP: Google Calendar 연동 (설계도 반영)
            *get_calendar_tools(),
        ],
        output_key="schedule_result",
        description=(
            "Manages calendar events, appointment booking, and medication reminders. "
            "Handles conflict detection, fasting-test auto-scheduling, and advance notifications."
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,  # 낮은 temperature -> 일관성 있는 스케줄링 / Low temp -> consistent scheduling
            response_mime_type="application/json",
        ),
        before_model_callback=_before_model_guard,
        after_model_callback=_after_model_postprocess,
    )


# Backward-compat default export — 기존 임포트 호환용 기본 인스턴스
# Default instance kept for backward compatibility with existing imports.
schedule_agent = build_schedule_agent()

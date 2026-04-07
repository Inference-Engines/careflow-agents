# ============================================================================
# CareFlow Task Agent — Agent Assembly
# 태스크 에이전트 조립 및 콜백 정의
# ============================================================================
# LlmAgent 기반 약물 추출 + 안전성 검증 + 태스크 관리 에이전트.
# 진료 후 방문 기록에서 약물, 태스크, 경고를 구조화된 JSON으로 추출.
#
# LlmAgent-based medication extraction + safety validation + task management.
# Extracts medications, tasks, and warnings from post-visit notes as
# structured JSON.
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
from .prompt import TASK_INSTRUCTION
from .tools import (
    get_current_medications,
    add_medication,
    update_medication_status,
    log_medication_change,
    check_drug_interactions,
    lookup_medication_info,
    create_task,
    get_pending_tasks,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Callbacks (before_model / after_model)
# 모델 호출 전후 가드레일 및 후처리 콜백
# Pre/post model-call guardrails and post-processing callbacks
# ---------------------------------------------------------------------------

# 금지 키워드 — 정규식 패턴 기반 (false positive 대폭 감소).
# 이전: "stop taking" → "doctor said stop taking aspirin" 같은 정당한 문맥도 차단.
# 수정: 명령형/진단형 패턴만 잡도록 regex anchor 사용.
# Blocked patterns — regex-based to reduce false positives.
# Before: bare substring "stop taking" also blocked "doctor said stop taking aspirin".
# Now: only catches imperative/diagnostic patterns via regex anchors.
import re as _re
_BLOCKED_PATTERNS_INPUT = [
    _re.compile(r"\b(please\s+)?diagnose\s+me\b", _re.IGNORECASE),
    _re.compile(r"\b(can you|please)\s+(tell me my|give me a)\s+prognosis\b", _re.IGNORECASE),
    _re.compile(r"\byou\s+should\s+stop\s+taking\b", _re.IGNORECASE),
    _re.compile(r"\b(what|which)\s+(disease|illness)\s+do\s+i\s+have\b", _re.IGNORECASE),
    _re.compile(r"\bguarantee(d|s)?\s+(cure|recovery|result)\b", _re.IGNORECASE),
]
_BLOCKED_PATTERNS_OUTPUT = [
    _re.compile(r"\byou\s+(have|are\s+suffering\s+from)\s+[a-z]", _re.IGNORECASE),
    _re.compile(r"\bi\s+diagnose\s+you\b", _re.IGNORECASE),
    _re.compile(r"\byou\s+must\s+stop\s+taking\b", _re.IGNORECASE),
    _re.compile(r"\bguaranteed\s+(cure|recovery)\b", _re.IGNORECASE),
    _re.compile(r"\byour\s+prognosis\s+is\b", _re.IGNORECASE),
]

# 태스크 에이전트 면책 조항 — 모든 약물 관련 응답에 자동 첨부
# Task agent disclaimer — automatically appended to medication responses
_TASK_DISCLAIMER = (
    "This information is for reference only. All medication changes "
    "should be confirmed with your healthcare provider."
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
        logger.warning("[Task] Request blocked by SafetyPlugin")
        return safety_result

    # --- 사용자 입력 검사 / Inspect user input ---
    last_user_text = ""
    if llm_request.contents and llm_request.contents[-1].role == "user":
        parts = llm_request.contents[-1].parts
        if parts and parts[0].text:
            last_user_text = parts[0].text.lower()

    for pattern in _BLOCKED_PATTERNS_INPUT:
        match = pattern.search(last_user_text)
        if match:
            logger.warning(
                "[Task] Blocked request matching '%s' from agent '%s'",
                match.group(),
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
                                        "I can only help with medication extraction, "
                                        "task management, and drug interaction checks. "
                                        "For medical diagnoses, please consult your "
                                        "healthcare provider."
                                    ),
                                    "disclaimer": _TASK_DISCLAIMER,
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
        logger.info("[Task] Injecting patient context: %s", patient_id)
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

    # --- 진단/처방 패턴 사후 검사 / Post-hoc diagnostic pattern check ---
    for pattern in _BLOCKED_PATTERNS_OUTPUT:
        match = pattern.search(response_text)
        if match:
            logger.warning(
                "[Task] Post-model filter caught '%s' in response",
                match.group(),
            )
            blocked_response = {
                "action": "error",
                "message": (
                    "The generated response was filtered because it contained "
                    "language outside the scope of medication/task management. "
                    "Please rephrase your query."
                ),
                "disclaimer": _TASK_DISCLAIMER,
            }
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=json.dumps(blocked_response, ensure_ascii=False))],
                )
            )

    # --- HITL structured trigger — pending_hitl state 확인 / check pending_hitl ---
    # check_drug_interactions 등 tool이 pending_hitl을 state에 설정한 경우,
    # 해당 상호작용 경고를 응답 텍스트에 삽입하여 임상의/사용자 확인을 유도.
    pending = callback_context.state.get("pending_hitl")
    if pending and isinstance(pending, dict):
        hitl_notice = (
            f"\n\n⚠️ **CLINICIAN REVIEW REQUIRED** — {pending.get('action_type', 'drug interaction')} "
            f"detected (severity: {pending.get('severity', 'UNKNOWN')}, "
            f"source: {pending.get('source', 'unknown')}). "
            f"Please confirm with your healthcare provider before proceeding."
        )
        response_text = response_text + hitl_notice
        first_part.text = response_text
        # 한 번 소비 후 제거 — 중복 경고 방지
        callback_context.state["pending_hitl"] = None
        logger.info("[Task] HITL notice injected: %s", pending.get("severity"))

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
            parsed["disclaimer"] = _TASK_DISCLAIMER

        modified_text = json.dumps(parsed, ensure_ascii=False, indent=2)
        modified_parts = [deepcopy(part) for part in llm_response.content.parts]
        modified_parts[0].text = modified_text

        return LlmResponse(
            content=types.Content(role="model", parts=modified_parts),
            grounding_metadata=llm_response.grounding_metadata,
        )

    except (json.JSONDecodeError, ValueError):
        logger.debug("[Task] Response is not JSON; appending disclaimer as text.")
        modified_parts = [deepcopy(part) for part in llm_response.content.parts]
        modified_parts[0].text = response_text + f"\n\n{_TASK_DISCLAIMER}"
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
def build_task_agent(suffix: str = "") -> LlmAgent:
    """Task Agent 인스턴스 생성 / Build a new Task Agent instance.

    Args:
        suffix: name 충돌 방지용 접미사. 기본값 ""은 backward-compat용.
                Suffix appended to the agent name to avoid collisions.
    """
    return LlmAgent(
        name=f"task_agent{suffix}",
        model="gemini-2.5-flash",
        instruction=TASK_INSTRUCTION,
        tools=[
            get_current_medications,
            add_medication,
            update_medication_status,
            log_medication_change,
            check_drug_interactions,
            lookup_medication_info,
            create_task,
            get_pending_tasks,
        ],
        output_key="task_result",
        description=(
            "Extracts medications, follow-up tasks, and action items from visit notes. "
            "Performs drug interaction safety validation against the patient's current "
            "medication list. Manages medication changes and task priorities."
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,  # 낮은 temperature → 일관성 있는 추출 / Low temp → consistent extraction
        ),
        before_model_callback=_before_model_guard,
        after_model_callback=_after_model_postprocess,
    )


# Backward-compat default export — 기존 임포트 호환용 기본 인스턴스
# Default instance kept for backward compatibility with existing imports.
task_agent = build_task_agent()

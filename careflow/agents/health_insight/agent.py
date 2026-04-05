# ============================================================================
# CareFlow Health Insight Agent - Agent Assembly
# 건강 인사이트 에이전트 조립 및 콜백 정의
# ============================================================================
# LlmAgent 기반 프로액티브 건강 분석 에이전트.
# 축적된 건강 데이터에서 트렌드, 이상치, 상관관계를 감지하고
# 실행 가능한 인사이트를 JSON 형식으로 생성합니다.
#
# LlmAgent-based proactive health analytics agent.
# Detects trends, anomalies, and correlations from accumulated health data,
# generating actionable insights in structured JSON format.
# ============================================================================

import json
import logging
from copy import deepcopy
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
# Gemini API 제약: google_search는 FunctionTool과 함께 사용 불가
# Gemini API constraint: google_search cannot be combined with FunctionTools
# ("Multiple tools are supported only when they are all search tools")
# from google.adk.tools.google_search_tool import google_search
from google.genai import types

from careflow.agents.safety.plugin import (
    before_model_callback as safety_before_model_callback,
    after_model_callback as safety_after_model_callback,
)
from .prompt import HEALTH_INSIGHT_INSTRUCTION
from .tools import (
    calculate_trend,
    get_health_metrics,
    get_medication_history,
    get_visit_records,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Callbacks (before_model / after_model)
# 모델 호출 전후 가드레일 및 후처리 콜백
# Pre/post model-call guardrails and post-processing callbacks
# ---------------------------------------------------------------------------

# 금지 키워드 목록 — 진단/처방 행위 차단용
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

# 의료 면책 조항 — 모든 인사이트에 자동 첨부
# Medical disclaimer — automatically appended to every insight
_MEDICAL_DISCLAIMER = (
    "This analysis is based on recorded data and does not constitute "
    "medical advice. Please discuss findings with your healthcare provider."
)


async def _before_model_guard(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """Pre-model guardrail: SafetyPlugin 검사 + 입력 검증 + 컨텍스트 주입.

    0. SafetyPlugin 핵심 검사 (PII scan, cross-patient, prompt injection) 먼저 실행.
    1. 사용자 입력에 부적절한 의료 요청(진단/처방)이 포함되었는지 확인.
    2. session state에서 patient_id를 시스템 인스트럭션에 주입.

    0. Run SafetyPlugin core checks (PII scan, cross-patient, prompt injection) first.
    1. Checks if user input contains inappropriate medical requests (diagnosis/prescription).
    2. Injects patient_id from session state into the system instruction context.

    Returns:
        LlmResponse if the request should be blocked, None to proceed normally.
    """
    # ── Step 0: SafetyPlugin 공통 검사 / SafetyPlugin shared checks ──
    # PII 스캔, cross-patient 차단, 프롬프트 인젝션 탐지를 먼저 수행
    # Run PII scan, cross-patient blocking, prompt injection detection first
    safety_result = await safety_before_model_callback(callback_context, llm_request)
    if safety_result is not None:
        # SafetyPlugin이 차단 → 즉시 반환 / SafetyPlugin blocked → return immediately
        logger.warning("[HealthInsight] Request blocked by SafetyPlugin")
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
                "[HealthInsight] Blocked request containing '%s' from agent '%s'",
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
                                    "insight_type": "error",
                                    "severity": "INFO",
                                    "message": (
                                        "I cannot provide diagnoses or medication recommendations. "
                                        "Please consult your healthcare provider for medical decisions."
                                    ),
                                    "disclaimer": _MEDICAL_DISCLAIMER,
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
        logger.info(
            "[HealthInsight] Injecting patient context: %s", patient_id
        )
        # 시스템 인스트럭션에 환자 ID 컨텍스트 추가
        # Append patient ID context to system instruction
        sys_instr = llm_request.config.system_instruction
        if sys_instr and isinstance(sys_instr, types.Content) and sys_instr.parts:
            ctx_note = f"\n\n[Session Context] Current patient_id: {patient_id}"
            sys_instr.parts[0].text = (sys_instr.parts[0].text or "") + ctx_note

    # None 반환 → 정상적으로 LLM 호출 진행
    # Return None → proceed with LLM call normally
    return None


async def _after_model_postprocess(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> Optional[LlmResponse]:
    """Post-model processing: SafetyPlugin 검사 + 응답 검증 + 면책 조항 첨부.

    0. SafetyPlugin 출력 검사 (PII 마스킹, HITL 게이트, 면책조항) 먼저 실행.
    1. 응답이 JSON인 경우 면책 조항(disclaimer) 필드 자동 삽입.
    2. 진단/처방 키워드가 포함된 응답을 차단.
    3. confidence가 0.6 미만이면 경고 문구 추가.

    0. Run SafetyPlugin output checks (PII masking, HITL gate, disclaimer) first.
    1. Auto-injects disclaimer field if response is valid JSON.
    2. Blocks responses containing diagnostic/prescriptive keywords.
    3. Adds caution note when confidence is below 0.6.

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
                "[HealthInsight] Post-model filter caught '%s' in response",
                keyword,
            )
            blocked_response = {
                "insight_type": "error",
                "severity": "INFO",
                "message": (
                    "The generated insight was filtered because it contained "
                    "language that could be interpreted as medical advice. "
                    "Please rephrase your query focusing on data trends."
                ),
                "disclaimer": _MEDICAL_DISCLAIMER,
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
            # ```json ... ``` 또는 ``` ... ``` 패턴 처리
            lines = clean_text.split("\n")
            lines = lines[1:]  # 첫 줄 (```json) 제거
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]  # 마지막 줄 (```) 제거
            clean_text = "\n".join(lines)

        parsed = json.loads(clean_text)

        # disclaimer 자동 삽입 / Auto-inject disclaimer
        if isinstance(parsed, dict):
            parsed["disclaimer"] = _MEDICAL_DISCLAIMER

            # confidence 기반 경고 / Confidence-based caveat
            confidence = parsed.get("confidence")
            if confidence is not None and isinstance(confidence, (int, float)):
                if confidence < 0.6:
                    parsed["data_quality_note"] = (
                        "Limited data — interpret with caution."
                    )

        modified_text = json.dumps(parsed, ensure_ascii=False, indent=2)
        modified_parts = [deepcopy(part) for part in llm_response.content.parts]
        modified_parts[0].text = modified_text

        return LlmResponse(
            content=types.Content(role="model", parts=modified_parts),
            grounding_metadata=llm_response.grounding_metadata,
        )

    except (json.JSONDecodeError, ValueError):
        # JSON이 아닌 텍스트 응답 → 면책 조항만 append
        # Non-JSON text response → just append disclaimer
        logger.debug("[HealthInsight] Response is not JSON; appending disclaimer as text.")
        modified_parts = [deepcopy(part) for part in llm_response.content.parts]
        modified_parts[0].text = response_text + f"\n\n{_MEDICAL_DISCLAIMER}"
        return LlmResponse(
            content=types.Content(role="model", parts=modified_parts),
            grounding_metadata=llm_response.grounding_metadata,
        )


# ---------------------------------------------------------------------------
# Agent Definition
# 에이전트 정의 — LlmAgent 조립
# Agent assembly — wiring prompt, tools, callbacks, and generation config
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Factory function — ADK single-parent 제약 대응
# Factory function — work around ADK single-parent constraint
#
# 동일 에이전트를 여러 워크플로우 + root standalone에 등록하려면 인스턴스를
# 새로 만들어야 함. suffix로 name 충돌 방지.
# A fresh instance is required whenever the same agent is wired under
# multiple parents; use suffix to avoid name collisions.
# ---------------------------------------------------------------------------
def build_health_insight_agent(suffix: str = "") -> LlmAgent:
    """Health Insight Agent 인스턴스 생성 / Build a new Health Insight Agent."""
    return LlmAgent(
        name=f"health_insight_agent{suffix}",
        model="gemini-2.5-flash",
        instruction=HEALTH_INSIGHT_INSTRUCTION,
        tools=[
            get_health_metrics,
            get_medication_history,
            get_visit_records,
            calculate_trend,
            # Gemini API 제약: google_search는 FunctionTool과 함께 사용 불가
            # Gemini API constraint: google_search cannot coexist with FunctionTools
            # ("Multiple tools are supported only when they are all search tools")
            # google_search,
        ],
        output_key="health_insight_result",
        description=(
            "Analyzes accumulated health data for trends, anomalies, and correlations. "
            "Generates proactive health insights and pre-visit summaries in JSON format."
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,  # 낮은 temperature → 일관성 있는 분석 / Low temp → consistent analytics
            response_mime_type="application/json",
        ),
        before_model_callback=_before_model_guard,
        after_model_callback=_after_model_postprocess,
    )


# Backward-compat default export / 기존 임포트 호환용 기본 인스턴스
health_insight_agent = build_health_insight_agent()

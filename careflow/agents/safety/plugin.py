# Copyright 2026 CareFlow Team
#
# CareFlow SafetyPlugin — ADK callback 기반 안전 레이어
# ADK callback-based safety layer applied to all CareFlow agents.
#
# 설계 문서 참조 / Design doc reference:
#   CareFlow_System_Design_EN_somi.md — Section 3-10 SafetyPlugin
#
# ADK 공식 시그니처 / Official ADK callback signatures:
#   async def before_model_callback(callback_context, llm_request) -> None | LlmResponse
#   async def after_model_callback(callback_context, llm_response) -> None | LlmResponse

from __future__ import annotations

import logging
import re
from typing import Any

from google.adk.models import LlmResponse
from google.genai import types

# HITL 게이트 임포트 / HITL gate import
from careflow.agents.safety.hitl import (
    detect_risk_in_response,
    hitl_gate,
    process_confirmation_response,
    RiskLevel,
)

# Layer 2 scope judge 임포트 (Dr. Emily Watson 가이드의 Hybrid 2-Layer 설계)
# Layer 2 scope judge import (Hybrid 2-Layer design per Dr. Emily Watson's guidance)
from careflow.agents.safety.scope_judge import classify_scope

logger = logging.getLogger(__name__)

# =============================================================================
# 상수 정의 / Constants
# =============================================================================

# 프롬프트 인젝션 탐지용 위험 키워드 패턴
# Dangerous keyword patterns for prompt injection detection
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|to\s+be)\s+", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(safety|guidelines|rules)", re.IGNORECASE),
    re.compile(r"override\s+(safety|security|instructions?)", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system|internal)\s+(prompt|instructions?)", re.IGNORECASE),
]

# -----------------------------------------------------------------------------
# Hybrid 2-Layer 스코프 필터 / Hybrid 2-Layer scope filter
# -----------------------------------------------------------------------------
# 출처 / Source: Dr. Emily Watson (Healthcare AI Safety Researcher) 리뷰 권고.
# 기존 whitelist 기반 `_HEALTHCARE_KEYWORDS` 는 폐기되었다 — Lifestyle/감정/일상
# 질문을 과차단(false-block)하여 UX를 심각하게 해쳤기 때문.
#
# The previous whitelist-based `_HEALTHCARE_KEYWORDS` approach has been REMOVED
# on Dr. Emily Watson's recommendation — it over-blocked lifestyle/feeling/
# daily-life questions and severely hurt UX. Replaced by a hybrid pipeline:
#   Layer 1 (fast_prefilter, below):   ms-scale hard block for obvious off-topic
#   Layer 2 (scope_judge.classify_scope): Gemini 2.5 Flash LLM-as-Judge
# -----------------------------------------------------------------------------

# 사용자에게 되돌려주는 친절한 리다이렉트 메시지 / Friendly redirect to user
REDIRECT_MESSAGE = (
    "I'm CareFlow, your diabetes and blood pressure companion. "
    "I can't help with that, but I'm here for anything about your health, "
    "meals, medications, activity, or how you're feeling today. "
    "What's on your mind?"
)

# Layer 1 — 명백한 off-topic hard-block 패턴 (whitelist 아님, blacklist)
# Layer 1 — obvious off-topic hard-block patterns (blacklist, NOT whitelist).
# 반드시 매우 보수적으로 유지할 것 — 조금이라도 애매하면 Layer 2 가 처리.
# Keep this list extremely conservative — anything borderline is Layer 2's job.
_HARD_BLOCK_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(write|generate|compose)\s+(a\s+)?(poem|song|story|essay)\b", re.IGNORECASE),
    re.compile(r"\b(stock|crypto|bitcoin)\s+(price|tip|advice|prediction)\b", re.IGNORECASE),
    re.compile(r"\b(hack|exploit|jailbreak)\b", re.IGNORECASE),
    re.compile(r"\b(homework|math\s+problem|solve\s+this\s+equation)\b", re.IGNORECASE),
]

# PII 패턴 — 인도 Aadhaar, 전화번호, 이메일
# PII patterns — Indian Aadhaar number, phone numbers, email addresses
_PII_PATTERNS: dict[str, re.Pattern] = {
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),          # 12자리 Aadhaar
    "phone": re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b"),         # 인도 휴대폰 / Indian mobile
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
}

# 의료 조언/진단/처방 관련 키워드 — 면책조항 삽입 트리거
# Medical recommendation keywords — triggers disclaimer injection
_MEDICAL_RECOMMENDATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(recommend|suggest|advise|prescri|diagnos|indicat)", re.IGNORECASE),
    re.compile(r"\b(take\s+\d+\s*mg|dosage|dose)\b", re.IGNORECASE),
    re.compile(r"\b(you\s+(should|may|might)\s+(take|try|consider|consult))\b", re.IGNORECASE),
    re.compile(r"\b(treatment\s+plan|medication\s+change)\b", re.IGNORECASE),
]

# 의료 면책조항 / Medical disclaimer
MEDICAL_DISCLAIMER = (
    "\n\n⚠️ This information is for reference only. "
    "All medical decisions should be discussed with your healthcare provider."
)


# =============================================================================
# 내부 헬퍼 함수 / Internal helper functions
# =============================================================================

def _extract_user_text(llm_request: Any) -> str:
    """LLM 요청에서 사용자 텍스트를 추출한다.
    Extract user text from the LLM request contents.

    ADK의 llm_request.contents에서 마지막 user 메시지의 텍스트 파트를 가져온다.
    Retrieves text parts from the last user message in llm_request.contents.
    """
    try:
        contents = llm_request.contents or []
        for content in reversed(contents):
            if getattr(content, "role", None) == "user":
                parts = getattr(content, "parts", [])
                texts = [getattr(p, "text", "") for p in parts if getattr(p, "text", None)]
                return " ".join(texts)
    except (AttributeError, TypeError):
        pass
    return ""


def _extract_response_text(llm_response: Any) -> str:
    """LLM 응답에서 텍스트를 추출한다.
    Extract text from the LLM response content.
    """
    try:
        content = llm_response.content
        if content and hasattr(content, "parts"):
            texts = [getattr(p, "text", "") for p in content.parts if getattr(p, "text", None)]
            return " ".join(texts)
    except (AttributeError, TypeError):
        pass
    return ""


def _build_block_response(message: str) -> LlmResponse:
    """차단 응답을 생성한다. short-circuit용 LlmResponse.
    Build a blocking response that short-circuits the LLM call.

    ADK 패턴: before_model_callback에서 None이 아닌 값을 반환하면
    LLM 호출을 건너뛴다.
    ADK pattern: returning non-None from before_model_callback skips the LLM call.

    반환 타입을 GenerateContentResponse에서 LlmResponse로 수정 —
    ADK 공식 콜백이 LlmResponse를 기대함.
    Changed return type from GenerateContentResponse to LlmResponse —
    ADK official callbacks expect LlmResponse.
    """
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(text=message)],
        ),
    )


def _detect_prompt_injection(text: str) -> bool:
    """프롬프트 인젝션 공격 탐지 / Detect prompt injection attacks."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning("[SafetyPlugin] Prompt injection detected: pattern=%s", pattern.pattern)
            return True
    return False


def fast_prefilter(text: str) -> str:
    """Layer 1: Fast prefilter (hard block only) — target latency < 1ms.

    Dr. Emily Watson 가이드에 따라 whitelist 방식을 폐기하고, 명백한 off-topic만
    정규식으로 즉시 차단한다. 애매한 건 Layer 2 (Gemini Flash judge) 에 위임.

    Per Dr. Emily Watson's guidance, the whitelist approach is abandoned. This
    prefilter ONLY hard-blocks obvious off-topic patterns via regex; anything
    borderline falls through to Layer 2 (Gemini Flash judge).

    Returns:
        "hard_block" — 즉시 차단 / block immediately
        "pass"       — Layer 2 로 전달 / forward to Layer 2
    """
    if not text:
        return "pass"
    for pattern in _HARD_BLOCK_PATTERNS:
        if pattern.search(text):
            logger.info(
                "safety.layer1.hard_block",
                extra={"pattern": pattern.pattern, "message_len": len(text)},
            )
            return "hard_block"
    return "pass"


def _is_healthcare_related(text: str) -> bool:
    """DEPRECATED / LEGACY — DO NOT USE.

    이 함수는 Dr. Emily Watson 리뷰 권고에 따라 폐기되었다.
    Whitelist 기반 도메인 판정은 lifestyle/feelings/daily-life 질문을 과차단하여
    CareFlow의 핵심 UX(공감적 만성질환 동반자)를 훼손한다.
    대신 `fast_prefilter` (Layer 1) + `scope_judge.classify_scope` (Layer 2)를 사용할 것.

    DEPRECATED per Dr. Emily Watson's safety review. The whitelist-based domain
    check over-blocked lifestyle/feelings/daily-life questions, damaging
    CareFlow's core UX as an empathetic chronic-disease companion. Use
    `fast_prefilter` (Layer 1) + `scope_judge.classify_scope` (Layer 2) instead.
    """
    # 항상 True — 안전한 기본값, 호출자는 새로운 2-Layer 파이프라인으로 이동해야 함.
    # Always True — safe default; callers should migrate to the 2-Layer pipeline.
    return True


def _scan_pii(text: str) -> dict[str, list[str]]:
    """텍스트에서 PII를 스캔한다 / Scan text for PII.

    Returns:
        dict: 탐지된 PII 타입 → 매칭된 값 목록
              detected PII type → list of matched values
    """
    found: dict[str, list[str]] = {}
    for pii_type, pattern in _PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            found[pii_type] = matches
    return found


def _mask_pii(text: str) -> str:
    """텍스트 내 PII를 마스킹한다 / Mask PII in text.

    Aadhaar: XXXX-XXXX-1234 (마지막 4자리만 노출)
    Phone:   ******7890 (마지막 4자리만 노출)
    Email:   a***@example.com (첫 글자만 노출)
    """
    # Aadhaar 마스킹 — 마지막 4자리만 노출 / mask all but last 4 digits
    def _mask_aadhaar(match: re.Match) -> str:
        digits = re.sub(r"\s", "", match.group())
        return f"XXXX-XXXX-{digits[-4:]}"

    text = _PII_PATTERNS["aadhaar"].sub(_mask_aadhaar, text)

    # 전화번호 마스킹 / Phone masking
    def _mask_phone(match: re.Match) -> str:
        digits = re.sub(r"[\s\-+]", "", match.group())
        return f"******{digits[-4:]}"

    text = _PII_PATTERNS["phone"].sub(_mask_phone, text)

    # 이메일 마스킹 / Email masking
    def _mask_email(match: re.Match) -> str:
        email = match.group()
        local, domain = email.split("@", 1)
        return f"{local[0]}***@{domain}"

    text = _PII_PATTERNS["email"].sub(_mask_email, text)

    return text


def _contains_medical_recommendation(text: str) -> bool:
    """응답에 의료 조언/진단/처방 내용이 포함되어 있는지 확인
    Check if response contains medical advice/diagnosis/prescription content.
    """
    for pattern in _MEDICAL_RECOMMENDATION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _set_response_text(llm_response: Any, new_text: str) -> Any:
    """LLM 응답의 텍스트를 교체한다 / Replace text in the LLM response.

    원본 응답 구조를 최대한 유지하면서 텍스트만 변경한다.
    Preserves the original response structure, only modifying text content.
    """
    try:
        if llm_response.content and llm_response.content.parts:
            new_parts = []
            for part in llm_response.content.parts:
                if getattr(part, "text", None) is not None:
                    new_parts.append(types.Part(text=new_text))
                else:
                    new_parts.append(part)
            llm_response.content.parts = new_parts
    except (AttributeError, TypeError):
        pass
    return llm_response


# =============================================================================
# ADK 공식 콜백 / Official ADK Callbacks
# =============================================================================

async def before_model_callback(
    callback_context: Any,
    llm_request: Any,
) -> Any | None:
    """LLM 호출 전 입력 안전 검증 / Pre-LLM input safety validation.

    ADK 공식 시그니처를 정확히 따른다.
    Follows the official ADK callback signature exactly.

    Returns:
        None — 통과, LLM 호출 진행 / pass through, proceed with LLM call
        LlmResponse — short-circuit, LLM 호출 건너뜀 / skip LLM call
    """
    user_text = _extract_user_text(llm_request)

    # ── Step -1: HITL 사용자 승인 루프 / HITL user confirmation loop ──
    #   session state에 pending_confirmation이 있으면 사용자 응답을 먼저 처리
    #   If pending_confirmation exists in session state, process user response first
    try:
        state = getattr(callback_context, "state", {}) or {}
        pending = state.get("pending_confirmation")
        if pending and user_text:
            result = process_confirmation_response(user_text, pending)

            if result["status"] == "approved":
                # 승인됨 → pending 상태 제거, 정상 진행
                # Approved → clear pending state, proceed normally
                logger.info("[SafetyPlugin] HITL confirmed — action approved")
                callback_context.state.pop("pending_confirmation", None)
                return _build_block_response(
                    "Confirmed. Proceeding with the requested action.\n"
                    "확인되었습니다. 요청하신 액션을 진행합니다."
                )

            elif result["status"] == "denied":
                # 거부됨 → pending 상태 제거, 액션 취소 메시지 반환
                # Denied → clear pending state, return cancellation message
                logger.info("[SafetyPlugin] HITL denied — action cancelled")
                callback_context.state.pop("pending_confirmation", None)
                return _build_block_response(result["message"])

            else:
                # 인식 불가 → 재확인 요청 / Unrecognized → re-ask
                logger.info("[SafetyPlugin] HITL re-ask — unrecognized response")
                return _build_block_response(result["message"])
    except (AttributeError, TypeError):
        pass

    # ── Step 0: Cross-patient 접근 차단 / Cross-patient access blocking ──
    #   현재 환자가 아닌 다른 환자의 정보에 접근하려는 시도를 차단
    #   Block attempts to access another patient's information
    current_patient_id = None
    try:
        state = getattr(callback_context, "state", {}) or {}
        current_patient_id = state.get("current_patient_id")
    except (AttributeError, TypeError):
        pass

    if current_patient_id:
        # 다른 환자 ID 패턴 탐지 — "patient 12345", "patient_id: 999" 등
        # Detect other patient ID patterns — "patient 12345", "patient_id: 999", etc.
        patient_id_pattern = re.compile(
            r"\b(?:patient[_\s-]*(?:id)?[:\s]*(\w+))\b", re.IGNORECASE
        )
        matches = patient_id_pattern.findall(user_text)
        for matched_id in matches:
            if matched_id and str(matched_id) != str(current_patient_id):
                logger.warning(
                    "[SafetyPlugin] Cross-patient access blocked: "
                    "current=%s, attempted=%s",
                    current_patient_id,
                    matched_id,
                )
                return _build_block_response(
                    "🚫 Access denied. You can only access information for "
                    "the currently authenticated patient. "
                    "Cross-patient data access is not permitted."
                )

    # ── Step 1: PII 입력 스캐너 (Step 0 수준으로 이동) ──
    #   PII scan/mask FIRST — before prompt-injection & scope-judge (Flash) calls.
    #   이유: Flash LLM judge 에 도달하기 **전에** 마스킹해서 외부 전송을 차단.
    #   Rationale: mask BEFORE reaching the Flash LLM judge so no PII ever
    #   leaves the service boundary. Also ensures downstream regex checks run
    #   on the masked variant.
    #
    #   음성 입력 시 환자가 Aadhaar 번호를 말할 수 있으므로 LLM 도달 전 제거.
    #   Patients may speak Aadhaar numbers via voice input; redact before LLM.
    pii_found = _scan_pii(user_text)
    if pii_found:
        user_text = _mask_pii(user_text)  # 이후 모든 검사는 마스킹된 버전 사용
        logger.info(
            "[SafetyPlugin] PII detected in input — types=%s, redacting before LLM",
            list(pii_found.keys()),
        )
        # llm_request의 마지막 user 메시지를 정제된 텍스트로 교체
        # Replace last user message in llm_request with redacted text
        try:
            contents = llm_request.contents or []
            for content in reversed(contents):
                if getattr(content, "role", None) == "user":
                    for part in content.parts:
                        if getattr(part, "text", None) is not None:
                            part.text = user_text
                    break
        except (AttributeError, TypeError):
            pass

    # ── Step 2: 프롬프트 인젝션 탐지 / Prompt injection detection ──
    if _detect_prompt_injection(user_text):
        logger.warning("[SafetyPlugin] Blocked: prompt injection attempt")
        return _build_block_response(
            "🚫 Your input has been blocked by our safety policy. "
            "Please rephrase your request."
        )

    # ── Step 3: Hybrid 2-Layer 스코프 필터 / Hybrid 2-Layer scope filter ──
    #   Dr. Emily Watson (Healthcare AI Safety) 권고에 따른 설계.
    #   Per Dr. Emily Watson's (Healthcare AI Safety) recommendation.
    #
    #   이 시점에서 user_text 는 이미 PII-마스킹된 상태 — Flash judge 에 절대
    #   원본 PII 가 전달되지 않도록 보장한다.
    #   By this point user_text is already PII-masked — guarantees the Flash
    #   judge never sees raw PII.
    #
    #   Layer 1: fast regex prefilter — 명백한 off-topic 즉시 차단 (<1ms)
    #            Hard-blocks obvious off-topic instantly (<1ms).
    #   Layer 2: Gemini 2.5 Flash LLM-as-Judge — 애매한 건 판단, fail-open
    #            Nuanced classification via Gemini Flash, fail-open on error.
    if user_text and fast_prefilter(user_text) == "hard_block":
        logger.info("[SafetyPlugin] Blocked by Layer 1 fast prefilter")
        return _build_block_response(REDIRECT_MESSAGE)

    # sub-agent 가 root 에서 이미 scope check 를 했다면 중복 호출 skip
    # (Issue 4: sub-agent 콜백 중복 제거)
    # Skip if the root already ran scope check for this turn
    # (Issue 4: deduplicate sub-agent scope checks).
    scope_already_checked = False
    try:
        state = getattr(callback_context, "state", {}) or {}
        scope_already_checked = bool(state.get("scope_checked_at_root"))
    except (AttributeError, TypeError):
        scope_already_checked = False

    if user_text and not scope_already_checked:
        verdict = await classify_scope(user_text)
        logger.info(
            "scope.judge.verdict",
            extra={
                "label": verdict.get("label"),
                "confidence": verdict.get("confidence"),
                "reason": verdict.get("reason"),
            },
        )
        # 한 턴에 한 번만 Flash judge 호출되도록 플래그 세팅
        # Mark the turn so sub-agents can skip redundant scope checks.
        try:
            if hasattr(callback_context, "state") and callback_context.state is not None:
                callback_context.state["scope_checked_at_root"] = True
        except (AttributeError, TypeError):
            pass

        # SAFE DEFAULT: out_of_scope + confidence >= 0.90 일 때만 차단.
        # 그 외 (in_scope, ambiguous, 낮은 confidence out_of_scope) 는 메인 모델이 판단.
        # SAFE DEFAULT: only block when out_of_scope AND confidence >= 0.90.
        # Everything else (in_scope, ambiguous, low-conf out_of_scope) passes
        # through for the main model to handle.
        if (
            verdict.get("label") == "out_of_scope"
            and float(verdict.get("confidence", 0.0)) >= 0.90
        ):
            logger.info(
                "[SafetyPlugin] Blocked by Layer 2 scope judge",
                extra={"confidence": verdict.get("confidence"), "reason": verdict.get("reason")},
            )
            return _build_block_response(REDIRECT_MESSAGE)
    elif scope_already_checked:
        logger.debug("[SafetyPlugin] scope check skipped — already done at root")

    # 통과 — LLM 호출 계속 / Pass — proceed with LLM call
    return None


async def after_model_callback(
    callback_context: Any,
    llm_response: Any,
) -> Any | None:
    """LLM 응답 후 출력 안전 검증 / Post-LLM output safety validation.

    ADK 공식 시그니처를 정확히 따른다.
    Follows the official ADK callback signature exactly.

    Returns:
        None — 통과, 원본 응답 그대로 반환 / pass through, return original response
        LlmResponse — 수정된 응답 반환 / return modified response
    """
    response_text = _extract_response_text(llm_response)
    if not response_text:
        return None  # 텍스트 없으면 패스 / no text, pass through

    modified = False

    # ── Step 1: PII 마스킹 (출력) / PII masking (output) ──
    pii_found = _scan_pii(response_text)
    if pii_found:
        response_text = _mask_pii(response_text)
        logger.info(
            "[SafetyPlugin] PII masked in output — types=%s",
            list(pii_found.keys()),
        )
        modified = True

    # ── Step 2: HITL 게이트 — 고위험 응답 감지 / HITL gate — high-risk response detection ──
    #   응답 텍스트에서 고위험 액션 키워드를 감지하여 확인 요청을 삽입한다.
    #   Detect high-risk action keywords in response and insert confirmation request.
    detected_action, detected_risk = detect_risk_in_response(response_text)
    if detected_action and detected_risk:
        # HITL 게이트 호출 / Call HITL gate
        hitl_result = await hitl_gate(
            action_type=detected_action,
            action_details={"description": detected_action, "details": response_text[:300]},
            context={},
        )
        if hitl_result.get("status") == "pending_confirmation":
            # pending_confirmation을 session state에 저장 — 다음 턴에서 승인 루프 처리
            # Save pending_confirmation to session state — processed in next turn's approval loop
            try:
                state = getattr(callback_context, "state", None)
                if state is not None:
                    state["pending_confirmation"] = {
                        "confirmation_id": hitl_result.get("confirmation_id"),
                        "action": hitl_result.get("action"),
                        "risk_level": hitl_result.get("risk_level"),
                    }
                    logger.info(
                        "[SafetyPlugin] Pending confirmation saved to session state: id=%s",
                        hitl_result.get("confirmation_id"),
                    )
            except (AttributeError, TypeError):
                logger.warning("[SafetyPlugin] Failed to save pending_confirmation to state")

            # 확인 메시지를 응답 앞에 삽입 / Prepend confirmation message to response
            confirmation_msg = hitl_result["message"]
            response_text = f"{confirmation_msg}\n\n---\n\n{response_text}"
            modified = True
            logger.info(
                "[SafetyPlugin] HITL confirmation injected: action=%s, risk=%s",
                detected_action,
                detected_risk.value,
            )

    # ── Step 3: 의료 면책조항 자동 삽입 / Auto-insert medical disclaimer ──
    #   진단/처방 관련 응답에만 삽입 — 불필요한 면책조항은 UX를 해침
    #   Only inject for diagnosis/prescription responses — unnecessary disclaimers hurt UX
    if _contains_medical_recommendation(response_text):
        if MEDICAL_DISCLAIMER not in response_text:
            response_text += MEDICAL_DISCLAIMER
            modified = True
            logger.info("[SafetyPlugin] Medical disclaimer injected")

    if modified:
        _set_response_text(llm_response, response_text)
        return llm_response

    return None  # 수정 없음 — 원본 그대로 / no modifications — keep original

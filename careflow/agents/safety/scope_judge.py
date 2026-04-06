# Copyright 2026 CareFlow Team
#
# CareFlow Scope Judge — Gemini Flash 기반 LLM-as-Judge (Layer 2)
# Gemini Flash-powered LLM-as-Judge for scope classification (Layer 2).
#
# 출처 / Source:
#   Dr. Emily Watson (Healthcare AI Safety) 가이드에 따른 Hybrid 2-Layer 설계.
#   Per Dr. Emily Watson's (Healthcare AI Safety) guidance: Hybrid 2-Layer design.
#   Layer 1 (plugin.py fast_prefilter) blocks obvious off-topic;
#   Layer 2 (this module) uses Gemini 2.5 Flash for nuanced scope classification.
#
# 핵심 원칙 / Core principles:
#   - Fail-open: LLM 오류 시 "ambiguous" 반환 → 메인 모델이 판단하도록
#     Fail-open: on LLM error return "ambiguous" → let main model decide
#   - 높은 confidence(>=0.90) 일 때만 out_of_scope 차단 허용
#     Only allow out_of_scope block when confidence >= 0.90
#   - Lifestyle/body/feelings 질문은 절대 out_of_scope로 판정 금지
#     Never classify lifestyle/body/feelings questions as out_of_scope

from __future__ import annotations

import json
import logging
import re
from typing import Any

# Rate limiter — 429 방어를 위해 genai Client 사용 전에 패치 적용
# Ensure genai is monkey-patched before any Client usage
import careflow.rate_limiter  # noqa: F401

logger = logging.getLogger(__name__)

# Gemini 2.5 Flash 모델명 / Gemini 2.5 Flash model name
_JUDGE_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Flash 429 방어 / Flash 429 defense
# ---------------------------------------------------------------------------
# 1) genai.Client() 싱글턴 — 매 호출마다 새 클라이언트를 만들면 소켓/인증이
#    반복 초기화되어 rate limit 에 더 쉽게 걸린다.
# 2) 메시지 기반 캐시 — 동일 메시지 반복 호출 시 Flash를 건너뛴다.
# 3) 짧은 메시지 / greeting 은 Flash 호출 자체를 skip.
#
# 1) Module-level genai.Client() singleton — creating a new client per call
#    reinitializes sockets/auth and makes rate limits much easier to hit.
# 2) Message-based memoization cache — skip Flash for repeated messages.
# 3) Short messages / greetings skip the Flash call entirely.
# ---------------------------------------------------------------------------
_GENAI_CLIENT: Any = None  # lazy singleton / 지연 싱글턴

# 간단한 dict 기반 메모이제이션 (async lru_cache 대체)
# Simple dict-based memoization (stand-in for async lru_cache)
_SCOPE_CACHE: dict[str, dict[str, Any]] = {}
_SCOPE_CACHE_MAX = 512  # 메모리 leak 방지용 상한 / cap to avoid memory leak

# Greeting / 인사말 패턴 — Flash 호출 skip
_GREETING_PATTERNS = re.compile(
    r"^\s*(hi|hello|hey|thanks|thank\s+you|bye|goodbye|ok|okay|yes|no|sure)\s*[!.?]*\s*$",
    re.IGNORECASE,
)


def _get_genai_client() -> Any:
    """genai.Client 싱글턴 반환 / Return the module-level genai.Client singleton.

    지연 초기화 — 첫 호출 시에만 Client() 생성. 이후는 재사용하여 429 방어.
    Lazy init — construct the Client() once on first call; reuse thereafter
    to reduce the chance of hitting Flash rate limits.
    """
    global _GENAI_CLIENT
    if _GENAI_CLIENT is None:
        from google import genai
        _GENAI_CLIENT = genai.Client()
    return _GENAI_CLIENT

# LLM-as-Judge 시스템 프롬프트 / LLM-as-Judge system prompt
# Dr. Watson 가이드의 CRITICAL RULES를 그대로 포함.
# Embeds CRITICAL RULES from Dr. Watson's guidance verbatim.
_JUDGE_PROMPT = """You are a scope classifier for CareFlow, an AI assistant built specifically for chronic disease patients managing Type 2 Diabetes (DM2) and Hypertension (HTN). Your only job is to classify a user's message into one of three labels and return JSON.

# Labels
- "in_scope": clearly related to the patient's health, body, daily life, meals, drinks, sleep, mood, stress, travel, exercise, medications, symptoms, appointments, or general wellbeing.
- "ambiguous": unclear, could be health-related or social small talk, greetings, or vague questions.
- "out_of_scope": clearly unrelated to health/lifestyle — e.g. writing poems/songs/essays, stock/crypto tips, hacking, solving math homework, celebrity gossip.

# CRITICAL RULES (MUST follow)
1. Lifestyle questions (food, drink, sleep, travel, stress, exercise) are ALWAYS "in_scope". No exceptions.
2. NEVER return "out_of_scope" with confidence below 0.90. If you are unsure, use "ambiguous".
3. If the message mentions the user's body, feelings, food, sleep, or daily routine in ANY way, it is NEVER "out_of_scope". Classify as "in_scope" or at worst "ambiguous".
4. Greetings ("hi", "hello", "how are you") and meta questions ("what can you do?") are "in_scope".
5. Short or vague messages should be "ambiguous", not "out_of_scope".

# Output format
Return ONLY a single JSON object, no prose, no markdown fences:
{"label": "in_scope" | "ambiguous" | "out_of_scope", "confidence": <float 0.0-1.0>, "reason": "<short english reason>"}

# User message
"""


def _parse_json_response(raw: str) -> dict[str, Any] | None:
    """LLM의 raw 텍스트에서 JSON 객체를 안전하게 파싱한다.
    Safely parse a JSON object from the LLM's raw text.

    response_mime_type="application/json"을 강제하지만, Gemini가 드물게
    마크다운 펜스를 섞거나 여분의 텍스트를 뱉는 경우에도 살아남아야 한다.
    Although we force response_mime_type="application/json", this function
    must survive edge cases where Gemini still emits markdown fences or
    extra prose around the JSON payload.

    반환값이 dict가 아니면 (list/str/number 등) None을 반환 →
    호출자가 fail-open 처리를 하도록 보장한다.
    Returns None if the parsed payload is not a dict (list/str/number/etc.),
    ensuring the caller falls through to fail-open handling.
    """
    if not raw:
        return None
    try:
        text = raw.strip()
        if not text:
            return None
        # 마크다운 펜스 제거 / strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # 1차: 전체 텍스트를 곧바로 파싱 (mime_type=json일 때 best path)
        # First try: parse the entire text directly (best path with mime_type=json)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 2차: 첫 번째 JSON 오브젝트만 추출해서 파싱
        # Fallback: extract the first JSON object substring
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed
    except Exception:  # noqa: BLE001 — fail-open by design
        # 예상치 못한 정규식/디코딩 오류까지 모두 삼켜서 fail-open 보장
        # Swallow any unexpected regex/decoding errors to guarantee fail-open
        return None


def _ambiguous(reason: str) -> dict[str, Any]:
    """Fail-open 기본값 / Fail-open default."""
    return {"label": "ambiguous", "confidence": 0.0, "reason": reason}


async def classify_scope(message: str) -> dict[str, Any]:
    """사용자 메시지의 스코프를 분류한다 / Classify the scope of a user message.

    Returns:
        dict with keys:
            label: "in_scope" | "ambiguous" | "out_of_scope"
            confidence: float in [0.0, 1.0]
            reason: short string explanation

    Fail-open 정책 / Fail-open policy:
        Gemini 호출 실패, 파싱 실패, 유효하지 않은 라벨 — 모두 "ambiguous" 반환.
        Any LLM/parse/validation failure → return "ambiguous" so the main model decides.
    """
    if not message or not message.strip():
        return _ambiguous("empty message")

    stripped = message.strip()

    # ── Fast-path 1: 매우 짧은 메시지 → 즉시 in_scope (Flash 호출 skip) ──
    # Fast-path 1: very short messages → in_scope immediately, skip Flash.
    if len(stripped) < 3:
        return {"label": "in_scope", "confidence": 1.0, "reason": "empty/short"}

    # ── Fast-path 2: greeting/인사말 → 즉시 in_scope (Flash 호출 skip) ──
    # Fast-path 2: greetings → in_scope immediately, skip Flash.
    if _GREETING_PATTERNS.match(stripped):
        return {"label": "in_scope", "confidence": 1.0, "reason": "greeting"}

    # ── Fast-path 2.5: 의료 키워드 → 즉시 in_scope (RPM 절약) ──
    # Fast-path 2.5: medical keywords → in_scope immediately, saves RPM.
    _MEDICAL_KEYWORDS = {
        "blood pressure", "bp", "sugar", "glucose", "hba1c", "diabetes",
        "hypertension", "medication", "medicine", "pill", "tablet", "dose",
        "doctor", "appointment", "dizzy", "pain", "nausea", "headache",
        "symptom", "chest", "heart", "breathing", "shaking", "tremor",
        "diet", "sodium", "salt", "food", "eat", "lunch", "dinner",
        "exercise", "walk", "weight", "test", "lab", "report",
        "metformin", "amlodipine", "aspirin", "atorvastatin", "lisinopril",
        "caregiver", "father", "mother", "daughter", "priya",
        "trending", "insight", "health", "medical", "visit", "follow-up",
    }
    lower = stripped.lower()
    if any(kw in lower for kw in _MEDICAL_KEYWORDS):
        return {"label": "in_scope", "confidence": 0.95, "reason": "medical_keyword"}

    # ── Fast-path 3: 메모이제이션 캐시 히트 → Flash 호출 skip ──
    # Fast-path 3: memoization cache hit → skip Flash.
    cache_key = stripped.lower()[:200]
    cached = _SCOPE_CACHE.get(cache_key)
    if cached is not None:
        logger.debug("scope.judge.cache_hit", extra={"key_len": len(cache_key)})
        return cached

    # Gemini 2.5 Flash 호출 / Call Gemini 2.5 Flash
    # google-genai SDK를 사용 (careflow 전반에서 이미 사용 중).
    # Uses google-genai SDK (already used throughout careflow).
    #
    # response_mime_type="application/json"을 강제하여 Gemini가 JSON만 뱉도록
    # 한다. 그래도 파싱이 실패하면 아래에서 무조건 fail-open (ambiguous) 처리.
    # We force response_mime_type="application/json" so Gemini only emits
    # JSON. Any remaining parse failure is unconditionally fail-open below.
    raw_text = ""
    try:
        from google.genai import types as genai_types

        # 싱글턴 클라이언트 재사용 → 429 방어
        # Reuse singleton client → 429 defense
        client = _get_genai_client()
        response = await client.aio.models.generate_content(
            model=_JUDGE_MODEL,
            contents=_JUDGE_PROMPT + message.strip(),
            config=genai_types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                max_output_tokens=256,
            ),
        )
        raw_text = getattr(response, "text", "") or ""
    except Exception as exc:  # noqa: BLE001 — fail-open by design
        logger.warning("scope.judge.error", extra={"error": str(exc)})
        return _ambiguous(f"llm_error: {type(exc).__name__}")

    # 파싱 단계도 방어적으로 감싸서, 어떤 예외가 나와도 ambiguous를 반환하도록 보장
    # Wrap parsing defensively so any exception still returns ambiguous (fail-open)
    try:
        parsed = _parse_json_response(raw_text)
        if not parsed or not isinstance(parsed, dict) or "label" not in parsed:
            logger.warning("scope.judge.parse_error", extra={"raw": raw_text[:200]})
            return _ambiguous("parse_error")

        label = str(parsed.get("label", "")).lower().strip()
        if label not in {"in_scope", "ambiguous", "out_of_scope"}:
            logger.warning("scope.judge.invalid_label", extra={"label": label})
            return _ambiguous(f"invalid_label:{label}")

        try:
            confidence = float(parsed.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        reason = str(parsed.get("reason", ""))[:200]
    except Exception as exc:  # noqa: BLE001 — fail-open by design
        # 파싱/검증 중 예상치 못한 오류 → 무조건 ambiguous 반환
        # Unexpected error during parse/validate → unconditionally ambiguous
        logger.warning(
            "scope.judge.unexpected_parse_error",
            extra={"error": str(exc), "raw": raw_text[:200]},
        )
        return _ambiguous(f"unexpected_parse_error: {type(exc).__name__}")

    verdict = {"label": label, "confidence": confidence, "reason": reason}
    logger.info(
        "scope.judge",
        extra={
            "label": label,
            "confidence": confidence,
            "reason": reason,
            "message_len": len(message),
        },
    )

    # 캐시에 저장 — 동일 메시지 반복 시 Flash 호출 skip
    # Cache the verdict — subsequent identical messages skip the Flash call.
    # 단순한 LRU: 상한 초과 시 가장 오래된 항목(삽입 순) 하나 제거.
    # Simple LRU: when over the cap, pop the oldest inserted item.
    if len(_SCOPE_CACHE) >= _SCOPE_CACHE_MAX:
        try:
            _SCOPE_CACHE.pop(next(iter(_SCOPE_CACHE)))
        except StopIteration:
            pass
    _SCOPE_CACHE[cache_key] = verdict
    return verdict

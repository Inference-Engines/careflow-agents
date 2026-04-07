"""
Symptom Triage Agent — LlmAgent Assembly
증상 분류 에이전트 — LlmAgent 조립

Assembles the CareFlow Symptom Triage Agent using Google ADK's LlmAgent.
Google ADK의 LlmAgent를 사용하여 증상 분류 에이전트를 조립합니다.

Architecture / 아키텍처:
  - Model: Gemini 2.5 Flash (low latency for real-time triage)
  - Temperature: 0.1 (deterministic output for safety-critical classification)
    안전 분류는 deterministic해야 하므로 temperature를 최소화합니다.
  - Output: JSON (structured output for downstream EHR integration)
  - Tools: 5 FunctionTools (medications, adherence, metrics, ICD-11, escalation)

Safety design / 안전 설계:
  temperature=0.1 — 증상 분류는 창의성이 아니라 일관성이 필요합니다.
  A triage system must be consistent, not creative.
  Forces structured output to prevent parsing errors in the escalation pipeline.
"""

from datetime import datetime

from google.adk.agents import LlmAgent
# Gemini API 제약: google_search는 FunctionTool과 함께 사용 불가
# Gemini API constraint: google_search cannot be combined with FunctionTools
# ("Multiple tools are supported only when they are all search tools")
# from google.adk.tools.google_search_tool import google_search
from google.genai import types

from careflow.mcp import get_gmail_tools
from careflow.agents.symptom_triage.prompt import SYMPTOM_TRIAGE_INSTRUCTION
from careflow.agents.symptom_triage.tools import (
    get_adherence_history,
    get_patient_medications,
    get_recent_health_metrics,
    lookup_icd11_code,
    send_escalation_alert,
)
# 안전 콜백 임포트 — 증상 분류는 안전 최우선 (safety-critical)
# Safety callbacks — symptom triage is safety-critical, must have full protection
from careflow.agents.safety.plugin import (
    before_model_callback,
    after_model_callback,
)

# ──────────────────────────────────────────────────────────────────────
# Symptom Triage Agent 조립 / Agent Assembly
# ──────────────────────────────────────────────────────────────────────
#
# output_key="symptom_triage_result"
#   → 세션 상태(state)에 결과를 저장하여 LoopAgent, CaregiverAgent 등
#     후속 에이전트가 참조할 수 있도록 합니다.
#   → Persists result to session state so downstream agents
#     (LoopAgent, CaregiverAgent, etc.) can access it.
#
# generate_content_config 설정 근거 / Rationale:
#   temperature=0.1
#     안전 분류에서는 동일 입력에 동일 출력이 나와야 합니다.
#     For safety classification, same input must yield same output.
#     높은 temperature는 긴급도 판정의 일관성을 해칩니다.
#     High temperature degrades urgency classification consistency.
#
#     JSON 출력을 강제하여 에스컬레이션 파이프라인의 파싱 안정성을 보장합니다.
#     Enforces JSON output for reliable parsing in the escalation pipeline.
#     Few-shot 예시와 결합하여 출력 스키마 준수율을 높입니다.
#     Combined with few-shot examples, this maximizes output schema compliance.
# ──────────────────────────────────────────────────────────────────────

# ---------------------------------------------------------------------------
# Factory function — ADK single-parent 제약 대응
# Factory function — work around ADK single-parent constraint
#
# symptom_workflow 와 root standalone 양쪽에서 사용하려면 각각 새 인스턴스가
# 필요. suffix로 name 충돌 방지.
# Fresh instances are required when wiring the same agent under multiple
# parents (e.g. symptom_workflow + root standalone). Suffix avoids
# name collisions.
# ---------------------------------------------------------------------------
def build_symptom_triage_agent(suffix: str = "") -> LlmAgent:
    """Symptom Triage Agent 인스턴스 생성 / Build a new Symptom Triage Agent."""
    now = datetime.now()
    instruction = SYMPTOM_TRIAGE_INSTRUCTION.format(
        current_date=now.strftime("%Y-%m-%d"),
        current_weekday=now.strftime("%A"),
    )
    return LlmAgent(
        name=f"symptom_triage_agent{suffix}",
        model="gemini-2.5-flash",
        instruction=instruction,
        tools=[
            get_patient_medications,
            get_adherence_history,
            get_recent_health_metrics,
            lookup_icd11_code,
            send_escalation_alert,
            # MCP: Gmail 연동 — 긴급 알림 발송 (설계도 반영)
            *get_gmail_tools(),
            # google_search,
        ],
        output_key="symptom_triage_result",
        description="Classifies symptom urgency and triggers escalation chain",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.1,  # 안전 분류는 deterministic하게 / Deterministic for safety
        ),
        # 안전 콜백 연결 — 증상 분류는 안전 최우선이므로 반드시 필요
        # Safety callbacks — mandatory for safety-critical symptom triage
        before_model_callback=before_model_callback,
        after_model_callback=after_model_callback,
    )


# Backward-compat default export / 기존 임포트 호환용 기본 인스턴스
symptom_triage_agent = build_symptom_triage_agent()

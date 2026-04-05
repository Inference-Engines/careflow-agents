# ============================================================================
# CareFlow Medical Info Agent - Agent Assembly
# 의료 정보 에이전트 조립 및 콜백 정의
# ============================================================================
# LlmAgent 기반 진료 기록 구조화, 시맨틱 검색(RAG), 건강 지표 추세,
# 사전 방문 요약, 보호자 알림 에이전트.
#
# LlmAgent-based visit record structuring, semantic search (RAG),
# health metric trends, pre-visit summaries, and caregiver notification agent.
# ============================================================================
"""
CareFlow — Medical Info Agent
Google ADK LlmAgent for medical record structuring, semantic search (RAG),
health metric trends, pre-visit summaries, and caregiver notifications.

This is a SUB-AGENT designed to be invoked by the root orchestrator.
Combines: Medical Info Agent + Caregiver Notification Agent capabilities.
"""

from google.adk.agents import LlmAgent
from google.genai import types

from careflow.agents.medical_info_agent.prompt import MEDICAL_INFO_AGENT_INSTRUCTION
from careflow.tools import (
    # Visit & RAG tools
    store_visit_record,
    search_medical_history,
    get_upcoming_appointments,
    get_health_metrics,
    get_health_metrics_by_type,
    save_health_insight,
    # Notification tools
    send_caregiver_notification,
    get_caregiver_info,
)
# 안전 콜백 임포트 — 프롬프트 인젝션 차단, PII 마스킹, 의료 면책조항 삽입
# Safety callbacks — prompt injection blocking, PII masking, medical disclaimer injection
from careflow.safety_plugin import (
    before_model_callback,
    after_model_callback,
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
        instruction=MEDICAL_INFO_AGENT_INSTRUCTION,
        tools=[
            # Visit record tools
            store_visit_record,
            search_medical_history,
            get_upcoming_appointments,
            # Health metric tools
            get_health_metrics,
            get_health_metrics_by_type,
            save_health_insight,
            # Notification tools
            send_caregiver_notification,
            get_caregiver_info,
        ],
        output_key="medical_info_result",
        description=(
            "Structures medical visit records, performs semantic search (RAG) over patient history, "
            "tracks health metric trends over time, compiles pre-visit summaries, and sends "
            "notifications to caregivers. Use this agent for questions about past visits, medical "
            "history, health trends, appointment preparation, and caregiver notifications."
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,  # 낮은 temperature -> 사실 기반 응답 / Low temp -> factual responses
            response_mime_type="application/json",
        ),
        # 안전 콜백 연결 — 입력/출력 양방향 보호
        # Safety callbacks — bidirectional input/output protection
        before_model_callback=before_model_callback,
        after_model_callback=after_model_callback,
    )


# Backward-compat default export — 기존 임포트 호환용 기본 인스턴스
# Default instance kept for backward compatibility with existing imports.
medical_info_agent = build_medical_info_agent()

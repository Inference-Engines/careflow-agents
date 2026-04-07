# ============================================================================
# CareFlow Caregiver Notification Agent - Agent Assembly
# 보호자 알림 에이전트 조립
# ============================================================================
# LlmAgent 기반 보호자 알림 에이전트. 이벤트 타입 분류 후 Twilio(WhatsApp/SMS)와
# Gmail SMTP를 통해 적절한 채널로 알림을 전달. Deeptesha의 원본 FastAPI
# Notification-Agent를 ADK 패턴으로 포팅.
#
# LlmAgent-based caregiver notification agent. Classifies event type and
# dispatches notifications through appropriate channels via Twilio
# (WhatsApp/SMS) and Gmail SMTP. Ports Deeptesha's original FastAPI
# Notification-Agent to the ADK pattern.
# ============================================================================

import logging
from datetime import datetime

from google.adk.agents import LlmAgent
# Gemini API 제약: google_search는 FunctionTool과 함께 사용 불가
# Gemini API constraint: google_search cannot be combined with FunctionTools
# ("Multiple tools are supported only when they are all search tools")
# from google.adk.tools.google_search_tool import google_search
from google.genai import types

from careflow.agents.safety.plugin import (
    before_model_callback as safety_before_model_callback,
    after_model_callback as safety_after_model_callback,
)
from careflow.mcp import get_gmail_tools

from .prompt import CAREGIVER_INSTRUCTION
from .tools import (
    generate_notification_message,
    send_whatsapp_notification,
    send_sms_notification,
    send_email_notification,
    dispatch_notification,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent Factory
# 에이전트 팩토리 -- ADK는 에이전트 인스턴스가 단일 부모만 가질 수 있으므로,
# 여러 워크플로우(post_visit_sequential, symptom_workflow, root standalone)에서
# 재사용하려면 매번 새 인스턴스를 만들어야 함.
#
# ADK requires each agent instance to have a single parent. To reuse the
# caregiver agent across multiple workflows (post_visit_sequential,
# symptom_workflow, root standalone) we instantiate a fresh copy per call.
# ---------------------------------------------------------------------------


def build_caregiver_agent(suffix: str = "") -> LlmAgent:
    """보호자 알림 LlmAgent 인스턴스 생성.

    Build a fresh caregiver notification LlmAgent instance.

    Args:
        suffix: Optional suffix appended to the agent name so multiple
                instances can coexist under different parents without
                ADK's single-parent constraint being violated.

    Returns:
        A newly constructed LlmAgent ready to be wired into a workflow.
    """
    now = datetime.now()
    instruction = CAREGIVER_INSTRUCTION.format(
        current_date=now.strftime("%Y-%m-%d"),
        current_weekday=now.strftime("%A"),
    )
    return LlmAgent(
        name=f"caregiver_agent{suffix}",
        model="gemini-2.5-flash",
        instruction=instruction,
        tools=[
            generate_notification_message,
            send_whatsapp_notification,
            send_sms_notification,
            send_email_notification,
            dispatch_notification,
            # MCP: Gmail 연동 — 보호자 이메일 알림 (설계도 반영)
            *get_gmail_tools(),
        ],
        output_key="caregiver_notification_result",
        description=(
            "Generates and dispatches caregiver notifications for chronic disease "
            "patients. Classifies events (ALERT / VISIT_UPDATE / WEEKLY_DIGEST) and "
            "fans out to the appropriate channels: WhatsApp + SMS + Email for alerts, "
            "WhatsApp + Email for visit updates, Email only for weekly digests."
        ),
        generate_content_config=types.GenerateContentConfig(
            # 메시지 생성에 약간의 다양성을 부여 -- 딱딱한 템플릿 느낌 완화
            # Slight creativity for message generation -- avoids rigid template feel
            temperature=0.3,
        ),
        before_model_callback=safety_before_model_callback,
        after_model_callback=safety_after_model_callback,
    )


# ---------------------------------------------------------------------------
# Default instance
# 기본 인스턴스 -- 직접 임포트해서 사용할 경우를 위한 편의 인스턴스
# Default instance -- convenience export for direct import cases
# ---------------------------------------------------------------------------

caregiver_agent = build_caregiver_agent()

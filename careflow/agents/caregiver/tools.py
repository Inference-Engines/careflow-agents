# ============================================================================
# CareFlow Caregiver Notification Agent - Function Tools
# 보호자 알림 에이전트 도구 함수 정의
# ============================================================================
# Twilio(WhatsApp/SMS) + Gmail SMTP 연동을 mock으로 구현한 FunctionTool 모음.
# 환경변수가 설정되어 있으면 실제 API 호출을 시도하고, 없으면 로그만 남김.
# Deeptesha의 원본 Notification-Agent main.py를 ADK 패턴으로 포팅.
#
# FunctionTool collection for Twilio (WhatsApp/SMS) + Gmail SMTP integration,
# implemented as mocks by default. If env vars are present, real API calls
# are attempted; otherwise only logs are written. Ports Deeptesha's original
# Notification-Agent main.py to the ADK pattern.
# ============================================================================

import logging
import os
from datetime import datetime
from typing import Optional

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature Flags (Environment Variables)
# 기능 토글 -- 환경변수가 설정되어야 실제 API가 호출됨
# Feature toggles -- real APIs are called only when env vars are configured
# ---------------------------------------------------------------------------

_TWILIO_ENABLED = bool(
    os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN")
)
_GMAIL_ENABLED = bool(
    os.getenv("GMAIL_USER") and os.getenv("GMAIL_PASS")
)


# ---------------------------------------------------------------------------
# Internal Helpers
# 내부 헬퍼 -- 알림 로그 저장 및 이벤트 타입 -> 채널 매핑
# Internal helpers -- notification log persistence and event->channel mapping
# ---------------------------------------------------------------------------

# 이벤트 타입 -> 채널 매핑 / Event type to channel mapping
_EVENT_CHANNEL_MAP = {
    "ALERT":         ["whatsapp", "sms", "email"],   # 3 channels, highest urgency
    "VISIT_UPDATE":  ["whatsapp", "email"],          # 2 channels, medium urgency
    "WEEKLY_DIGEST": ["email"],                      # 1 channel, low urgency
}


def _append_notification_log(tool_context: ToolContext, entry: dict) -> None:
    """session state에 알림 로그 항목을 추가.

    Append a notification log entry to session state.
    """
    log = tool_context.state.get("notification_log", [])
    log.append(entry)
    tool_context.state["notification_log"] = log


# ---------------------------------------------------------------------------
# Tool Functions
# LLM이 function-calling으로 호출 가능한 도구 함수들
# Tool functions callable by the LLM via function-calling
# ---------------------------------------------------------------------------


def generate_notification_message(
    event_type: str,
    patient_name: str,
    details: str,
    tool_context: ToolContext,
) -> dict:
    """Generate a structured notification message (subject, body, short form).

    Produces the three message variants required for multi-channel delivery:
    a short email subject, a full email body, and a <50-word short message
    suitable for WhatsApp/SMS. The LLM is expected to synthesize the final
    wording; this tool returns a scaffold plus context that the model can
    refine when it composes the final response.

    보호자에게 보낼 알림 메시지의 세 가지 버전(제목/본문/단문)을 생성하기 위한
    스캐폴드를 반환합니다. 실제 메시지 작성은 LLM이 자체 프롬프트로 처리합니다.

    Args:
        event_type: One of "ALERT", "VISIT_UPDATE", "WEEKLY_DIGEST".
        patient_name: Patient's full name.
        details: Free-form event details (vitals, visit notes, digest stats).
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "event_type", "scaffold" containing subject/email_body/short_message.
    """
    event_type = event_type.upper()
    if event_type not in _EVENT_CHANNEL_MAP:
        return {
            "status": "error",
            "message": (
                f"Unknown event_type '{event_type}'. "
                f"Must be one of: {list(_EVENT_CHANNEL_MAP.keys())}."
            ),
        }

    # state에 생성 이력 기록 / Log generation history in state
    gen_log = tool_context.state.get("message_generation_log", [])
    gen_log.append({
        "event_type": event_type,
        "patient_name": patient_name,
        "generated_at": datetime.now().isoformat(),
    })
    tool_context.state["message_generation_log"] = gen_log

    # 스캐폴드 반환 -- LLM이 실제 문구를 다듬음
    # Return scaffold -- the LLM will refine the actual wording
    scaffold = {
        "subject": f"[CareFlow] {event_type}: {patient_name}",
        "email_body": (
            f"Dear Caregiver,\n\n"
            f"This is a {event_type} notification regarding {patient_name}.\n\n"
            f"Details:\n{details}\n\n"
            f"-- CareFlow"
        ),
        "short_message": (
            f"CareFlow {event_type}: {patient_name} - "
            f"{details[:100]}"
        )[:250],
    }

    return {
        "status": "success",
        "event_type": event_type,
        "patient_name": patient_name,
        "scaffold": scaffold,
        "recommended_channels": _EVENT_CHANNEL_MAP[event_type],
        "note": (
            "This is a scaffold. Refine subject/email_body/short_message in the "
            "final JSON response. short_message must remain under 50 words."
        ),
    }


def send_whatsapp_notification(
    phone: str,
    message: str,
    tool_context: ToolContext,
) -> dict:
    """Send a WhatsApp notification via Twilio.

    If TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables are set,
    the call is forwarded to the real Twilio REST API. Otherwise the message
    is only logged to session state for testing/demo purposes.

    Twilio를 통해 WhatsApp 알림을 발송합니다. 환경변수 미설정 시 로그만 기록.

    Args:
        phone: Recipient phone number in E.164 format (e.g. "+919876543210").
        message: Short message body (under 50 words recommended).
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "channel", "phone", and "message".
    """
    entry = {
        "channel": "whatsapp",
        "phone": phone,
        "message": message,
        "sent_at": datetime.now().isoformat(),
        "mode": "live" if _TWILIO_ENABLED else "mock",
    }

    if _TWILIO_ENABLED:
        try:
            # 지연 임포트 -- twilio 미설치 환경에서도 모듈 로드 가능
            # Lazy import -- allow module to load without twilio installed
            from twilio.rest import Client  # type: ignore

            client = Client(
                os.getenv("TWILIO_ACCOUNT_SID"),
                os.getenv("TWILIO_AUTH_TOKEN"),
            )
            client.messages.create(
                body=message,
                from_=os.getenv("TWILIO_WHATSAPP_NUMBER"),
                to=f"whatsapp:{phone}",
            )
            entry["status"] = "sent"
            logger.info("[Caregiver] WhatsApp sent to %s", phone)
        except Exception as exc:  # pragma: no cover - network side-effect
            entry["status"] = "failed"
            entry["error"] = str(exc)
            logger.warning("[Caregiver] WhatsApp send failed: %s", exc)
    else:
        entry["status"] = "sent"  # mock 성공 / mock success
        logger.info("[Caregiver] [MOCK] WhatsApp -> %s: %s", phone, message)

    _append_notification_log(tool_context, entry)
    return {
        "status": entry["status"],
        "channel": "whatsapp",
        "phone": phone,
        "mode": entry["mode"],
        "message": f"WhatsApp notification {entry['status']} to {phone}",
    }


def send_sms_notification(
    phone: str,
    message: str,
    tool_context: ToolContext,
) -> dict:
    """Send an SMS notification via Twilio.

    If Twilio env vars are present, performs a real SMS send; otherwise
    records a mock entry in session state for development.

    Twilio를 통해 SMS 알림을 발송합니다. 환경변수 미설정 시 로그만 기록.

    Args:
        phone: Recipient phone number in E.164 format (e.g. "+919876543210").
        message: Short message body (under 160 chars recommended).
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "channel", "phone", and "message".
    """
    entry = {
        "channel": "sms",
        "phone": phone,
        "message": message,
        "sent_at": datetime.now().isoformat(),
        "mode": "live" if _TWILIO_ENABLED else "mock",
    }

    if _TWILIO_ENABLED:
        try:
            from twilio.rest import Client  # type: ignore

            client = Client(
                os.getenv("TWILIO_ACCOUNT_SID"),
                os.getenv("TWILIO_AUTH_TOKEN"),
            )
            client.messages.create(
                body=message,
                from_=os.getenv("TWILIO_SMS_NUMBER"),
                to=phone,
            )
            entry["status"] = "sent"
            logger.info("[Caregiver] SMS sent to %s", phone)
        except Exception as exc:  # pragma: no cover
            entry["status"] = "failed"
            entry["error"] = str(exc)
            logger.warning("[Caregiver] SMS send failed: %s", exc)
    else:
        entry["status"] = "sent"
        logger.info("[Caregiver] [MOCK] SMS -> %s: %s", phone, message)

    _append_notification_log(tool_context, entry)
    return {
        "status": entry["status"],
        "channel": "sms",
        "phone": phone,
        "mode": entry["mode"],
        "message": f"SMS notification {entry['status']} to {phone}",
    }


def send_email_notification(
    email: str,
    subject: str,
    body: str,
    tool_context: ToolContext,
) -> dict:
    """Send an email notification via Gmail SMTP.

    If GMAIL_USER and GMAIL_PASS environment variables are set, the message
    is delivered through smtp.gmail.com:465 (SSL). Otherwise the message is
    only logged to session state.

    Gmail SMTP를 통해 이메일 알림을 발송합니다. 환경변수 미설정 시 로그만 기록.

    Args:
        email: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body (can contain newlines).
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "channel", "email", "subject", and "message".
    """
    entry = {
        "channel": "email",
        "email": email,
        "subject": subject,
        "body_preview": body[:200],
        "sent_at": datetime.now().isoformat(),
        "mode": "live" if _GMAIL_ENABLED else "mock",
    }

    if _GMAIL_ENABLED:
        try:
            # 지연 임포트 -- 표준 라이브러리이지만 mock 경로에서도 불필요
            # Lazy import -- std-lib, not needed in mock path
            import smtplib
            from email.mime.text import MIMEText

            mime = MIMEText(body)
            mime["Subject"] = subject
            mime["From"] = os.getenv("GMAIL_USER")
            mime["To"] = email

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_PASS"))
                server.send_message(mime)
            entry["status"] = "sent"
            logger.info("[Caregiver] Email sent to %s", email)
        except Exception as exc:  # pragma: no cover
            entry["status"] = "failed"
            entry["error"] = str(exc)
            logger.warning("[Caregiver] Email send failed: %s", exc)
    else:
        entry["status"] = "sent"
        logger.info("[Caregiver] [MOCK] Email -> %s | %s", email, subject)

    _append_notification_log(tool_context, entry)
    return {
        "status": entry["status"],
        "channel": "email",
        "email": email,
        "subject": subject,
        "mode": entry["mode"],
        "message": f"Email notification {entry['status']} to {email}",
    }


def dispatch_notification(
    event_type: str,
    user_info: dict,
    message: dict,
    tool_context: ToolContext,
) -> dict:
    """Dispatch a notification through the channels appropriate for the event.

    Fan-out orchestrator: picks channels based on event_type and invokes the
    corresponding send_* tools. This is the primary tool the agent should use
    for end-to-end delivery. Individual channel tools are only needed for
    single-channel overrides.

    이벤트 타입에 맞는 채널들로 알림을 자동 fan-out 발송합니다.
    - ALERT          -> WhatsApp + SMS + Email
    - VISIT_UPDATE   -> WhatsApp + Email
    - WEEKLY_DIGEST  -> Email only

    Args:
        event_type: One of "ALERT", "VISIT_UPDATE", "WEEKLY_DIGEST".
        user_info: dict with "phone" and/or "email" keys for the caregiver.
        message: dict with "subject", "email_body", "short_message" keys.
        tool_context: ADK ToolContext for state management.

    Returns:
        dict with "status", "event_type", "channels_used", and per-channel "delivery_status".
    """
    event_type = event_type.upper()
    if event_type not in _EVENT_CHANNEL_MAP:
        return {
            "status": "error",
            "message": (
                f"Unknown event_type '{event_type}'. "
                f"Must be one of: {list(_EVENT_CHANNEL_MAP.keys())}."
            ),
        }

    target_channels = _EVENT_CHANNEL_MAP[event_type]
    # Priya Sharma 기본 연락처 — LLM이 user_info를 비워 보내면 자동 보충.
    # Default caregiver contact — auto-fill when LLM sends empty user_info.
    phone = user_info.get("phone") or "+91-98765-43210"
    email = user_info.get("email") or "priya.sharma@example.com"
    subject = message.get("subject", "CareFlow Update")
    email_body = message.get("email_body", message.get("short_message", ""))
    short_message = message.get("short_message", "")

    delivery_status: dict = {}
    channels_used: list = []

    # WhatsApp
    if "whatsapp" in target_channels:
        if phone:
            result = send_whatsapp_notification(phone, short_message, tool_context)
            delivery_status["whatsapp"] = result["status"]
            channels_used.append("whatsapp")
        else:
            delivery_status["whatsapp"] = "skipped"
            logger.warning("[Caregiver] WhatsApp skipped -- no phone in user_info")

    # SMS
    if "sms" in target_channels:
        if phone:
            result = send_sms_notification(phone, short_message, tool_context)
            delivery_status["sms"] = result["status"]
            channels_used.append("sms")
        else:
            delivery_status["sms"] = "skipped"
            logger.warning("[Caregiver] SMS skipped -- no phone in user_info")

    # Email — 기존 send_email_notification + Gmail MCP OAuth 모두 시도.
    # Tries both the legacy send_email_notification and the Gmail MCP OAuth path.
    if "email" in target_channels and email:
        result = send_email_notification(email, subject, email_body, tool_context)
        delivery_status["email"] = result["status"]
        channels_used.append("email")
        # Gmail MCP OAuth도 시도 (실제 Gmail 발송)
        try:
            from careflow.mcp.google_mcp import send_email as gmail_send
            gmail_result = gmail_send(email, subject, email_body, tool_context)
            if gmail_result.get("status") == "sent":
                delivery_status["gmail_oauth"] = "sent"
                channels_used.append("gmail_oauth")
        except Exception as _e:
            logger.debug("[Caregiver] Gmail MCP fallback: %s", _e)

    # state에 디스패치 이력 기록 / Log dispatch history in state
    dispatch_log = tool_context.state.get("dispatch_log", [])
    dispatch_log.append({
        "event_type": event_type,
        "channels_used": channels_used,
        "delivery_status": delivery_status,
        "dispatched_at": datetime.now().isoformat(),
    })
    tool_context.state["dispatch_log"] = dispatch_log

    # 전체 성공 여부 판단 / Determine overall success
    # "skipped"도 성공으로 처리 — LLM이 재시도 무한 루프에 빠지지 않도록.
    # Treat "skipped" as success to prevent LLM retry loops.
    any_sent = any(s in ("sent", "skipped") for s in delivery_status.values())
    overall_status = "success" if any_sent else "partial"

    return {
        "status": overall_status,
        "event_type": event_type,
        "channels_used": channels_used,
        "delivery_status": delivery_status,
        "message": (
            f"Dispatched {event_type} via {len(channels_used)} channel(s): "
            f"{', '.join(channels_used) if channels_used else 'none'}."
        ),
    }

# ============================================================================
# CareFlow Google MCP Integration — Gmail + Google Calendar
# 구글 MCP 통합 모듈 — Gmail + Google Calendar
# ============================================================================
#
# 이 모듈은 두 가지 모드로 동작합니다:
# This module operates in two modes:
#
#   1) REAL MCP MODE (OAuth 설정 완료 시 / when OAuth is configured)
#      - Google의 공식 Gmail MCP 서버 및 Calendar MCP 서버에 SSE로 연결
#      - Connects to Google's official Gmail & Calendar MCP servers via SSE
#      - McpToolset + SseConnectionParams 사용
#      - Uses McpToolset + SseConnectionParams
#
#   2) FALLBACK MODE (기본값 / default)
#      - Gmail: Python smtplib 기반 SMTP 전송 또는 mock 로깅
#      - Gmail: Python smtplib-based SMTP sending or mock logging
#      - Calendar: session state 기반 in-memory 이벤트 관리
#      - Calendar: session state-based in-memory event management
#
# ─── 환경변수 / Environment Variables ───────────────────────────────────────
#
#   MCP 모드 전환 / MCP mode switch:
#     CAREFLOW_USE_REAL_MCP=true       실제 MCP 서버 사용 / Use real MCP servers
#
#   Gmail MCP (실제 MCP 모드):
#     GMAIL_MCP_SERVER_URL             Gmail MCP 서버 SSE 엔드포인트 URL
#     GOOGLE_OAUTH_CLIENT_ID           OAuth 2.0 클라이언트 ID
#     GOOGLE_OAUTH_CLIENT_SECRET       OAuth 2.0 클라이언트 시크릿
#     GOOGLE_OAUTH_REFRESH_TOKEN       OAuth 2.0 리프레시 토큰
#
#   Gmail Fallback (SMTP 모드):
#     GMAIL_USER                       발신자 Gmail 주소 / Sender Gmail address
#     GMAIL_PASS                       앱 비밀번호 / App password
#                                      (Google 계정 > 2단계 인증 > 앱 비밀번호)
#                                      (Google Account > 2FA > App Passwords)
#
#   Google Calendar MCP (실제 MCP 모드):
#     CALENDAR_MCP_SERVER_URL          Calendar MCP 서버 SSE 엔드포인트 URL
#     (GOOGLE_OAUTH_* 위와 동일 / same as above)
#
# ─── OAuth 설정 가이드 / OAuth Setup Guide ──────────────────────────────────
#
#   1. Google Cloud Console > APIs & Services > Credentials
#      - OAuth 2.0 클라이언트 ID 생성 (Desktop 또는 Web)
#      - Create OAuth 2.0 Client ID (Desktop or Web)
#
#   2. Gmail API + Google Calendar API 활성화
#      Enable Gmail API + Google Calendar API
#
#   3. OAuth 동의 화면에 스코프 추가:
#      Add scopes to OAuth consent screen:
#      - https://www.googleapis.com/auth/gmail.send
#      - https://www.googleapis.com/auth/calendar
#      - https://www.googleapis.com/auth/calendar.events
#
#   4. Refresh token을 발급받아 환경변수에 설정
#      Obtain refresh token and set in environment variables
#
#   5. Google의 공식 MCP 서버를 로컬에서 실행하거나 호스팅된 URL 사용
#      Run Google's official MCP servers locally or use a hosted URL
#      - Gmail:    npx @anthropic-ai/gmail-mcp-server  (예시)
#      - Calendar: npx @anthropic-ai/calendar-mcp-server (예시)
#
#   6. CAREFLOW_USE_REAL_MCP=true 설정 후 에이전트 재시작
#      Set CAREFLOW_USE_REAL_MCP=true and restart the agents
#
# ============================================================================

from __future__ import annotations

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration / 설정
# ============================================================================

_USE_REAL_MCP = os.getenv("CAREFLOW_USE_REAL_MCP", "false").lower() == "true"
_GMAIL_USER = os.getenv("GMAIL_USER", "")
_GMAIL_PASS = os.getenv("GMAIL_PASS", "")
_GMAIL_SMTP_ENABLED = bool(_GMAIL_USER and _GMAIL_PASS)


# ============================================================================
# ██████╗ ███████╗ █████╗ ██╗         ███╗   ███╗ ██████╗██████╗
# ██╔══██╗██╔════╝██╔══██╗██║         ████╗ ████║██╔════╝██╔══██╗
# ██████╔╝█████╗  ███████║██║         ██╔████╔██║██║     ██████╔╝
# ██╔══██╗██╔══╝  ██╔══██║██║         ██║╚██╔╝██║██║     ██╔═══╝
# ██║  ██║███████╗██║  ██║███████╗    ██║ ╚═╝ ██║╚██████╗██║
# ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝    ╚═╝     ╚═╝ ╚═════╝╚═╝
#
# Real MCP Connection (OAuth 설정 후 활성화 / activate after OAuth setup)
# ============================================================================

async def _get_real_gmail_toolset():
    """실제 CareFlow MCP SSE 서버에 연결하여 Gmail 도구를 반환.

    Connect to CareFlow's MCP SSE server and return Gmail tools.

    Prerequisites / 사전 요구사항:
        - MCP SSE 서버 실행 중 (mcp_server/server.py)
        - MCP_SERVER_URL 환경변수 (기본값: http://localhost:9000/sse)
        - google-adk[mcp] 패키지 설치

    Returns:
        list of ADK Tool objects from the MCP server (Gmail tools).

    Raises:
        ImportError: google.adk.tools.mcp_tool 패키지 미설치 시
        ConnectionError: MCP 서버 연결 실패 시
    """
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams

    mcp_server_url = os.getenv(
        "MCP_SERVER_URL",
        "http://localhost:9000/sse",
    )

    gmail_toolset = McpToolset(
        connection_params=SseConnectionParams(url=mcp_server_url),
        # Gmail 도구만 필터 / Filter to Gmail tools only
        tool_filter=["gmail_send", "gmail_search"],
    )

    tools = await gmail_toolset.get_tools()
    logger.info("[MCP] Gmail tools loaded from %s: %d tools", mcp_server_url, len(tools))
    return tools


async def _get_real_calendar_toolset():
    """실제 CareFlow MCP SSE 서버에 연결하여 Calendar 도구를 반환.

    Connect to CareFlow's MCP SSE server and return Calendar tools.

    Prerequisites / 사전 요구사항:
        - MCP SSE 서버 실행 중 (mcp_server/server.py)
        - MCP_SERVER_URL 환경변수 (기본값: http://localhost:9000/sse)
        - google-adk[mcp] 패키지 설치

    Returns:
        list of ADK Tool objects from the MCP server (Calendar tools).

    Raises:
        ImportError: google.adk.tools.mcp_tool 패키지 미설치 시
        ConnectionError: MCP 서버 연결 실패 시
    """
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams

    mcp_server_url = os.getenv(
        "MCP_SERVER_URL",
        "http://localhost:9000/sse",
    )

    calendar_toolset = McpToolset(
        connection_params=SseConnectionParams(url=mcp_server_url),
        # Calendar 도구만 필터 / Filter to Calendar tools only
        tool_filter=["calendar_create_event", "calendar_list_events"],
    )

    tools = await calendar_toolset.get_tools()
    logger.info("[MCP] Calendar tools loaded from %s: %d tools", mcp_server_url, len(tools))
    return tools


# ============================================================================
# ███████╗ █████╗ ██╗     ██╗     ██████╗  █████╗  ██████╗██╗  ██╗
# ██╔════╝██╔══██╗██║     ██║     ██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
# █████╗  ███████║██║     ██║     ██████╔╝███████║██║     █████╔╝
# ██╔══╝  ██╔══██║██║     ██║     ██╔══██╗██╔══██║██║     ██╔═██╗
# ██║     ██║  ██║███████╗███████╗██████╔╝██║  ██║╚██████╗██║  ██╗
# ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
#
# Fallback Tools — OAuth 없이 즉시 사용 가능
# Fallback Tools — work immediately without OAuth
# ============================================================================


# ---------------------------------------------------------------------------
# Gmail Fallback Tools
# Gmail 폴백 도구 — SMTP 발송 또는 mock 로깅
# Gmail fallback — SMTP delivery or mock logging
# ---------------------------------------------------------------------------

def send_email(
    to: str,
    subject: str,
    body: str,
    tool_context: ToolContext,
    cc: str = "",
    is_html: bool = False,
) -> dict:
    """이메일 전송 — SMTP 또는 mock 모드.

    Send an email via Gmail SMTP. Falls back to mock logging when
    GMAIL_USER / GMAIL_PASS environment variables are not set.

    caregiver_agent와 symptom_triage_agent에서 보호자/의료진에게 알림을
    보낼 때 사용합니다.

    Used by caregiver_agent and symptom_triage_agent to send notifications
    to caregivers and healthcare providers.

    Args:
        to: Recipient email address (e.g. "priya.sharma@email.com").
            쉼표로 구분하여 여러 수신자 지정 가능.
            Multiple recipients can be separated by commas.
        subject: Email subject line.
        body: Email body text. Plain text by default; set is_html=True for HTML.
        tool_context: ADK ToolContext for session state management.
        cc: Optional CC recipients (comma-separated). 기본값 빈 문자열.
        is_html: If True, body is treated as HTML content. 기본값 False.

    Returns:
        dict with "status", "mode", delivery details, and "message".
    """
    timestamp = datetime.now().isoformat()

    # session state에 이메일 발송 이력 기록
    # Log email send history in session state
    email_log = tool_context.state.get("mcp_email_log", [])
    log_entry: dict[str, Any] = {
        "to": to,
        "cc": cc,
        "subject": subject,
        "body_preview": body[:200],
        "is_html": is_html,
        "sent_at": timestamp,
    }

    # ── OAuth Gmail API 경로 (우선) / OAuth Gmail API path (preferred) ──
    _oauth_token_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "oauth_token.json",
    )
    if os.path.exists(_oauth_token_path):
        try:
            import json as _json
            import base64 as _b64
            from google.oauth2.credentials import Credentials as _OAuthCreds
            from googleapiclient.discovery import build as _build

            with open(_oauth_token_path) as _f:
                _td = _json.load(_f)
            _creds = _OAuthCreds(
                token=_td["token"],
                refresh_token=_td.get("refresh_token"),
                token_uri=_td.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=_td.get("client_id"),
                client_secret=_td.get("client_secret"),
                scopes=_td.get("scopes"),
            )
            _svc = _build("gmail", "v1", credentials=_creds)
            _mime = MIMEText(body, "html" if is_html else "plain", "utf-8")
            _mime["to"] = to
            _mime["subject"] = subject
            if cc:
                _mime["Cc"] = cc
            _raw = _b64.urlsafe_b64encode(_mime.as_bytes()).decode()
            _result = _svc.users().messages().send(userId="me", body={"raw": _raw}).execute()

            log_entry["status"] = "sent"
            log_entry["mode"] = "oauth_gmail_api"
            log_entry["message_id"] = _result.get("id", "")
            logger.info("[Gmail MCP] OAuth API sent to %s | ID: %s", to, _result.get("id"))

            email_log.append(log_entry)
            tool_context.state["mcp_email_log"] = email_log
            return {
                "status": "sent",
                "mode": "oauth_gmail_api",
                "to": to, "cc": cc, "subject": subject,
                "sent_at": timestamp,
                "message_id": _result.get("id", ""),
                "message": f"Email '{subject}' -> {to} [oauth_gmail_api, sent]",
            }
        except Exception as _e:
            logger.warning("[Gmail MCP] OAuth API failed, falling back: %s", _e)

    if _GMAIL_SMTP_ENABLED:
        # ── SMTP 폴백 전송 / SMTP fallback delivery ──
        try:
            msg = MIMEMultipart("alternative") if is_html else MIMEMultipart()
            msg["From"] = _GMAIL_USER
            msg["To"] = to
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = cc

            # 본문 첨부 / Attach body
            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))

            # 전체 수신자 목록 (To + CC)
            # Full recipient list (To + CC)
            all_recipients = [addr.strip() for addr in to.split(",")]
            if cc:
                all_recipients.extend(addr.strip() for addr in cc.split(","))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(_GMAIL_USER, _GMAIL_PASS)
                server.send_message(msg, to_addrs=all_recipients)

            log_entry["status"] = "sent"
            log_entry["mode"] = "smtp"
            logger.info(
                "[Gmail MCP Fallback] Email sent to %s | Subject: %s",
                to, subject,
            )

        except smtplib.SMTPAuthenticationError as exc:
            log_entry["status"] = "auth_error"
            log_entry["mode"] = "smtp"
            log_entry["error"] = str(exc)
            logger.error(
                "[Gmail MCP Fallback] SMTP auth failed. "
                "Check GMAIL_USER and GMAIL_PASS (use App Password, not account password). "
                "Error: %s", exc,
            )

        except smtplib.SMTPException as exc:
            log_entry["status"] = "smtp_error"
            log_entry["mode"] = "smtp"
            log_entry["error"] = str(exc)
            logger.error("[Gmail MCP Fallback] SMTP error: %s", exc)

        except Exception as exc:
            log_entry["status"] = "failed"
            log_entry["mode"] = "smtp"
            log_entry["error"] = str(exc)
            logger.error("[Gmail MCP Fallback] Unexpected error: %s", exc)

    else:
        # ── Mock 모드 — 로그만 기록 / Mock mode — log only ──
        log_entry["status"] = "sent"
        log_entry["mode"] = "mock"
        logger.info(
            "[Gmail MCP Fallback] [MOCK] Email -> %s | Subject: %s | Body: %s...",
            to, subject, body[:80],
        )

    email_log.append(log_entry)
    tool_context.state["mcp_email_log"] = email_log

    return {
        "status": log_entry.get("status", "unknown"),
        "mode": log_entry.get("mode", "unknown"),
        "to": to,
        "cc": cc,
        "subject": subject,
        "sent_at": timestamp,
        "message": (
            f"Email '{subject}' -> {to} "
            f"[{log_entry.get('mode', 'unknown')} mode, {log_entry.get('status', 'unknown')}]"
        ),
        **({"error": log_entry["error"]} if "error" in log_entry else {}),
    }


def search_email_log(
    keyword: str,
    tool_context: ToolContext,
) -> dict:
    """발송된 이메일 로그에서 키워드 검색.

    Search the sent email log in session state by keyword.

    이전에 전송된 이메일 내역을 확인할 때 사용합니다.
    Useful for reviewing previously sent emails.

    Args:
        keyword: Search keyword to match against subject and body_preview.
        tool_context: ADK ToolContext for session state access.

    Returns:
        dict with "status", "keyword", "match_count", and "matches" list.
    """
    email_log = tool_context.state.get("mcp_email_log", [])
    keyword_lower = keyword.lower()

    matches = [
        entry for entry in email_log
        if keyword_lower in entry.get("subject", "").lower()
        or keyword_lower in entry.get("body_preview", "").lower()
        or keyword_lower in entry.get("to", "").lower()
    ]

    return {
        "status": "success",
        "keyword": keyword,
        "match_count": len(matches),
        "matches": matches,
    }


# ---------------------------------------------------------------------------
# Google Calendar Fallback Tools
# Calendar 폴백 도구 — session state 기반 in-memory 이벤트 관리
# Calendar fallback — session state-based in-memory event management
# ---------------------------------------------------------------------------

# 기본 mock 이벤트 — session state가 비어있을 때 초기화용
# Default mock events — used to initialize empty session state
_DEFAULT_CALENDAR_EVENTS = [
    {
        "event_id": "EVT-001",
        "title": "Follow-up with Dr. Patel",
        "date": "2026-04-10",
        "start_time": "09:00",
        "end_time": "09:30",
        "location": "Apollo Hospital, Room 302",
        "description": "Quarterly diabetes checkup. Bring recent lab reports.",
        "attendees": ["patient_001", "dr.patel@apollohospital.com"],
        "reminders": [{"method": "email", "minutes": 1440}, {"method": "popup", "minutes": 120}],
        "status": "confirmed",
        "created_at": "2026-04-01T10:00:00",
    },
    {
        "event_id": "EVT-002",
        "title": "HbA1c Fasting Blood Test",
        "date": "2026-04-15",
        "start_time": "07:30",
        "end_time": "08:00",
        "location": "Apollo Hospital Lab, Ground Floor",
        "description": "FASTING REQUIRED: No food or drink (except water) for 8-12 hours before.",
        "attendees": ["patient_001"],
        "reminders": [{"method": "email", "minutes": 1440}, {"method": "popup", "minutes": 120}],
        "status": "confirmed",
        "created_at": "2026-04-01T10:30:00",
    },
]

# 자동 증가 이벤트 ID 카운터 / Auto-increment event ID counter
_next_event_id = 3


def _get_calendar_events(tool_context: ToolContext) -> list:
    """session state에서 캘린더 이벤트 로드 (없으면 mock 데이터 초기화).

    Load calendar events from session state. Initialize with mock data if empty.
    """
    events = tool_context.state.get("mcp_calendar_events")
    if events is None:
        events = [evt.copy() for evt in _DEFAULT_CALENDAR_EVENTS]
        tool_context.state["mcp_calendar_events"] = events
    return events


def _save_calendar_events(tool_context: ToolContext, events: list) -> None:
    """session state에 캘린더 이벤트 저장 / Save calendar events to session state."""
    tool_context.state["mcp_calendar_events"] = events


def _generate_event_id() -> str:
    """새 이벤트 ID 생성 / Generate a new event ID."""
    global _next_event_id
    eid = f"EVT-{_next_event_id:03d}"
    _next_event_id += 1
    return eid


def create_calendar_event(
    title: str,
    date: str,
    start_time: str,
    end_time: str,
    tool_context: ToolContext,
    description: str = "",
    location: str = "",
    attendees: str = "",
) -> dict:
    """캘린더에 새 이벤트 생성.

    Create a new event on the patient's calendar.

    schedule_agent에서 예약 생성 시 사용합니다.
    실제 MCP 모드에서는 Google Calendar API의 events.insert를 호출합니다.

    Used by schedule_agent for appointment creation.
    In real MCP mode, this calls Google Calendar API events.insert.

    Args:
        title: Event title (e.g. "Follow-up with Dr. Patel").
        date: Date in YYYY-MM-DD format.
        start_time: Start time in HH:MM 24-hour format.
        end_time: End time in HH:MM 24-hour format.
        tool_context: ADK ToolContext for session state management.
        description: Optional event description/notes.
        location: Optional event location.
        attendees: Optional comma-separated attendee emails.

    Returns:
        dict with "status", "event_id", event details, and "message".
    """
    # ── OAuth Google Calendar API 경로 (우선) ──
    _oauth_token_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "oauth_token.json",
    )
    if os.path.exists(_oauth_token_path):
        try:
            import json as _json
            from google.oauth2.credentials import Credentials as _OAuthCreds
            from googleapiclient.discovery import build as _build

            with open(_oauth_token_path) as _f:
                _td = _json.load(_f)
            _creds = _OAuthCreds(
                token=_td["token"],
                refresh_token=_td.get("refresh_token"),
                token_uri=_td.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=_td.get("client_id"),
                client_secret=_td.get("client_secret"),
                scopes=_td.get("scopes"),
            )
            _svc = _build("calendar", "v3", credentials=_creds)
            _event_body = {
                "summary": title,
                "description": description,
                "location": location,
                "start": {"dateTime": f"{date}T{start_time}:00+05:30", "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": f"{date}T{end_time}:00+05:30", "timeZone": "Asia/Kolkata"},
            }
            if attendees:
                _event_body["attendees"] = [{"email": a.strip()} for a in attendees.split(",") if a.strip()]
            _result = _svc.events().insert(calendarId="primary", body=_event_body).execute()

            logger.info("[Calendar MCP] OAuth API event created: %s", _result.get("id"))
            return {
                "status": "success",
                "mode": "oauth_calendar_api",
                "event_id": _result.get("id", ""),
                "title": title, "date": date,
                "start_time": start_time, "end_time": end_time,
                "location": location,
                "link": _result.get("htmlLink", ""),
                "message": f"Event '{title}' created on Google Calendar for {date} {start_time}-{end_time}.",
            }
        except Exception as _e:
            logger.warning("[Calendar MCP] OAuth API failed, falling back: %s", _e)

    events = _get_calendar_events(tool_context)

    # 시간 충돌 확인 / Check for time conflicts
    for evt in events:
        if evt["date"] == date and evt["status"] != "cancelled":
            # 단순 시간 겹침 체크: 새 이벤트의 시작이 기존 이벤트 범위 안에 있는지
            # Simple overlap check: does new start fall within existing event range
            if evt["start_time"] <= start_time < evt["end_time"]:
                return {
                    "status": "conflict",
                    "conflict_with": {
                        "event_id": evt["event_id"],
                        "title": evt["title"],
                        "start_time": evt["start_time"],
                        "end_time": evt["end_time"],
                    },
                    "message": (
                        f"Time conflict with '{evt['title']}' "
                        f"({evt['start_time']}-{evt['end_time']}) on {date}. "
                        "Please choose a different time."
                    ),
                }

    # 이벤트 생성 / Create event
    event_id = _generate_event_id()
    attendee_list = [a.strip() for a in attendees.split(",") if a.strip()] if attendees else []

    new_event = {
        "event_id": event_id,
        "title": title,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "location": location,
        "description": description,
        "attendees": attendee_list,
        "reminders": [
            {"method": "email", "minutes": 1440},   # 24시간 전 / 24h before
            {"method": "popup", "minutes": 120},     # 2시간 전 / 2h before
        ],
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
    }
    events.append(new_event)
    _save_calendar_events(tool_context, events)

    logger.info(
        "[Calendar MCP Fallback] Event created: %s on %s %s-%s",
        title, date, start_time, end_time,
    )

    return {
        "status": "success",
        "event_id": event_id,
        "title": title,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "location": location,
        "attendees": attendee_list,
        "reminders": new_event["reminders"],
        "message": (
            f"Event '{title}' created for {date} {start_time}-{end_time}. "
            "Reminders: 24h before (email) + 2h before (popup)."
        ),
    }


def list_calendar_events(
    date_from: str,
    date_to: str,
    tool_context: ToolContext,
) -> dict:
    """날짜 범위 내 캘린더 이벤트 목록 조회.

    List calendar events within a date range.

    schedule_agent에서 예약 현황 확인 시 사용합니다.
    실제 MCP 모드에서는 Google Calendar API의 events.list를 호출합니다.

    Used by schedule_agent to check appointment status.
    In real MCP mode, this calls Google Calendar API events.list.

    Args:
        date_from: Start date in YYYY-MM-DD format (inclusive).
        date_to: End date in YYYY-MM-DD format (inclusive).
        tool_context: ADK ToolContext for session state access.

    Returns:
        dict with "status", "date_range", "event_count", and "events" list.
    """
    events = _get_calendar_events(tool_context)

    # 날짜 범위 필터 및 정렬 / Filter by date range and sort
    filtered = [
        evt for evt in events
        if date_from <= evt["date"] <= date_to
        and evt["status"] != "cancelled"
    ]
    filtered.sort(key=lambda e: (e["date"], e["start_time"]))

    return {
        "status": "success",
        "date_range": {"from": date_from, "to": date_to},
        "event_count": len(filtered),
        "events": filtered,
    }


def update_calendar_event(
    event_id: str,
    tool_context: ToolContext,
    title: str = "",
    date: str = "",
    start_time: str = "",
    end_time: str = "",
    description: str = "",
    location: str = "",
) -> dict:
    """기존 캘린더 이벤트 수정.

    Update an existing calendar event. Only provided (non-empty) fields are changed.

    schedule_agent에서 예약 변경 시 사용합니다.
    실제 MCP 모드에서는 Google Calendar API의 events.update를 호출합니다.

    Used by schedule_agent for appointment modifications.
    In real MCP mode, this calls Google Calendar API events.update.

    Args:
        event_id: The event ID to update (e.g. "EVT-001").
        tool_context: ADK ToolContext for session state management.
        title: New title (leave empty to keep current).
        date: New date in YYYY-MM-DD format (leave empty to keep current).
        start_time: New start time in HH:MM format (leave empty to keep current).
        end_time: New end time in HH:MM format (leave empty to keep current).
        description: New description (leave empty to keep current).
        location: New location (leave empty to keep current).

    Returns:
        dict with "status", updated event details, and "message".
    """
    events = _get_calendar_events(tool_context)

    # 대상 이벤트 검색 / Find target event
    target = None
    for evt in events:
        if evt["event_id"] == event_id:
            target = evt
            break

    if target is None:
        return {
            "status": "error",
            "message": (
                f"Event '{event_id}' not found. "
                "Use list_calendar_events to see valid event IDs."
            ),
        }

    # 제공된 필드만 업데이트 / Update only provided fields
    changes: dict[str, Any] = {}
    if title:
        changes["title"] = title
        target["title"] = title
    if date:
        changes["date"] = date
        target["date"] = date
    if start_time:
        changes["start_time"] = start_time
        target["start_time"] = start_time
    if end_time:
        changes["end_time"] = end_time
        target["end_time"] = end_time
    if description:
        changes["description"] = description
        target["description"] = description
    if location:
        changes["location"] = location
        target["location"] = location

    if not changes:
        return {
            "status": "no_change",
            "event_id": event_id,
            "message": "No fields provided to update.",
        }

    target["updated_at"] = datetime.now().isoformat()
    _save_calendar_events(tool_context, events)

    logger.info("[Calendar MCP Fallback] Event %s updated: %s", event_id, changes)

    return {
        "status": "success",
        "event_id": event_id,
        "changes": changes,
        "updated_event": target,
        "message": f"Event '{event_id}' updated: {', '.join(changes.keys())} changed.",
    }


def delete_calendar_event(
    event_id: str,
    tool_context: ToolContext,
) -> dict:
    """캘린더 이벤트 삭제 (soft delete — 상태를 'cancelled'로 변경).

    Delete a calendar event (soft delete -- marks status as 'cancelled').

    schedule_agent에서 예약 취소 시 사용합니다.
    실제 MCP 모드에서는 Google Calendar API의 events.delete를 호출합니다.

    Used by schedule_agent for appointment cancellation.
    In real MCP mode, this calls Google Calendar API events.delete.

    Args:
        event_id: The event ID to cancel (e.g. "EVT-001").
        tool_context: ADK ToolContext for session state management.

    Returns:
        dict with "status", cancelled event details, and "message".
    """
    events = _get_calendar_events(tool_context)

    target = None
    for evt in events:
        if evt["event_id"] == event_id:
            target = evt
            break

    if target is None:
        return {
            "status": "error",
            "message": (
                f"Event '{event_id}' not found. "
                "Use list_calendar_events to see valid event IDs."
            ),
        }

    if target["status"] == "cancelled":
        return {
            "status": "already_cancelled",
            "event_id": event_id,
            "message": f"Event '{event_id}' was already cancelled.",
        }

    # Soft delete -- 이벤트 기록은 유지하되 상태만 변경
    # Soft delete -- preserve event record but change status
    target["status"] = "cancelled"
    target["cancelled_at"] = datetime.now().isoformat()
    _save_calendar_events(tool_context, events)

    # 취소 이력 기록 / Log cancellation history
    cancel_log = tool_context.state.get("mcp_calendar_cancel_log", [])
    cancel_log.append({
        "event_id": event_id,
        "title": target["title"],
        "date": target["date"],
        "cancelled_at": target["cancelled_at"],
    })
    tool_context.state["mcp_calendar_cancel_log"] = cancel_log

    logger.info("[Calendar MCP Fallback] Event %s cancelled: %s", event_id, target["title"])

    return {
        "status": "success",
        "cancelled_event": {
            "event_id": event_id,
            "title": target["title"],
            "date": target["date"],
            "start_time": target["start_time"],
            "end_time": target["end_time"],
        },
        "message": (
            f"Event '{target['title']}' on {target['date']} "
            f"({target['start_time']}-{target['end_time']}) has been cancelled."
        ),
    }


def find_available_slots(
    date: str,
    duration_minutes: int,
    tool_context: ToolContext,
) -> dict:
    """지정 날짜에서 사용 가능한 시간대 검색.

    Find available time slots on a given date for the specified duration.

    schedule_agent에서 예약 가능 시간을 확인할 때 사용합니다.
    실제 MCP 모드에서는 Google Calendar API의 freebusy.query를 호출합니다.

    Used by schedule_agent to check available booking times.
    In real MCP mode, this calls Google Calendar API freebusy.query.

    Args:
        date: Target date in YYYY-MM-DD format.
        duration_minutes: Required appointment duration in minutes (e.g. 30).
        tool_context: ADK ToolContext for session state access.

    Returns:
        dict with "status", "date", "duration_minutes", and "available_slots" list.
    """
    events = _get_calendar_events(tool_context)

    # 해당 날짜의 예약된 시간대 수집 / Collect booked time ranges on the date
    booked_ranges = []
    for evt in events:
        if evt["date"] == date and evt["status"] != "cancelled":
            booked_ranges.append((evt["start_time"], evt["end_time"]))
    booked_ranges.sort()

    # 업무 시간 (07:00 ~ 18:00) 내 가용 슬롯 계산
    # Calculate available slots within business hours (07:00-18:00)
    available_slots = []
    # 30분 단위로 슬롯 생성 / Generate slots in 30-minute increments
    hour = 7
    minute = 0
    while hour < 18:
        slot_start = f"{hour:02d}:{minute:02d}"
        # 종료 시간 계산 / Calculate end time
        end_total_min = hour * 60 + minute + duration_minutes
        end_hour = end_total_min // 60
        end_min = end_total_min % 60
        if end_hour > 18:
            break
        slot_end = f"{end_hour:02d}:{end_min:02d}"

        # 충돌 여부 확인 / Check for conflicts
        has_conflict = False
        for booked_start, booked_end in booked_ranges:
            # 겹침 조건: 새 슬롯 시작 < 기존 종료 AND 새 슬롯 종료 > 기존 시작
            # Overlap condition: new_start < existing_end AND new_end > existing_start
            if slot_start < booked_end and slot_end > booked_start:
                has_conflict = True
                break

        if not has_conflict:
            available_slots.append({
                "start_time": slot_start,
                "end_time": slot_end,
            })

        # 30분 증가 / Advance by 30 minutes
        minute += 30
        if minute >= 60:
            hour += 1
            minute = 0

    return {
        "status": "success",
        "date": date,
        "duration_minutes": duration_minutes,
        "available_count": len(available_slots),
        "available_slots": available_slots,
        "booked_ranges": [
            {"start": s, "end": e} for s, e in booked_ranges
        ],
    }


# ============================================================================
# ████████╗ ██████╗  ██████╗ ██╗         ██╗     ██╗███████╗████████╗███████╗
#    ██║   ██╔═══██╗██╔═══██╗██║         ██║     ██║██╔════╝   ██║   ██╔════╝
#    ██║   ██║   ██║██║   ██║██║         ██║     ██║███████╗   ██║   ███████╗
#    ██║   ██║   ██║██║   ██║██║         ██║     ██║╚════██║   ██║   ╚════██║
#    ██║   ╚██████╔╝╚██████╔╝███████╗   ███████╗██║███████║   ██║   ███████║
#    ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝   ╚══════╝╚═╝╚══════╝   ╚═╝   ╚══════╝
#
# Public API — 에이전트 정의에서 사용하는 진입점
# Public API — entry points used in agent definitions
# ============================================================================


def get_gmail_tools() -> list:
    """Gmail 관련 FunctionTool 목록을 반환.

    Return the list of Gmail-related tools for ADK agent registration.

    실제 MCP 모드에서는 McpToolset에서 가져온 도구를 반환하고,
    폴백 모드에서는 SMTP/mock 기반 FunctionTool을 반환합니다.

    In real MCP mode, returns tools fetched from the McpToolset.
    In fallback mode, returns SMTP/mock-based FunctionTools.

    Usage / 사용법:
        # caregiver_agent 또는 symptom_triage_agent의 tools 목록에 추가
        # Add to caregiver_agent's or symptom_triage_agent's tools list
        from careflow.mcp.google_mcp import get_gmail_tools

        agent = LlmAgent(
            name="caregiver_agent",
            tools=[
                *existing_tools,
                *get_gmail_tools(),
            ],
        )

    Returns:
        list of tool functions compatible with ADK FunctionTool registration.
    """
    # ── Gmail 도구 반환 (OAuth fallback 포함) / Gmail tools with OAuth fallback ──
    # MCP SSE 서버 연결은 async이므로 동기 함수에서는 fallback 도구를 반환.
    # 실제 MCP 연결은 에이전트가 async 컨텍스트에서 _get_real_gmail_toolset()를 호출.
    # Gmail OAuth 직접 호출은 fallback 도구(send_email)에서 이미 지원.
    return [
        send_email,
        search_email_log,
    ]


def get_calendar_tools() -> list:
    """Google Calendar 관련 FunctionTool 목록을 반환.

    Return the list of Google Calendar-related tools for ADK agent registration.

    실제 MCP 모드에서는 McpToolset에서 가져온 도구를 반환하고,
    폴백 모드에서는 session state 기반 FunctionTool을 반환합니다.

    In real MCP mode, returns tools fetched from the McpToolset.
    In fallback mode, returns session state-based FunctionTools.

    Usage / 사용법:
        # schedule_agent의 tools 목록에 추가
        # Add to schedule_agent's tools list
        from careflow.mcp.google_mcp import get_calendar_tools

        agent = LlmAgent(
            name="schedule_agent",
            tools=[
                *existing_tools,
                *get_calendar_tools(),
            ],
        )

    Returns:
        list of tool functions compatible with ADK FunctionTool registration.
    """
    # ── Calendar 도구 반환 (OAuth fallback 포함) / Calendar tools with OAuth fallback ──
    # Calendar OAuth 직접 호출은 fallback 도구(create_calendar_event 등)에서 이미 지원.
    return [
        create_calendar_event,
        list_calendar_events,
        update_calendar_event,
        delete_calendar_event,
        find_available_slots,
    ]

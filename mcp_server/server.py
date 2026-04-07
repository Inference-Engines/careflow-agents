# ============================================================================
# CareFlow MCP SSE Server — Gmail + Google Calendar
# MCP SSE 서버 — Gmail API v1 + Calendar API v3 도구 제공
# ============================================================================
#
# Model Context Protocol (MCP) 서버. SSE 전송을 통해 4개의 Google API 도구를
# ADK 에이전트(caregiver_agent, schedule_agent)에 노출한다.
#
# MCP (Model Context Protocol) server that exposes 4 Google API tools over
# SSE transport. ADK agents connect via McpToolset + SseConnectionParams.
#
# 도구 목록 / Tools:
#   gmail_send             — Gmail API v1: 보호자 알림 발송
#   gmail_search           — Gmail API v1: 이전 알림/회신 검색
#   calendar_create_event  — Calendar API v3: 진료 예약 생성
#   calendar_list_events   — Calendar API v3: 예정 일정 조회
#
# 인증: OAuth 2.0 (offline access) — 토큰 만료 시 자동 갱신 후 디스크에 저장.
# Auth: OAuth 2.0 (offline) — auto-refreshes expired tokens and persists them.
#
# Usage:
#   python server.py                          # default port 9000
#   PORT=8080 python server.py                # Cloud Run
#   OAUTH_TOKEN_PATH=/path/to/token.json python server.py
#
# ============================================================================

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import uvicorn

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("careflow-mcp")

# ── Configuration ────────────────────────────────────────────────────────────

PORT = int(os.getenv("PORT", "9000"))
OAUTH_TOKEN_PATH = os.getenv(
    "OAUTH_TOKEN_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "oauth_token.json"),
)

# ── OAuth 자격증명 관리 / Credential Management ─────────────────────────────
# OAuth 2.0 offline access 토큰을 로드하고, 만료 시 자동 갱신.
# Cloud Run 배포 시에도 동일한 토큰 파일을 Secret Manager로 마운트하여 사용.
# Loads OAuth 2.0 offline token; auto-refreshes on expiry.
# In Cloud Run, the same token file is mounted via Secret Manager.


def _load_credentials() -> Credentials:
    """OAuth 자격증명 로드 + 자동 갱신 / Load OAuth creds with auto-refresh.

    만료된 토큰을 감지하면 refresh_token으로 갱신 후 디스크에 재저장하여,
    서버 재시작 없이도 장기 운영이 가능하다.
    Detects expired tokens, refreshes via refresh_token, and persists to disk
    so the server can run long-term without manual re-authentication.
    """
    if not os.path.exists(OAUTH_TOKEN_PATH):
        raise FileNotFoundError(
            f"OAuth token file not found: {OAUTH_TOKEN_PATH}. "
            "Run oauth_setup.py first."
        )

    with open(OAUTH_TOKEN_PATH) as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data.get("token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )

    # Auto-refresh if expired
    if creds.expired or not creds.valid:
        logger.info("OAuth token expired, refreshing...")
        creds.refresh(GoogleAuthRequest())
        # Persist refreshed token
        token_data["token"] = creds.token
        with open(OAUTH_TOKEN_PATH, "w") as f:
            json.dump(token_data, f, indent=2)
        logger.info("OAuth token refreshed and saved.")

    return creds


def _get_gmail_service():
    """Gmail API v1 서비스 빌드 / Build Gmail API v1 service."""
    return build("gmail", "v1", credentials=_load_credentials())


def _get_calendar_service():
    """Calendar API v3 서비스 빌드 / Build Calendar API v3 service."""
    return build("calendar", "v3", credentials=_load_credentials())


# ============================================================================
# MCP Server Definition
# ============================================================================

mcp_server = Server("careflow-google-mcp")


# ── Tool Listing ─────────────────────────────────────────────────────────────


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """MCP 도구 목록 반환 / Return list of available MCP tools."""
    return [
        Tool(
            name="gmail_send",
            description=(
                "Send an email via Gmail API. "
                "Gmail API를 통해 이메일을 전송합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address (comma-separated for multiple)",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line",
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body (plain text or HTML)",
                    },
                    "is_html": {
                        "type": "boolean",
                        "description": "Set true if body is HTML content",
                        "default": False,
                    },
                },
                "required": ["to", "subject", "body"],
            },
        ),
        Tool(
            name="gmail_search",
            description=(
                "Search Gmail inbox using Gmail query syntax. "
                "Gmail 검색 구문으로 받은편지함을 검색합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query (e.g. 'from:doctor subject:appointment')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="calendar_create_event",
            description=(
                "Create a new event on Google Calendar. "
                "Google Calendar에 새 이벤트를 생성합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Event title / summary",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format (e.g. '2026-04-10T09:00:00+05:30')",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in ISO 8601 format (e.g. '2026-04-10T09:30:00+05:30')",
                    },
                    "description": {
                        "type": "string",
                        "description": "Event description / notes",
                        "default": "",
                    },
                    "location": {
                        "type": "string",
                        "description": "Event location",
                        "default": "",
                    },
                    "attendees": {
                        "type": "string",
                        "description": "Comma-separated attendee email addresses",
                        "default": "",
                    },
                },
                "required": ["summary", "start_time", "end_time"],
            },
        ),
        Tool(
            name="calendar_list_events",
            description=(
                "List upcoming events from Google Calendar. "
                "Google Calendar에서 예정된 이벤트 목록을 조회합니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "time_min": {
                        "type": "string",
                        "description": "Start of time range in ISO 8601 (e.g. '2026-04-07T00:00:00Z')",
                    },
                    "time_max": {
                        "type": "string",
                        "description": "End of time range in ISO 8601 (e.g. '2026-04-30T23:59:59Z')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to return",
                        "default": 20,
                    },
                },
                "required": ["time_min", "time_max"],
            },
        ),
    ]


# ── Tool Execution ───────────────────────────────────────────────────────────


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """MCP 도구 실행 / Execute an MCP tool by name."""
    logger.info("Tool call: %s(%s)", name, json.dumps(arguments, ensure_ascii=False)[:200])

    try:
        if name == "gmail_send":
            result = _gmail_send(**arguments)
        elif name == "gmail_search":
            result = _gmail_search(**arguments)
        elif name == "calendar_create_event":
            result = _calendar_create_event(**arguments)
        elif name == "calendar_list_events":
            result = _calendar_list_events(**arguments)
        else:
            result = {"error": f"Unknown tool: {name}"}
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        result = {"error": str(exc)}

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# ============================================================================
# Tool Implementations
# ============================================================================


def _gmail_send(
    to: str,
    subject: str,
    body: str,
    is_html: bool = False,
) -> dict[str, Any]:
    """Gmail API v1 — 이메일 발송 / Send email via Gmail API.

    caregiver_agent가 보호자에게 환자 상태 알림을 보낼 때 호출.
    Called by caregiver_agent to send patient status notifications.
    """
    service = _get_gmail_service()

    mime = MIMEText(body, "html" if is_html else "plain", "utf-8")
    mime["to"] = to
    mime["subject"] = subject

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    result = service.users().messages().send(
        userId="me",
        body={"raw": raw},
    ).execute()

    logger.info("[gmail_send] Sent to %s | ID: %s", to, result.get("id"))

    return {
        "status": "sent",
        "message_id": result.get("id", ""),
        "thread_id": result.get("threadId", ""),
        "to": to,
        "subject": subject,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


def _gmail_search(
    query: str,
    max_results: int = 10,
) -> dict[str, Any]:
    """Gmail API v1 — 받은편지함 검색 / Search Gmail inbox.

    이전 알림 이력이나 의사 회신을 확인할 때 사용.
    Used to check previous notification history or doctor replies.
    """
    service = _get_gmail_service()

    response = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results,
    ).execute()

    messages = response.get("messages", [])
    results = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me",
            id=msg_ref["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        results.append({
            "id": msg["id"],
            "thread_id": msg.get("threadId", ""),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        })

    logger.info("[gmail_search] Query '%s' returned %d results", query, len(results))

    return {
        "status": "success",
        "query": query,
        "result_count": len(results),
        "messages": results,
    }


def _calendar_create_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    location: str = "",
    attendees: str = "",
) -> dict[str, Any]:
    """Calendar API v3 — 이벤트 생성 / Create Google Calendar event.

    schedule_agent가 진료 예약·검사 일정을 캘린더에 등록할 때 호출.
    Called by schedule_agent to book appointments and lab tests.
    """
    service = _get_calendar_service()

    event_body: dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
    }
    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location
    if attendees:
        event_body["attendees"] = [
            {"email": a.strip()} for a in attendees.split(",") if a.strip()
        ]

    result = service.events().insert(
        calendarId="primary",
        body=event_body,
    ).execute()

    logger.info("[calendar_create_event] Created: %s (%s)", summary, result.get("id"))

    return {
        "status": "success",
        "event_id": result.get("id", ""),
        "summary": summary,
        "start": start_time,
        "end": end_time,
        "location": location,
        "html_link": result.get("htmlLink", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _calendar_list_events(
    time_min: str,
    time_max: str,
    max_results: int = 20,
) -> dict[str, Any]:
    """Calendar API v3 — 일정 조회 / List events in a time range.

    STATUS_CHECK 인텐트에서 예정된 진료·검사를 확인할 때 사용.
    Used by STATUS_CHECK intent to show upcoming appointments and tests.
    """
    service = _get_calendar_service()

    response = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = response.get("items", [])
    results = []

    for evt in events:
        start = evt.get("start", {})
        end = evt.get("end", {})
        results.append({
            "id": evt.get("id", ""),
            "summary": evt.get("summary", "(No title)"),
            "start": start.get("dateTime", start.get("date", "")),
            "end": end.get("dateTime", end.get("date", "")),
            "location": evt.get("location", ""),
            "description": evt.get("description", ""),
            "status": evt.get("status", ""),
            "html_link": evt.get("htmlLink", ""),
            "attendees": [
                a.get("email", "") for a in evt.get("attendees", [])
            ],
        })

    logger.info(
        "[calendar_list_events] %s to %s: %d events",
        time_min, time_max, len(results),
    )

    return {
        "status": "success",
        "time_range": {"min": time_min, "max": time_max},
        "event_count": len(results),
        "events": results,
    }


# ── SSE 전송 계층 + Starlette 앱 / SSE Transport + Starlette App ─────────────
# MCP 프로토콜은 SSE(Server-Sent Events)로 ADK와 통신. /sse로 연결 후
# /messages/로 도구 호출을 POST한다.
# MCP protocol communicates with ADK via SSE. Connect on /sse, then POST
# tool calls to /messages/.

sse_transport = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    """SSE connection endpoint — ADK connects here via /sse."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )


async def handle_messages(request: Request):
    """Message POST endpoint — client sends tool calls here."""
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )


async def health(request: Request):
    """Health check endpoint for Cloud Run / load balancers."""
    return JSONResponse({
        "status": "healthy",
        "server": "careflow-google-mcp",
        "tools": ["gmail_send", "gmail_search", "calendar_create_event", "calendar_list_events"],
        "oauth_token_path": OAUTH_TOKEN_PATH,
        "oauth_token_exists": os.path.exists(OAUTH_TOKEN_PATH),
    })


app = Starlette(
    debug=False,
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/sse", handle_sse),
        Mount("/messages", routes=[Route("/", handle_messages, methods=["POST"])]),
    ],
)


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("CareFlow MCP SSE Server starting on port %d", PORT)
    logger.info("OAuth token: %s (exists: %s)", OAUTH_TOKEN_PATH, os.path.exists(OAUTH_TOKEN_PATH))
    logger.info("SSE endpoint: http://localhost:%d/sse", PORT)
    logger.info("Health check: http://localhost:%d/health", PORT)
    logger.info("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=PORT)

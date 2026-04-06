# ============================================================================
# CareFlow MCP Integration Package
# MCP(Model Context Protocol) 통합 패키지
# ============================================================================
# Gmail MCP와 Google Calendar MCP 도구를 CareFlow ADK 에이전트에 제공합니다.
# OAuth 미설정 시 mock/SMTP 폴백으로 자동 전환되어 개발/데모가 가능합니다.
#
# Provides Gmail MCP and Google Calendar MCP toolsets for CareFlow ADK agents.
# Automatically falls back to mock/SMTP implementations when OAuth is not
# configured, enabling development and demo without Google API credentials.
#
# Usage / 사용법:
#   from careflow.mcp.google_mcp import (
#       get_gmail_tools,
#       get_calendar_tools,
#   )
#
#   # Agent 정의 시 tools 목록에 추가
#   # Add to agent's tools list
#   tools = [*get_gmail_tools(), *get_calendar_tools()]
# ============================================================================

from careflow.mcp.google_mcp import (
    get_gmail_tools,
    get_calendar_tools,
)

__all__ = [
    "get_gmail_tools",
    "get_calendar_tools",
]

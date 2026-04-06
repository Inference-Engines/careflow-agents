"""CareFlow shared database helpers.

CareFlow 공용 데이터베이스 헬퍼 모듈.
에이전트 tools.py에서 AlloyDB 연결을 얻기 위한 단일 진입점을 제공합니다.

Two connectivity paths are available:
  1. Direct SQLAlchemy (alloydb_client) — used by hand-written tool functions.
  2. MCP Toolbox (mcp_client) — declarative SQL tools served by the Toolbox server.
"""

from careflow.db.alloydb_client import get_db_engine, query_dict
from careflow.db.mcp_client import get_mcp_toolset, aget_mcp_toolset

__all__ = ["get_db_engine", "query_dict", "get_mcp_toolset", "aget_mcp_toolset"]

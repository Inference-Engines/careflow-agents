"""AlloyDB connection helper with graceful mock fallback.
AlloyDB 연결 헬퍼 — 설정이 없으면 mock 데이터 경로로 우아하게 fallback.

환경변수 ALLOYDB_CONN_URI가 설정되어 있으면 실제 AlloyDB에 연결하고,
없으면 None을 반환하여 tools.py의 mock 데이터 fallback 경로를 타게 한다.

If the environment variable ALLOYDB_CONN_URI is set, we connect to AlloyDB
using SQLAlchemy. Otherwise we return None, which tells each tool function
to fall back to the curated in-memory mock data.

Expected URI format (SQLAlchemy + pg8000):
    postgresql+pg8000://<user>:<password>@<host>:<port>/<database>
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 모듈 수준 캐시 — 엔진은 한 번만 생성한다
# Module-level cache — engine is created once and reused.
_engine: Optional[Any] = None
_initialized: bool = False


def get_db_engine() -> Optional[Any]:
    """Return a SQLAlchemy engine, or None if AlloyDB is not configured.

    SQLAlchemy 엔진을 반환합니다. AlloyDB가 설정되지 않았거나 연결 실패 시 None.
    호출자는 None을 받았을 때 mock 데이터로 fallback해야 합니다.

    Returns:
        SQLAlchemy Engine instance on success, None otherwise.
    """
    global _engine, _initialized

    # 재초기화 방지 — 첫 호출 결과를 캐싱
    # Avoid re-initialising — cache the result of the first call.
    if _initialized:
        return _engine
    _initialized = True

    conn_uri = os.getenv("ALLOYDB_CONN_URI")
    if not conn_uri:
        logger.info("alloydb.not_configured — using mock data fallback")
        return None

    try:
        from sqlalchemy import create_engine  # type: ignore

        _engine = create_engine(
            conn_uri,
            pool_pre_ping=True,  # 끊긴 커넥션 자동 감지 / detect stale connections
            pool_size=5,
        )
        logger.info("alloydb.connected")
        return _engine
    except ImportError:
        # SQLAlchemy 또는 pg8000 드라이버 미설치
        # SQLAlchemy or pg8000 driver not installed.
        logger.warning(
            "alloydb.sqlalchemy_missing — run: pip install sqlalchemy pg8000"
        )
        return None
    except Exception as e:  # pragma: no cover — defensive
        logger.error(f"alloydb.connect_failed: {e}")
        return None


def query_dict(sql: str, params: Optional[dict] = None) -> list[dict]:
    """Execute a SQL query and return rows as a list of dicts.

    SQL 쿼리를 실행하여 결과를 dict 리스트로 반환합니다.
    AlloyDB가 설정되지 않았거나 쿼리 실패 시 빈 리스트를 반환합니다 —
    호출자는 빈 리스트를 mock fallback 트리거로 사용할 수 있습니다.

    On any failure (no engine, driver missing, query error) this function
    returns an empty list so that callers can use the empty result as the
    signal to fall back to their curated mock data path.

    Args:
        sql: SQL statement with named parameters (e.g. ``:pid``).
        params: Dict of bind parameters for the statement.

    Returns:
        List of row dicts, or an empty list on any failure.
    """
    engine = get_db_engine()
    if engine is None:
        return []

    try:
        from sqlalchemy import text  # type: ignore

        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return [_serialize_row(row._mapping) for row in result]
    except Exception as e:  # pragma: no cover — defensive
        logger.error(f"alloydb.query_failed: {e}")
        return []


def _serialize_row(mapping) -> dict:
    """AlloyDB 결과를 JSON 직렬화 가능한 dict로 변환.

    UUID, date, datetime, Decimal 등을 str/float로 변환하여
    ADK FunctionTool이 JSON.dumps 할 때 터지지 않도록 한다.
    """
    import uuid as _uuid_mod
    from datetime import date, datetime
    from decimal import Decimal
    row = dict(mapping)
    for k, v in row.items():
        if isinstance(v, _uuid_mod.UUID):
            row[k] = str(v)
        elif isinstance(v, datetime):
            row[k] = v.isoformat()
        elif isinstance(v, date):
            row[k] = v.isoformat()
        elif isinstance(v, Decimal):
            row[k] = float(v)
    return row


def execute_write(sql: str, params: Optional[dict] = None) -> list[dict]:
    """Execute a SQL write statement (INSERT/UPDATE/DELETE) and return rows if any.

    SQL 쓰기 쿼리를 실행합니다. `RETURNING` 절이 있으면 결과를 반환합니다.
    AlloyDB 연결 실패 또는 쿼리 실패 시 빈 리스트를 반환하여 mock fallback을 유도합니다.

    Args:
        sql: SQL write statement with named parameters.
        params: Dict of bind parameters.

    Returns:
        List of row dicts if RETURNING used, or empty list on failure. 
        If no RETURNING, returns a dummy dict `[{"status": "success"}]` on success.
    """
    engine = get_db_engine()
    if engine is None:
        return []

    try:
        from sqlalchemy import text  # type: ignore

        # .begin() automatically commits on exit
        with engine.begin() as conn:
            result = conn.execute(text(sql), params or {})
            if result.returns_rows:
                return [_serialize_row(row._mapping) for row in result]
            return [{"status": "success"}]
    except Exception as e:  # pragma: no cover
        logger.error(f"alloydb.write_failed: {e}")
        return []

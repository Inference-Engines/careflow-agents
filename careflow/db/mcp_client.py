"""MCP Toolbox for Databases — client integration for CareFlow agents.

CareFlow 에이전트가 MCP Toolbox HTTP 서버를 통해 AlloyDB 도구에 접근하기 위한
클라이언트 모듈. google-adk의 ToolboxToolset을 사용하여 Toolbox 서버와 통신한다.

This module provides a thin wrapper around the ADK ToolboxToolset so that any
CareFlow agent can load database tools (defined in tools.yaml) from the MCP
Toolbox HTTP server.

Prerequisites:
    1. MCP Toolbox server running:
         ./tools/toolbox.exe --tools-file tools.yaml
    2. Environment variable (optional — defaults to localhost):
         TOOLBOX_URL=http://127.0.0.1:5000

Usage in an agent module:
    from careflow.db.mcp_client import get_mcp_toolset

    # Load all tools
    toolset = get_mcp_toolset()

    # Load only read tools
    read_toolset = get_mcp_toolset("careflow_read_tools")
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Toolbox server URL — configurable via environment variable.
# 기본값은 로컬 개발 환경(localhost:5000).
# Default points to local dev server.
# ---------------------------------------------------------------------------
_TOOLBOX_URL: str = os.getenv("TOOLBOX_URL", "http://127.0.0.1:5000")

# ---------------------------------------------------------------------------
# Module-level cache — avoid re-creating toolsets for the same name.
# 동일 toolset 이름에 대해 중복 생성을 방지하는 모듈 수준 캐시.
# ---------------------------------------------------------------------------
_toolset_cache: dict[str, object] = {}


def get_mcp_toolset(
    toolset_name: str = "careflow_all_tools",
    *,
    url: Optional[str] = None,
    use_cache: bool = True,
) -> object:
    """Create (or retrieve cached) a ToolboxToolset connected to the MCP Toolbox server.

    MCP Toolbox 서버에 연결된 ToolboxToolset 인스턴스를 생성하거나 캐시에서 반환한다.

    Args:
        toolset_name: Name of the toolset defined in tools.yaml
            (e.g., ``careflow_all_tools``, ``careflow_read_tools``,
            ``careflow_write_tools``).
        url: Override the Toolbox server URL. If ``None``, uses the
            ``TOOLBOX_URL`` environment variable or the default
            ``http://127.0.0.1:5000``.
        use_cache: If ``True`` (default), reuse a previously created
            toolset for the same name. Set to ``False`` to force a
            fresh connection.

    Returns:
        A ``ToolboxToolset`` instance whose tools can be passed to an
        ADK agent's ``tools`` parameter.

    Raises:
        ImportError: If ``google-adk`` with Toolbox support is not installed.
        ConnectionError: If the Toolbox server is unreachable.
    """
    if use_cache and toolset_name in _toolset_cache:
        logger.debug("mcp_client.cache_hit toolset=%s", toolset_name)
        return _toolset_cache[toolset_name]

    effective_url = url or _TOOLBOX_URL
    logger.info(
        "mcp_client.connecting toolset=%s url=%s",
        toolset_name,
        effective_url,
    )

    try:
        from toolbox_core import ToolboxClient  # type: ignore[import-untyped]
    except ImportError as exc:
        logger.error(
            "mcp_client.import_error — "
            "install the MCP Toolbox client: pip install toolbox-core"
        )
        raise ImportError(
            "toolbox-core package is required. "
            "Install it with: pip install toolbox-core"
        ) from exc

    try:
        client = ToolboxClient(effective_url)
        toolset = client.load_toolset(toolset_name)
    except Exception as exc:
        logger.error(
            "mcp_client.connection_failed url=%s error=%s",
            effective_url,
            exc,
        )
        raise ConnectionError(
            f"Failed to connect to MCP Toolbox server at {effective_url}. "
            f"Ensure the server is running: ./tools/toolbox.exe --tools-file tools.yaml"
        ) from exc

    if use_cache:
        _toolset_cache[toolset_name] = toolset

    logger.info(
        "mcp_client.connected toolset=%s tools_count=%d",
        toolset_name,
        len(toolset) if hasattr(toolset, "__len__") else -1,
    )
    return toolset


async def aget_mcp_toolset(
    toolset_name: str = "careflow_all_tools",
    *,
    url: Optional[str] = None,
    use_cache: bool = True,
) -> object:
    """Async version of :func:`get_mcp_toolset`.

    비동기 버전. ADK의 async 에이전트 파이프라인에서 사용할 때 적합하다.

    Uses the async ToolboxClient for non-blocking I/O in async agent
    pipelines.

    Args:
        toolset_name: Name of the toolset defined in tools.yaml.
        url: Override the Toolbox server URL.
        use_cache: Reuse a cached toolset if available.

    Returns:
        A ``ToolboxToolset`` (async-loaded) instance.

    Raises:
        ImportError: If ``toolbox-core`` is not installed.
        ConnectionError: If the Toolbox server is unreachable.
    """
    cache_key = f"async_{toolset_name}"

    if use_cache and cache_key in _toolset_cache:
        logger.debug("mcp_client.async_cache_hit toolset=%s", toolset_name)
        return _toolset_cache[cache_key]

    effective_url = url or _TOOLBOX_URL
    logger.info(
        "mcp_client.async_connecting toolset=%s url=%s",
        toolset_name,
        effective_url,
    )

    try:
        from toolbox_core.async_client import AsyncToolboxClient  # type: ignore[import-untyped]
    except ImportError as exc:
        logger.error(
            "mcp_client.import_error — "
            "install the MCP Toolbox client: pip install toolbox-core"
        )
        raise ImportError(
            "toolbox-core package is required. "
            "Install it with: pip install toolbox-core"
        ) from exc

    try:
        async with AsyncToolboxClient(effective_url) as client:
            toolset = await client.load_toolset(toolset_name)
    except Exception as exc:
        logger.error(
            "mcp_client.async_connection_failed url=%s error=%s",
            effective_url,
            exc,
        )
        raise ConnectionError(
            f"Failed to connect to MCP Toolbox server at {effective_url}. "
            f"Ensure the server is running: ./tools/toolbox.exe --tools-file tools.yaml"
        ) from exc

    if use_cache:
        _toolset_cache[cache_key] = toolset

    logger.info(
        "mcp_client.async_connected toolset=%s",
        toolset_name,
    )
    return toolset


def clear_cache() -> None:
    """Clear the module-level toolset cache.

    모듈 수준 캐시를 비운다. 테스트나 서버 재시작 후 재연결할 때 유용하다.
    Useful for tests or when the Toolbox server is restarted.
    """
    _toolset_cache.clear()
    logger.info("mcp_client.cache_cleared")

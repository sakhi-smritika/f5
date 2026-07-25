"""
Parallel Web Search MCP — Streamable HTTP, free tier (no API key required).

Hosted endpoint: https://search.parallel.ai/mcp
Tools exposed: ``web_search`` (live search) and ``web_fetch`` (URL → markdown).

Optional ``PARALLEL_API_KEY`` env var unlocks higher rate limits (Bearer token).
"""

from __future__ import annotations

import os
from functools import lru_cache

from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

DEFAULT_PARALLEL_MCP_URL = "https://search.parallel.ai/mcp"


@lru_cache
def get_parallel_web_search_toolset() -> McpToolset:
    """Return a cached ``McpToolset`` for Parallel's hosted Search MCP server."""
    url = os.getenv("PARALLEL_MCP_URL", DEFAULT_PARALLEL_MCP_URL).strip()
    headers: dict[str, str] | None = None
    api_key = os.getenv("PARALLEL_API_KEY", "").strip()
    # Parallel API KEY for higher rate limits
    if api_key:
        headers = {"Authorization": f"Bearer {api_key}"}

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=url,
            headers=headers,
        ),
    )

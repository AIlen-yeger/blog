"""网页搜索（搜狗 MCP，配置见 config/mcp_servers.json）。"""

from __future__ import annotations

import logging

from utils.mcp.registry import get_mcp_client, is_mcp_enabled
from utils.log.trace_log import log_event

logger = logging.getLogger(__name__)

SOGOU_MCP_NAME = "sogou"


def sogou_search_sync(query: str, num_results: int = 5) -> str:
    if not is_mcp_enabled(SOGOU_MCP_NAME):
        log_event("mcp.sogou.disabled", level=logging.INFO, query=query[:120])
        return ""

    client = get_mcp_client(SOGOU_MCP_NAME)
    result = client.call_tool_sync(
        {"query": query, "num_results": num_results},
    )
    if not result.ok:
        log_event(
            "mcp.sogou.error",
            level=logging.WARNING,
            query=query[:120],
            error=(result.error or "")[:500],
        )
        return ""

    text = (result.text or "").strip()
    if not text:
        log_event("mcp.sogou.empty", level=logging.WARNING, query=query[:120])
    return text


def search_song_background_story_sync(
    title: str,
    artist: str,
    *,
    num_results: int = 5,
) -> str:
    artist = (artist or "").strip()
    title = (title or "").strip()
    if artist:
        query = f"{artist} {title} 歌曲 创作背景 故事 灵感"
    else:
        query = f"{title} 歌曲 创作背景 故事 灵感"
    return sogou_search_sync(query, num_results=num_results)

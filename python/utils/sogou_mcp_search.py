"""搜狗 MCP 网页搜索（SSE），供听歌报告等场景查歌曲背景。"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client

from utils.trace_log import log_event

logger = logging.getLogger(__name__)

_DEFAULT_SSE_URL = "https://phoenixdna-sogou-search.ms.show/gradio_api/mcp/sse"
SOGOU_TOOL_NAME = os.getenv("SOGOU_MCP_TOOL_NAME", "predict")
_tool_name_cache: str | None = None


def sogou_sse_url() -> str:
    from config.config import AgentConfig

    return AgentConfig().sogou_mcp_sse_url or _DEFAULT_SSE_URL


def text_from_mcp_result(result: Any) -> str:
    parts: list[str] = []
    for block in getattr(result, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    return "\n".join(p for p in parts if p).strip()


async def _resolve_tool_name(session: ClientSession) -> str:
    global _tool_name_cache
    if _tool_name_cache:
        return _tool_name_cache
    configured = (os.getenv("SOGOU_MCP_TOOL_NAME") or "").strip()
    if configured:
        _tool_name_cache = configured
        return configured
    tools = await session.list_tools()
    names = [t.name for t in tools.tools]
    logger.info("[sogou_mcp] available tools: %s", names)
    for candidate in ("predict", "sogou_search"):
        if candidate in names:
            _tool_name_cache = candidate
            return candidate
    if names:
        _tool_name_cache = names[0]
        return names[0]
    raise RuntimeError("搜狗 MCP 未返回任何工具，请检查 SSE 地址是否可访问")


async def sogou_search_async(query: str, num_results: int = 5) -> str:
    from config.config import AgentConfig

    if not AgentConfig().sogou_mcp_enabled:
        log_event("mcp.sogou.disabled", level=logging.INFO, query=query[:120])
        return ""

    try:
        async with sse_client(sogou_sse_url()) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tool_name = await _resolve_tool_name(session)
                result = await session.call_tool(
                    tool_name,
                    arguments={"query": query, "num_results": num_results},
                )
        text = text_from_mcp_result(result)
        if not text:
            log_event("mcp.sogou.empty", level=logging.WARNING, query=query[:120])
            return ""
        return text
    except Exception as exc:
        log_event(
            "mcp.sogou.error",
            level=logging.WARNING,
            query=query[:120],
            error=str(exc)[:500],
        )
        return ""


def sogou_search_sync(query: str, num_results: int = 5) -> str:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(sogou_search_async(query, num_results=num_results))

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(
            asyncio.run, sogou_search_async(query, num_results=num_results)
        ).result()


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

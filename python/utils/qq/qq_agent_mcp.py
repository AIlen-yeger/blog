"""MCP 客户端：连接 qq-agent-mcp（stdio）。"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Awaitable, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


def _params() -> StdioServerParameters:
    from config.config import ensure_env_loaded

    ensure_env_loaded()
    d = (os.getenv("QQ_MCP_DIR") or "").replace("\\", "/")
    bot = (os.getenv("QQ_MCP_BOT_QQ") or "").strip()
    if not d or not bot:
        raise RuntimeError("请配置 QQ_MCP_DIR、QQ_MCP_BOT_QQ")

    friends = (os.getenv("QQ_MCP_FRIENDS") or "").strip()
    args = [
        "run",
        "--directory",
        d,
        "qq-agent-mcp",
        "--qq",
        bot,
        "--napcat-host",
        os.getenv("QQ_MCP_NAPCAT_HOST", "127.0.0.1"),
        "--napcat-port",
        os.getenv("QQ_MCP_NAPCAT_PORT", "3000"),
        "--ws-port",
        os.getenv("QQ_MCP_WS_PORT", "3001"),
    ]
    if friends:
        args.extend(["--friends", friends])

    return StdioServerParameters(command="uv", args=args)


def _text(result: Any) -> str:
    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    return "\n".join(parts).strip()


def _parse_messages(raw: str) -> list[dict]:
    if not raw:
        return []
    data = json.loads(raw)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("messages", "data", "items"):
            val = data.get(key)
            if isinstance(val, list):
                return val
    return []


async def with_session(fn: Callable[[ClientSession], Awaitable[Any]]) -> Any:
    async with stdio_client(_params()) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            return await fn(session)


async def check_status() -> dict:
    async def _run(s: ClientSession) -> dict:
        raw = _text(await s.call_tool("check_status", arguments={}))
        return json.loads(raw or "{}")

    return await with_session(_run)


async def get_recent_private(friend_qq: str, limit: int = 20) -> list[dict]:
    async def _run(s: ClientSession) -> list[dict]:
        raw = _text(
            await s.call_tool(
                "get_recent_context",
                arguments={
                    "target": friend_qq,
                    "target_type": "private",
                    "limit": limit,
                },
            )
        )
        return _parse_messages(raw)

    return await with_session(_run)


async def send_private(friend_qq: str, content: str) -> str:
    async def _run(s: ClientSession) -> str:
        return _text(
            await s.call_tool(
                "send_message",
                arguments={
                    "target": friend_qq,
                    "content": content[:4000],
                    "target_type": "private",
                },
            )
        )

    return await with_session(_run)


class QqMcpSession:
    """长连接 MCP：供 inbox poller 复用，避免频繁 spawn。"""

    def __init__(self) -> None:
        self._ctx: Any = None
        self._session: ClientSession | None = None

    async def open(self) -> None:
        if self._session is not None:
            return
        self._ctx = stdio_client(_params())
        r, w = await self._ctx.__aenter__()
        self._session = ClientSession(r, w)
        await self._session.__aenter__()
        await self._session.initialize()
        logger.info("[qq_mcp] long-lived session ready")

    async def close(self) -> None:
        if self._session is not None:
            await self._session.__aexit__(None, None, None)
            self._session = None
        if self._ctx is not None:
            await self._ctx.__aexit__(None, None, None)
            self._ctx = None

    async def get_recent_private(self, friend_qq: str, limit: int = 20) -> list[dict]:
        if not self._session:
            raise RuntimeError("QqMcpSession 未 open")
        raw = _text(
            await self._session.call_tool(
                "get_recent_context",
                arguments={
                    "target": friend_qq,
                    "target_type": "private",
                    "limit": limit,
                },
            )
        )
        return _parse_messages(raw)

    async def send_private(self, friend_qq: str, content: str) -> str:
        if not self._session:
            raise RuntimeError("QqMcpSession 未 open")
        return _text(
            await self._session.call_tool(
                "send_message",
                arguments={
                    "target": friend_qq,
                    "content": content[:4000],
                    "target_type": "private",
                },
            )
        )

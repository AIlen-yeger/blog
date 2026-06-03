from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters

from utils.mcp.types import McpCallResult, McpClientConfig, McpTransport
from utils.mcp.text_utils import text_from_mcp_result

logger = logging.getLogger(__name__)

_SOGOU_TOOL_CANDIDATES = ("predict", "sogou_search")


class McpClient:
    """通用 MCP Client：stdio / SSE。"""

    def __init__(self, config: McpClientConfig):
        self.config = config
        self._tool_cache: str | None = None

    def _session_context(self):
        if self.config.transport == McpTransport.SSE:
            if not self.config.sse:
                raise RuntimeError(f"[{self.config.name}] 缺少 SSE 配置")
            return sse_client(
                self.config.sse.url,
                headers=self.config.sse.headers or {},
            )

        if not self.config.stdio:
            raise RuntimeError(f"[{self.config.name}] 缺少 stdio 配置")

        params = StdioServerParameters(
            command=self.config.stdio.command,
            args=self.config.stdio.args,
            cwd=self.config.stdio.cwd,
            env=self.config.stdio.env,
        )
        return stdio_client(params)

    async def list_tool_names(self) -> list[str]:
        async with self._session_context() as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [t.name for t in tools.tools]

    async def _resolve_tool(self, session: ClientSession, tool_name: str | None) -> str:
        if tool_name:
            return tool_name
        if self.config.default_tool:
            return self.config.default_tool
        if self._tool_cache:
            return self._tool_cache

        tools = await session.list_tools()
        names = [t.name for t in tools.tools]
        if not names:
            raise RuntimeError(f"[{self.config.name}] MCP 未返回任何 tool")

        if self.config.name == "sogou":
            for candidate in _SOGOU_TOOL_CANDIDATES:
                if candidate in names:
                    self._tool_cache = candidate
                    logger.info("[%s] pick tool: %s (all=%s)", self.config.name, candidate, names)
                    return candidate

        self._tool_cache = names[0]
        logger.info("[%s] auto pick tool: %s (all=%s)", self.config.name, self._tool_cache, names)
        return self._tool_cache

    async def call_tool_async(
        self,
        arguments: dict[str, Any],
        *,
        tool_name: str | None = None,
    ) -> McpCallResult:
        if not self.config.enabled:
            return McpCallResult(ok=False, text="", error="disabled")

        try:
            async with self._session_context() as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    name = await self._resolve_tool(session, tool_name)
                    raw = await session.call_tool(name, arguments=arguments)
            text = text_from_mcp_result(raw)
            return McpCallResult(ok=True, text=text, raw=raw)
        except Exception as exc:
            logger.warning("[%s] call_tool failed: %s", self.config.name, exc)
            return McpCallResult(ok=False, text="", error=str(exc))

    def call_tool_sync(
        self,
        arguments: dict[str, Any],
        *,
        tool_name: str | None = None,
    ) -> McpCallResult:
        coro = self.call_tool_async(arguments, tool_name=tool_name)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

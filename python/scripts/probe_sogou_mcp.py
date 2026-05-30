"""探测搜狗 MCP：列出工具名并试搜一次。用法: python scripts/probe_sogou_mcp.py"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mcp import ClientSession
from mcp.client.sse import sse_client

from utils.sogou_mcp_search import SOGOU_MCP_SSE_URL, sogou_search_async


async def main() -> None:
    print("SSE URL:", SOGOU_MCP_SSE_URL)
    async with sse_client(SOGOU_MCP_SSE_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("\n--- list_tools ---")
            for t in tools.tools:
                print("name:", t.name)
                print("desc:", (t.description or "")[:120])
                print("schema:", json.dumps(t.inputSchema, ensure_ascii=False)[:300])
                print("---")
    print("\n--- call_tool ---")
    try:
        text = await sogou_search_async("HACHI Rainy proof 创作背景", num_results=3)
        print("OK, len=", len(text))
        print(text[:800])
    except Exception as exc:
        print("FAIL:", type(exc).__name__, exc)


if __name__ == "__main__":
    asyncio.run(main())

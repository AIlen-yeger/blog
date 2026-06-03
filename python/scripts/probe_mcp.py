"""探测 MCP 配置：列出 server / tools / 试调用。

用法:
  python scripts/probe_mcp.py
  python scripts/probe_mcp.py sogou
  python scripts/probe_mcp.py sogou --args '{"query":"test","num_results":3}'
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.mcp.registry import get_mcp_client, list_mcp_names


async def _probe_one(name: str, args: dict) -> None:
    client = get_mcp_client(name)
    cfg = client.config
    print(f"\n=== {name} ===")
    print("enabled:", cfg.enabled)
    print("transport:", cfg.transport.value)
    if cfg.sse:
        print("url:", cfg.sse.url)
    if cfg.stdio:
        print("command:", cfg.stdio.command, cfg.stdio.args)

    names = await client.list_tool_names()
    print("tools:", names)

    if args:
        result = client.call_tool_sync(args)
        print("call ok:", result.ok)
        if result.error:
            print("error:", result.error)
        print("text preview:", (result.text or "")[:800])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", help="mcpServers 中的名称，默认 sogou")
    parser.add_argument("--args", default="", help='call_tool 参数 JSON，如 {"query":"hi"}')
    parser.add_argument("--list", action="store_true", help="仅列出已配置的 MCP")
    args = parser.parse_args()

    names = list_mcp_names()
    if args.list or not args.name:
        print("configured:", names)
        if args.list:
            return
        if not names:
            print("mcp_servers.json 为空")
            return

    name = args.name or (names[0] if names else "sogou")
    payload = json.loads(args.args) if args.args.strip() else {}
    if name == "sogou" and not payload:
        payload = {"query": "HACHI Rainy proof 创作背景", "num_results": 3}

    asyncio.run(_probe_one(name, payload))


if __name__ == "__main__":
    main()

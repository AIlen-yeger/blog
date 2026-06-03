from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from utils.mcp.base_client import McpClient
from utils.mcp.config_loader import load_mcp_servers
from utils.mcp.types import McpClientConfig

_clients: dict[str, McpClient] = {}

_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "mcp_servers.json"


@lru_cache(maxsize=1)
def _all_configs() -> dict[str, McpClientConfig]:
    path = os.getenv("MCP_SERVERS_CONFIG", str(_DEFAULT_CONFIG))
    return load_mcp_servers(path)


def get_mcp_client(name: str) -> McpClient:
    configs = _all_configs()
    if name not in configs:
        raise KeyError(f"unknown mcp: {name}, available={list(configs)}")
    if name not in _clients:
        _clients[name] = McpClient(configs[name])
    return _clients[name]


def is_mcp_enabled(name: str) -> bool:
    try:
        return _all_configs()[name].enabled
    except KeyError:
        return False


def list_mcp_names() -> list[str]:
    return list(_all_configs().keys())


def reload_mcp_configs() -> None:
    """修改 .env 或 mcp_servers.json 后调用，或重启进程。"""
    _all_configs.cache_clear()
    _clients.clear()

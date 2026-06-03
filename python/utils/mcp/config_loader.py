from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Any
from utils.mcp.types import (
    McpClientConfig,
    McpSseConfig,
    McpStdioConfig,
    McpTransport,
)

_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")
_ENV_REF_ONLY = re.compile(r"^\$\{([^}]+)\}$")


def _expand_env(value: Any) -> Any:
    """递归替换 ${VAR}；bool 字符串 "true"/"false" 可在外层再转。"""
    if isinstance(value, str):
        def repl(m: re.Match[str]) -> str:
            return os.getenv(m.group(1), "")
        return _ENV_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def _env_bool(name: str, *, default: bool = False) -> bool:
    from config.config import ensure_env_loaded

    ensure_env_loaded()
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _resolve_enabled(spec: dict[str, Any], *, default: bool = True) -> bool:
    """解析 enabled；${VAR} 直接读环境变量，避免展开成空串后被当成 false。"""
    raw = spec.get("enabled")
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return default
    if isinstance(raw, str):
        text = raw.strip()
        m = _ENV_REF_ONLY.match(text)
        if m:
            return _env_bool(m.group(1).strip(), default=default)
        expanded = _expand_env(text)
        if not str(expanded).strip():
            return default
        return _env_bool_from_literal(str(expanded), default=default)
    return _env_bool_from_literal(str(raw), default=default)


def _env_bool_from_literal(value: str, *, default: bool) -> bool:
    s = (value or "").strip().lower()
    if not s:
        return default
    if s in ("0", "false", "no", "off"):
        return False
    return s in ("1", "true", "yes", "on")


def _as_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return _env_bool_from_literal(str(value), default=default)


def _infer_transport(spec: dict[str, Any]) -> McpTransport:
    explicit = (spec.get("transport") or spec.get("type") or "").strip().lower()
    if explicit in ("stdio", "sse"):
        return McpTransport(explicit)
    if spec.get("url"):
        return McpTransport.SSE
    if spec.get("command"):
        return McpTransport.STDIO
    raise ValueError("无法推断 transport：需要 command(stdio) 或 url(sse)")




def spec_to_client_config(name: str, raw: dict[str, Any]) -> McpClientConfig:
    spec = _expand_env(raw)
    transport = _infer_transport(spec)
    enabled = _resolve_enabled(spec, default=True)
    default_tool = (spec.get("defaultTool") or spec.get("default_tool") or "").strip() or None
    if transport == McpTransport.SSE:
        url = (spec.get("url") or "").strip()
        if not url:
            raise ValueError(f"[{name}] SSE 缺少 url（可在 .env 设置 SOGOU_MCP_SSE_URL）")
        headers = spec.get("headers") or {}
        if not isinstance(headers, dict):
            raise ValueError(f"[{name}] headers 必须是对象")
        return McpClientConfig(
            name=name,
            transport=transport,
            enabled=enabled,
            sse=McpSseConfig(url=url, headers={str(k): str(v) for k, v in headers.items()}),
            default_tool=default_tool,
        )
    command = (spec.get("command") or "").strip()
    if not command:
        raise ValueError(f"[{name}] stdio 缺少 command")
    args = spec.get("args") or []
    if not isinstance(args, list):
        raise ValueError(f"[{name}] args 必须是数组")
    env = spec.get("env") or {}
    if not isinstance(env, dict):
        raise ValueError(f"[{name}] env 必须是对象")
    return McpClientConfig(
        name=name,
        transport=transport,
        enabled=enabled,
        stdio=McpStdioConfig(
            command=command,
            args=[str(a) for a in args],
            cwd=(spec.get("cwd") or None),
            env={str(k): str(v) for k, v in env.items()},
        ),
        default_tool=default_tool,
    )



def load_mcp_servers(path: str | Path) -> dict[str, McpClientConfig]:
    from config.config import ensure_env_loaded

    ensure_env_loaded()
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    servers = data.get("mcpServers") or data.get("servers") or data
    if not isinstance(servers, dict):
        raise ValueError("根节点需要 mcpServers 对象")
    out: dict[str, McpClientConfig] = {}
    for name, spec in servers.items():
        if not isinstance(spec, dict):
            continue
        out[name] = spec_to_client_config(name, spec)
    return out
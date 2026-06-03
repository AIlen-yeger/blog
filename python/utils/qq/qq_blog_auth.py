"""QQ 主号 → 博客用户 JWT（与 Web 端相同，供音乐等需登录的工具使用）。"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from utils.qq.qq_music_tools import blog_api_base

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 600.0
_cache: dict[str, tuple[float, "QqBlogIdentity"]] = {}


@dataclass(frozen=True)
class QqBlogIdentity:
    user_id: int
    access_token: str
    email: str = ""
    role: str = ""


def _ops_token() -> str:
    return (os.getenv("AGENT_OPS_TOKEN") or "").strip()


def _fetch_identity(friend_qq: str) -> QqBlogIdentity | None:
    ops = _ops_token()
    if not ops:
        logger.warning("[qq_blog_auth] AGENT_OPS_TOKEN unset, cannot issue blog JWT")
        return None

    qq = "".join(c for c in str(friend_qq).strip() if c.isdigit())
    if not qq:
        return None

    url = f"{blog_api_base()}/agent/ops/token-for-qq"
    payload = json.dumps({"qq": qq}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Ops-Token": ops,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:300]
        if exc.code == 401:
            logger.warning(
                "[qq_blog_auth] http 401 qq=%s: %s "
                "(Java 未放行 /agent/ops/* 或未重启后端；与 Web JWT 无关)",
                qq,
                err,
            )
        elif exc.code == 403:
            logger.warning(
                "[qq_blog_auth] http 403 qq=%s: %s (AGENT_OPS_TOKEN 与 Java app.agent.ops-token 不一致)",
                qq,
                err,
            )
        else:
            logger.warning("[qq_blog_auth] http %s qq=%s: %s", exc.code, qq, err)
        return None
    except urllib.error.URLError as exc:
        logger.warning("[qq_blog_auth] unreachable %s: %s", url, exc.reason)
        return None
    except Exception as exc:
        logger.warning("[qq_blog_auth] request failed qq=%s: %s", qq, exc)
        return None

    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict) or not data.get("found"):
        logger.info("[qq_blog_auth] no blog user for qq=%s email=%s", qq, data.get("email") if isinstance(data, dict) else "")
        return None

    token = (data.get("accessToken") or data.get("access_token") or "").strip()
    user_id = data.get("userId") or data.get("user_id") or 0
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        user_id = 0
    if not token or user_id <= 0:
        logger.warning("[qq_blog_auth] invalid payload for qq=%s: %s", qq, data)
        return None

    email = (data.get("email") or "").strip()
    role_raw = data.get("role")
    if isinstance(role_raw, str):
        role = role_raw.strip().lower()
    elif role_raw is not None:
        role = str(role_raw).strip().lower()
    else:
        role = ""
    logger.info(
        "[qq_blog_auth] issued blog session qq=%s user_id=%s role=%s",
        qq,
        user_id,
        role or "user",
    )
    return QqBlogIdentity(user_id=user_id, access_token=token, email=email, role=role)


def resolve_qq_blog_identity(friend_qq: str) -> QqBlogIdentity | None:
    """主号 QQ 在博客已注册（{qq}@qq.com）时返回 user_id + JWT。"""
    qq = "".join(c for c in str(friend_qq).strip() if c.isdigit())
    if not qq:
        return None

    now = time.monotonic()
    cached = _cache.get(qq)
    if cached and now - cached[0] <= _CACHE_TTL_SEC:
        return cached[1]

    identity = _fetch_identity(qq)
    if identity:
        _cache[qq] = (now, identity)
    return identity

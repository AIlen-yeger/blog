"""经 NapCat HTTP 拉取私聊历史（不依赖 qq-agent-mcp WS 缓冲）。"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from config.config import AgentConfig

logger = logging.getLogger(__name__)


def _parse_text_from_event(event: dict) -> str:
    raw = (event.get("raw_message") or "").strip()
    if raw:
        return raw
    message = event.get("message")
    if not isinstance(message, list):
        return ""
    parts: list[str] = []
    for seg in message:
        if not isinstance(seg, dict):
            continue
        if seg.get("type") == "text":
            data = seg.get("data") or {}
            if isinstance(data, dict):
                parts.append(str(data.get("text") or ""))
    return "".join(parts).strip()


def event_to_poll_message(event: dict, *, bot_qq: str) -> dict:
    sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
    sender_id = str(event.get("user_id") or sender.get("user_id") or "")
    text = _parse_text_from_event(event)
    return {
        "message_id": str(event.get("message_id") or ""),
        "sender_id": sender_id,
        "is_self": sender_id == str(bot_qq).strip(),
        "content": text,
        "text": text,
        "time": event.get("time"),
    }


def fetch_friend_private_history(friend_qq: str, *, count: int = 20) -> list[dict]:
    """调用 OneBot get_friend_msg_history，供 inbox poller 使用。"""
    cfg = AgentConfig()
    base = (cfg.napcat_http_url or "").rstrip("/")
    bot_qq = (cfg.qq_mcp_bot_qq or "").strip()
    if not base or not friend_qq:
        return []

    url = f"{base}/get_friend_msg_history"
    payload = {"user_id": int(str(friend_qq).strip()), "count": count}
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = (cfg.napcat_access_token or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:300]
        logger.warning("[napcat_history] http %s: %s", exc.code, err)
        return []
    except urllib.error.URLError as exc:
        logger.warning("[napcat_history] unreachable %s: %s", url, exc.reason)
        return []
    except Exception as exc:
        logger.warning("[napcat_history] request failed %s: %s", url, exc)
        return []

    if body.get("retcode") not in (0, None) and body.get("status") == "failed":
        logger.warning("[napcat_history] api error: %s", body)
        return []

    raw_data = body.get("data")
    if isinstance(raw_data, dict):
        events = raw_data.get("messages") or []
    elif isinstance(raw_data, list):
        events = raw_data
    else:
        events = []

    out: list[dict] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        msg = event_to_poll_message(ev, bot_qq=bot_qq)
        if msg.get("content"):
            out.append(msg)
    return out

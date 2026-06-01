"""后台轮询 QQ 私聊（QQ_MCP_ENABLED 时由 main lifespan 启动）。"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_DIR = Path("log")
_STATE_FILE = _STATE_DIR / "qq_inbox_seen.json"


def _load_seen() -> set[str]:
    if not _STATE_FILE.is_file():
        return set()
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return set(str(x) for x in data)
    except Exception:
        logger.warning("[qq_poller] corrupt seen file, reset")
    return set()


def _save_seen(seen: set[str], max_items: int = 2000) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    items = list(seen)[-max_items:]
    _STATE_FILE.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def _message_key(m: dict) -> str:
    return str(
        m.get("message_id")
        or m.get("id")
        or f"{m.get('time')}|{m.get('text') or m.get('raw_message')}"
    )


async def _poll_friend(mcp, friend_qq: str) -> None:
    from server.qq_chat_bridge import handle_qq_private_message_sync

    seen = _load_seen()
    messages = await mcp.get_recent_private(friend_qq, limit=20)

    for m in messages:
        if m.get("is_self"):
            continue
        key = _message_key(m)
        if key in seen:
            continue
        text = (m.get("text") or m.get("raw_message") or "").strip()
        if not text:
            continue

        seen.add(key)
        _save_seen(seen)

        try:
            reply = handle_qq_private_message_sync(friend_qq, text)
            if reply:
                await mcp.send_private(friend_qq, reply)
        except Exception:
            logger.exception("[qq_poller] handle failed friend=%s key=%s", friend_qq, key)


async def _poller_loop(interval: float, friends: list[str]) -> None:
    from utils.qq.qq_agent_mcp import QqMcpSession

    mcp = QqMcpSession()
    await mcp.open()
    logger.info("[qq_poller] loop started friends=%s interval=%.1fs", friends, interval)
    try:
        while True:
            for fq in friends:
                try:
                    await _poll_friend(mcp, fq)
                except Exception:
                    logger.exception("[qq_poller] poll friend=%s", fq)
            await asyncio.sleep(max(3.0, interval))
    finally:
        await mcp.close()


def start_qq_inbox_poller(*, friends: list[str], interval: float) -> None:
    if not friends:
        logger.warning("[qq_poller] QQ_MCP_FRIENDS empty, poller not started")
        return

    def _thread_main() -> None:
        try:
            asyncio.run(_poller_loop(interval, friends))
        except Exception:   
            logger.exception("[qq_poller] thread exited")

    t = threading.Thread(target=_thread_main, name="qq-inbox-poller", daemon=True)
    t.start()
    logger.info("[qq_poller] thread started friends=%s", friends)

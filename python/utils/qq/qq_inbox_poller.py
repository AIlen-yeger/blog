"""后台轮询 QQ 私聊（QQ_MCP_ENABLED 时由 main lifespan 启动）。"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_DIR = Path("log")
_STATE_FILE = _STATE_DIR / "qq_inbox_state.json"
_LEGACY_SEEN_FILE = _STATE_DIR / "qq_inbox_seen.json"
# 同一条消息 MCP/HTTP message_id 不一致时的短期内存去重（秒）
_RECENT_TTL = 45.0
_recent_handled: dict[str, float] = {}


@dataclass
class InboxState:
    seen: set[str] = field(default_factory=set)
    watermark: dict[str, int] = field(default_factory=dict)
    bootstrapped: set[str] = field(default_factory=set)


def _msg_text(m: dict) -> str:
    return (
        m.get("text")
        or m.get("raw_message")
        or m.get("content")
        or ""
    ).strip()


def _msg_time(m: dict) -> int | None:
    raw = m.get("time") if m.get("time") is not None else m.get("timestamp")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _same_incoming_message(a: dict, b: dict, *, time_slop: int = 8) -> bool:
    """MCP 缓冲与 NapCat HTTP 常对同一条私聊给出不同 message_id，用正文+时间对齐。"""
    text = _msg_text(a)
    if not text or text != _msg_text(b):
        return False
    sa = str(a.get("sender_id") or "")
    sb = str(b.get("sender_id") or "")
    if sa and sb and sa != sb:
        return False
    ta, tb = _msg_time(a), _msg_time(b)
    if ta is not None and tb is not None:
        return abs(ta - tb) <= time_slop
    return True


def _load_state() -> InboxState:
    if _STATE_FILE.is_file():
        try:
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                seen = data.get("seen") or []
                wm = data.get("watermark") or {}
                boot = data.get("bootstrapped") or []
                return InboxState(
                    seen=set(str(x) for x in seen),
                    watermark={str(k): int(v) for k, v in wm.items()},
                    bootstrapped=set(str(x) for x in boot),
                )
        except Exception:
            logger.warning("[qq_poller] corrupt state file, reset")

    state = InboxState()
    if _LEGACY_SEEN_FILE.is_file():
        try:
            legacy = json.loads(_LEGACY_SEEN_FILE.read_text(encoding="utf-8"))
            if isinstance(legacy, list):
                state.seen = set(str(x) for x in legacy)
                logger.info(
                    "[qq_poller] migrated %d keys from qq_inbox_seen.json",
                    len(state.seen),
                )
        except Exception:
            pass
    return state


def _save_state(state: InboxState, *, max_seen: int = 3000) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    seen_items = list(state.seen)[-max_seen:]
    payload = {
        "version": 1,
        "seen": seen_items,
        "watermark": state.watermark,
        "bootstrapped": sorted(state.bootstrapped),
    }
    _STATE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _message_key(m: dict, friend_qq: str) -> str:
    mid = str(m.get("message_id") or "").strip()
    if mid:
        return f"{friend_qq}:mid:{mid}"
    text = _msg_text(m)
    t = _msg_time(m)
    if t is not None:
        return f"{friend_qq}:t:{t}|{text}"
    return f"{friend_qq}:txt:{text}"


def _content_fingerprint(m: dict, friend_qq: str) -> str:
    sender = str(m.get("sender_id") or friend_qq).strip()
    text = _msg_text(m)
    t = _msg_time(m)
    bucket = t // 10 if t is not None else 0
    return f"{sender}|{bucket}|{text}"


def _recently_handled(fp: str) -> bool:
    now = time.monotonic()
    expired = [k for k, ts in _recent_handled.items() if now - ts > _RECENT_TTL]
    for k in expired:
        _recent_handled.pop(k, None)
    ts = _recent_handled.get(fp)
    return ts is not None and now - ts <= _RECENT_TTL


def _mark_recently_handled(fp: str) -> None:
    _recent_handled[fp] = time.monotonic()


def _merge_messages(mcp_msgs: list[dict], http_msgs: list[dict]) -> list[dict]:
    merged: list[dict] = list(http_msgs)
    http_by_mid = {
        str(m.get("message_id")).strip(): m
        for m in http_msgs
        if str(m.get("message_id") or "").strip()
    }

    for m in mcp_msgs:
        mid = str(m.get("message_id") or "").strip()
        if mid and mid in http_by_mid:
            continue
        if any(_same_incoming_message(m, h) for h in http_msgs):
            continue
        if any(_same_incoming_message(m, x) for x in merged):
            continue
        merged.append(m)

    merged.sort(key=lambda m: _msg_time(m) or 0)
    return merged


def _mark_message_seen(state: InboxState, m: dict, friend_qq: str) -> int | None:
    """写入 seen / 指纹，返回消息时间戳（若有）。"""
    state.seen.add(_message_key(m, friend_qq))
    state.seen.add(_content_fingerprint(m, friend_qq))
    return _msg_time(m)


def _bootstrap_friend(
    state: InboxState,
    friend_qq: str,
    messages: list[dict],
) -> None:
    """新设备/无水位线：把当前拉到的历史标为已处理，不触发 Agent。"""
    max_t = 0
    marked = 0
    for m in messages:
        if m.get("is_self"):
            continue
        if not _msg_text(m):
            continue
        t = _mark_message_seen(state, m, friend_qq)
        marked += 1
        if t is not None and t > max_t:
            max_t = t
    if max_t <= 0:
        max_t = int(time.time())
    state.watermark[friend_qq] = max_t
    state.bootstrapped.add(friend_qq)
    logger.info(
        "[qq_poller] bootstrap friend=%s watermark=%s marked=%d (no auto-reply for history)",
        friend_qq,
        max_t,
        marked,
    )


def _should_process_message(
    state: InboxState,
    m: dict,
    friend_qq: str,
) -> bool:
    key = _message_key(m, friend_qq)
    fp = _content_fingerprint(m, friend_qq)
    if key in state.seen or _recently_handled(fp):
        return False

    wm = state.watermark.get(friend_qq, 0)
    t = _msg_time(m)
    if t is not None and t <= wm:
        return False
    return True


async def _poll_friend(mcp, friend_qq: str) -> None:
    from config.config import AgentConfig
    from server.qq.bridge import handle_qq_private_message_sync
    from utils.qq.napcat_history import fetch_friend_private_history

    cfg = AgentConfig()
    state = _load_state()
    mcp_msgs = await mcp.get_recent_private(friend_qq, limit=20)
    http_msgs = fetch_friend_private_history(friend_qq, count=20)
    messages = _merge_messages(mcp_msgs, http_msgs)
    logger.info(
        "[qq_poller] friend=%s mcp=%d http=%d merged=%d wm=%s",
        friend_qq,
        len(mcp_msgs),
        len(http_msgs),
        len(messages),
        state.watermark.get(friend_qq),
    )

    if cfg.qq_mcp_bootstrap_on_start and friend_qq not in state.bootstrapped:
        _bootstrap_friend(state, friend_qq, messages)
        _save_state(state)
        return

    for m in messages:
        if m.get("is_self"):
            continue
        text = _msg_text(m)
        if not text:
            continue
        if not _should_process_message(state, m, friend_qq):
            continue

        key = _message_key(m, friend_qq)
        fp = _content_fingerprint(m, friend_qq)
        t = _mark_message_seen(state, m, friend_qq)
        _save_state(state)
        _mark_recently_handled(fp)

        try:
            reply = handle_qq_private_message_sync(friend_qq, text)
            if reply:
                await mcp.send_private(friend_qq, reply)
            if t is not None:
                state.watermark[friend_qq] = max(
                    state.watermark.get(friend_qq, 0),
                    t,
                )
                _save_state(state)
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


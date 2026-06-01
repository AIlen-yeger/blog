"""QQ 私聊 → Agent（非流式 channel=qq）→ 回复文本。"""
from __future__ import annotations

import logging

from config.config import AgentConfig
from server.agent_entry import get_agent_entry

logger = logging.getLogger(__name__)

QQ_BRIDGE_USER_ID = 0


def qq_session_id(friend_qq: str) -> str:
    return f"qq:private:{friend_qq}"


def handle_qq_private_message_sync(friend_qq: str, text: str) -> str:
    """同步入口：poller 线程内调用。"""
    cfg = AgentConfig()
    entry = get_agent_entry()
    logger.info("[qq_bridge] friend=%s text=%s", friend_qq, (text or "")[:80])
    reply = entry.run_once(
        question=text,
        session_id=qq_session_id(friend_qq),
        user_id=QQ_BRIDGE_USER_ID,
        limit=cfg.history_limit,
        access_token="",
        channel="qq",
    )
    return (reply or "").strip()[:4000]

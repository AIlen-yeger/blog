"""QQ 私聊入口：确定性分路 → AgentEntry。"""

from __future__ import annotations

import logging

from config.config import AgentConfig
from server.qq.daily_brief import try_handle_daily_brief_qq
from server.qq.history import persist_qq_turn
from utils.qq.qq_blog_auth import resolve_qq_blog_identity

logger = logging.getLogger(__name__)


def handle_qq_private_message_sync(friend_qq: str, text: str) -> str:
    """同步入口：poller 线程内调用。"""
    from server.agent_entry import get_agent_entry

    cfg = AgentConfig()
    entry = get_agent_entry()

    user_id = 0
    access_token = ""
    account = ""
    user_role = ""
    identity = resolve_qq_blog_identity(friend_qq)
    if identity:
        user_id = identity.user_id
        access_token = identity.access_token
        account = identity.email or ""
        user_role = identity.role or ""
        logger.info(
            "[qq_bridge] friend=%s blog_user_id=%s email=%s",
            friend_qq,
            user_id,
            identity.email or "(unknown)",
        )
    else:
        logger.info("[qq_bridge] friend=%s guest (no blog account for QQ)", friend_qq)

    logger.info("[qq_bridge] text=%s", (text or "")[:80])

    from service.btc_dca_position import try_handle_qq_message

    session_id = f"qq:private:{''.join(c for c in friend_qq if c.isdigit()) or friend_qq}"

    dca_reply = try_handle_qq_message(text)
    if dca_reply:
        logger.info("[qq_bridge] btc_dca handled friend=%s", friend_qq)
        persist_qq_turn(friend_qq, user_id, text, dca_reply)
        return dca_reply[:4000]

    daily_reply = try_handle_daily_brief_qq(
        text,
        friend_qq,
        account=account,
        user_role=user_role,
    )
    if daily_reply:
        logger.info("[qq_bridge] daily_brief handled friend=%s", friend_qq)
        persist_qq_turn(friend_qq, user_id, text, daily_reply)
        return daily_reply[:4000]

    result = entry.run(
        question=text,
        session_id=session_id,
        user_id=user_id,
        limit=cfg.history_limit,
        access_token=access_token,
        account=account,
        user_role=user_role,
        friend_qq=friend_qq,
        channel="qq",
        execution_mode="fast",
    )
    logger.info(
        "[qq_bridge] done friend=%s intent=%s role=%s account=%s",
        friend_qq,
        result.intent,
        user_role or "-",
        (account or "-")[:40],
    )
    return (result.collect_plain_text() or "").strip()[:4000]

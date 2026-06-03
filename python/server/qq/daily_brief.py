"""QQ 开发者手动触发定投每日简报。"""

from __future__ import annotations

import logging

from server.qq.developer import is_developer_on_qq

logger = logging.getLogger(__name__)

_DAILY_BRIEF_TRIGGERS = (
    "每日报告",
    "每日简报",
    "定投日报",
    "定投报告",
    "早报",
    "发日报",
    "发早报",
    "btc日报",
    "btc 日报",
    "纠缠之缘日报",
    "今日定投",
)


def is_daily_brief_command(text: str) -> bool:
    q = (text or "").strip()
    if not q:
        return False
    lower = q.lower().replace(" ", "")
    if lower in {t.replace(" ", "") for t in _DAILY_BRIEF_TRIGGERS}:
        return True
    for t in _DAILY_BRIEF_TRIGGERS:
        if t in q or t.replace(" ", "") in lower:
            if len(q) <= 24:
                return True
    return False


def try_handle_daily_brief_qq(
    text: str,
    friend_qq: str,
    *,
    account: str = "",
    user_role: str = "",
) -> str | None:
    """开发者 QQ 私聊触发日报；返回要回复的全文（由 poller 发出，不再走 NapCat 二次推送）。"""
    if not is_daily_brief_command(text):
        return None
    if not is_developer_on_qq(friend_qq, account=account, user_role=user_role):
        return None

    from service.btc_daily_brief import send_daily_brief_to_developer

    logger.info("[qq_daily] manual trigger friend=%s", friend_qq)
    result = send_daily_brief_to_developer(force=True, push=False)
    if not result.get("ok"):
        status = result.get("status") or "unknown"
        if status == "disabled":
            return "定投日报功能关着哦，要开 BTC_DCA_DAILY_ENABLED～"
        if status == "napcat_not_configured":
            return "行情没拉到或配置不全，稍后再试呀。"
        return f"日报生成失败（{status}），看一下 agent 日志哦。"

    message = (result.get("message") or "").strip()
    if message:
        return message[:4000]
    return "嗯…日报是空的，稍后再试一次？"

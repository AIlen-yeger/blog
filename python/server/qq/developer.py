"""QQ 渠道开发者身份判断。"""

from __future__ import annotations

from server.aicoin_access import is_aicoin_allowed


def is_developer_on_qq(
    friend_qq: str,
    *,
    account: str = "",
    user_role: str = "",
) -> bool:
    """与 AiCoin 开发者白名单一致：admin / DEVELOPER_EMAIL / DEVELOPER_QQ。"""
    return is_aicoin_allowed(
        account=account,
        user_role=user_role,
        friend_qq=friend_qq,
        channel="qq",
    )

"""AiCoin 行情子图访问控制：仅站点管理员 / 开发者账号可用。"""

from __future__ import annotations

from config.config import AgentConfig
from server.state import AgentState


def _normalize_qq(qq: str) -> str:
    return "".join(c for c in (qq or "").strip() if c.isdigit())


def is_aicoin_allowed(
    *,
    account: str = "",
    user_role: str = "",
    friend_qq: str = "",
    channel: str = "",
) -> bool:
    """管理员（role=admin）、开发者邮箱、或 QQ 主号（DEVELOPER_QQ）允许走 aicoin 子图。"""
    role = (user_role or "").strip().lower()
    if role == "admin":
        return True

    email = (account or "").strip().lower()
    dev_email = AgentConfig().developer_email
    if dev_email and email and email == dev_email:
        return True

    ch = (channel or "").strip().lower()
    if ch == "qq":
        dev_qq = AgentConfig().developer_qq
        qq = _normalize_qq(friend_qq)
        if dev_qq and qq and qq == dev_qq:
            return True
        # 博客已绑定 {qq}@qq.com 且为 admin 时，account/role 已在上面判断
    return False


def aicoin_allowed_for_state(state: AgentState) -> bool:
    return is_aicoin_allowed(
        account=(state.get("account") or "").strip(),
        user_role=(state.get("user_role") or "").strip(),
        friend_qq=(state.get("friend_qq") or "").strip(),
        channel=(state.get("channel") or "").strip(),
    )

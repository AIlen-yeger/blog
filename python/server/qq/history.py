"""QQ 私聊会话写入 chat 历史（MySQL + Redis）。"""

from __future__ import annotations

from service.chat_history import ChatHistoryService


def qq_session_id(friend_qq: str) -> str:
    digits = "".join(c for c in (friend_qq or "").strip() if c.isdigit())
    return f"qq:private:{digits or friend_qq}"


def persist_qq_turn(
    friend_qq: str,
    user_id: int,
    user_question: str,
    assistant_answer: str,
) -> None:
    session_id = qq_session_id(friend_qq)
    ChatHistoryService().save_turn(
        session_id=session_id,
        user_id=int(user_id or 0),
        user_question=user_question,
        assistant_answer=assistant_answer,
        channel="qq",
    )

"""提示词分层：角色设定 + 渠道技能 + 意图技能（Markdown 文件）。"""

from __future__ import annotations

from utils.path_tools import get_abs_path

INTENT_SKILL_MAP: dict[str, str] = {
    "music": "music",
    "add_son": "music",
    "bug": "bug",
    "commit_user": "comment",
}

CHANNEL_SKILL_MAP: dict[str, str] = {
    "qq": "channel_qq",
    "web": "channel_web",
}


def build_system_prompt(
    *,
    intent: str | None = None,
    user_logged_in: bool = False,
    channel: str | None = None,
) -> str:
    intent_key = (intent or "").strip().lower()

    if intent_key == "bug":
        parts = [_read_prompt("prompt/bug_ops_system.md"), _read_prompt("prompt/skills/bug.md")]
        return "\n\n---\n\n".join(p for p in parts if p)

    if intent_key == "commit_user":
        parts = [_read_prompt("prompt/system.md"), _read_prompt("prompt/skills/comment.md")]
        ch = (channel or "web").strip().lower()
        channel_skill = CHANNEL_SKILL_MAP.get(ch)
        if channel_skill:
            parts.insert(1, _read_prompt(f"prompt/skills/{channel_skill}.md"))
        return "\n\n---\n\n".join(p for p in parts if p)

    parts = [_read_prompt("prompt/system.md")]
    ch = (channel or "web").strip().lower()
    channel_skill = CHANNEL_SKILL_MAP.get(ch)
    if channel_skill:
        parts.append(_read_prompt(f"prompt/skills/{channel_skill}.md"))

    skill_key = INTENT_SKILL_MAP.get(intent_key)
    if skill_key:
        parts.append(_read_prompt(f"prompt/skills/{skill_key}.md"))

    if skill_key == "music" and user_logged_in:
        parts.append(
            "【会话状态】当前用户已登录，需要查听歌记录或保存曲目时直接处理，"
            "不要反复询问是否登录。"
        )

    return "\n\n---\n\n".join(p for p in parts if p)


def read_prompt(relative_path: str) -> str:
    return _read_prompt(relative_path)


def _read_prompt(relative_path: str) -> str:
    with open(get_abs_path(relative_path), encoding="utf-8") as f:
        return f.read().strip()

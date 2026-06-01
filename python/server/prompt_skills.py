"""提示词分层：角色设定 + 渠道技能 + 意图技能。"""

from __future__ import annotations

from utils.path_tools import get_abs_path

# 意图 → 技能文件名（位于 prompt/skills/）
INTENT_SKILL_MAP: dict[str, str] = {
    "music": "music",
    "add_son": "music",
    "bug": "bug",
}

# 渠道 → 场景技能（QQ 日常陪伴 / Web 业务助手）
CHANNEL_SKILL_MAP: dict[str, str] = {
    "qq": "channel_qq",
    "web": "channel_web",
}


def _read_text(relative_path: str) -> str:
    path = get_abs_path(relative_path)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def build_system_prompt(
    *,
    intent: str | None = None,
    user_logged_in: bool = False,
    channel: str | None = None,
) -> str:
    """
    组装 System 提示：
      1. prompt/system_prompt（身份 + 全员格式底线）
      2. prompt/skills/channel_{qq|web}.txt（渠道场景）
      3. prompt/skills/{music|bug}.txt（意图技能，按需）
    """
    intent_key = (intent or "").strip().lower()

    if intent_key == "bug":
        parts: list[str] = [_read_text("prompt/bug_ops_system.txt")]
        skill_key = INTENT_SKILL_MAP.get("bug")
        if skill_key:
            parts.append(_read_text(f"prompt/skills/{skill_key}.txt"))
        return "\n\n---\n\n".join(p for p in parts if p)

    parts: list[str] = [_read_text("prompt/system_prompt")]

    ch = (channel or "web").strip().lower()
    channel_skill = CHANNEL_SKILL_MAP.get(ch)
    if channel_skill:
        parts.append(_read_text(f"prompt/skills/{channel_skill}.txt"))

    skill_key = INTENT_SKILL_MAP.get(intent_key)
    if skill_key:
        parts.append(_read_text(f"prompt/skills/{skill_key}.txt"))

    if skill_key == "music" and user_logged_in:
        parts.append(
            "【会话状态】当前用户已登录，需要查听歌记录或保存曲目时直接处理，"
            "不要反复询问是否登录。"
        )

    return "\n\n---\n\n".join(p for p in parts if p)

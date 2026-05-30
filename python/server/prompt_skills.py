"""提示词分层：角色设定（始终） + 按意图加载的技能片段。"""

from __future__ import annotations

from functools import lru_cache

from utils.path_tools import get_abs_path

# 意图 → 技能文件名（位于 prompt/skills/）
INTENT_SKILL_MAP: dict[str, str] = {
    "music": "music",
    "add_son": "music",
    "bug": "bug",
}


@lru_cache(maxsize=8)
def _read_text(relative_path: str) -> str:
    path = get_abs_path(relative_path)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def build_system_prompt(
    *,
    intent: str | None = None,
    user_logged_in: bool = False,
) -> str:
    """
    组装 System 提示：先角色设定，再按需追加技能片段。
    intent 为 music / add_son 时加载音乐技能；bug 为内部运维，不用 Kohaku 人设。
    """
    if (intent or "").strip().lower() == "bug":
        parts: list[str] = [_read_text("prompt/bug_ops_system.txt")]
        skill_key = INTENT_SKILL_MAP.get("bug")
        if skill_key:
            parts.append(_read_text(f"prompt/skills/{skill_key}.txt"))
        return "\n\n---\n\n".join(p for p in parts if p)

    parts: list[str] = [_read_text("prompt/system_prompt")]

    skill_key = INTENT_SKILL_MAP.get((intent or "").strip().lower())
    if skill_key:
        parts.append(_read_text(f"prompt/skills/{skill_key}.txt"))

    if skill_key == "music" and user_logged_in:
        parts.append(
            "【会话状态】当前用户已登录，需要查听歌记录或保存曲目时直接处理，"
            "不要反复询问是否登录。"
        )

    return "\n\n---\n\n".join(p for p in parts if p)

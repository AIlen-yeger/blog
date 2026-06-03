"""提示词分层：角色设定 + 渠道技能 + 意图技能（Markdown 文件）。"""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from utils.path_tools import get_abs_path
from utils.world_lexicon import WORLD_LEXICON_PROMPT

_AICOIN_SECTION_RE = re.compile(r"<!--\s*@section\s+(\w+)\s*-->", re.I)

INTENT_SKILL_MAP: dict[str, str] = {
    "music": "music",
    "add_son": "music",
    "bug": "bug",
    "commit_user": "comment",
    "aicoin": "aicoin",
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
    developer_name: str | None = None,
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
        parts.append(_session_context(developer_name))
        return "\n\n---\n\n".join(p for p in parts if p)

    parts = [_read_prompt("prompt/system.md")]
    ch = (channel or "web").strip().lower()
    channel_skill = CHANNEL_SKILL_MAP.get(ch)
    if channel_skill:
        parts.append(_read_prompt(f"prompt/skills/{channel_skill}.md"))

    skill_key = INTENT_SKILL_MAP.get(intent_key)
    if skill_key:
        if skill_key == "aicoin":
            parts.append(read_aicoin_skill("web"))
            if ch == "qq":
                parts.append(read_aicoin_skill("qq_tone", include_preamble=False))
        else:
            parts.append(_read_prompt(f"prompt/skills/{skill_key}.md"))

    if skill_key == "music" and user_logged_in:
        parts.append(
            "【会话状态】当前用户已登录，需要查听歌记录或保存曲目时直接处理，"
            "不要反复询问是否登录。"
        )

    return "\n\n---\n\n".join(p for p in parts if p)


def _session_context(developer_name: str | None) -> str:
    """当前对话对象与时间，供 Kohaku 回答「我是谁 / 几点了」。"""
    name = (developer_name or "").strip()
    try:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        time_line = now.strftime("%Y-%m-%d %H:%M") + "（Asia/Shanghai）"
    except Exception:
        time_line = "未知"

    lines = ["# 当前会话", f"- 当前时间：{time_line}"]
    if name:
        lines.append(
            f"- 正在与你对话的是开发者；用户问「我叫什么 / 我的名字」时，"
            f"回答「{name}」（这是开发者在本站的称呼，不要改成「主人」或泛称「你」）。"
        )
    else:
        lines.append("- 用户是开发者；若未提供具体称呼，可亲切叫「你」，但不要称「主人」。")
    return "\n".join(lines)


def read_prompt(relative_path: str) -> str:
    return _read_prompt(relative_path)


def read_aicoin_skill(section: str | None = None, *, include_preamble: bool = True) -> str:
    """读取合并后的 aicoin.md；section 为 web | qq_tone | qq_data | dca_daily。"""
    raw = _read_prompt("prompt/skills/aicoin.md")
    chunks = _AICOIN_SECTION_RE.split(raw)
    preamble = "\n\n".join(
        p.strip() for p in (chunks[0].strip(), WORLD_LEXICON_PROMPT) if p.strip()
    )
    sections: dict[str, str] = {}
    for i in range(1, len(chunks), 2):
        if i + 1 < len(chunks):
            sections[chunks[i].strip().lower()] = chunks[i + 1].strip()

    if section is None:
        return raw.strip()

    key = section.strip().lower()
    body = sections.get(key, "")
    if not body:
        raise KeyError(f"unknown aicoin skill section: {section!r}")
    if include_preamble:
        return "\n\n---\n\n".join(p for p in (preamble, body) if p)
    return body


def _read_prompt(relative_path: str) -> str:
    with open(get_abs_path(relative_path), encoding="utf-8") as f:
        return f.read().strip()

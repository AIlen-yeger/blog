"""提示词分层：酒馆（人设） + OpenClaw（按路由能力）。

维护说明见 docs/prompt-layering.md。
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from server.skills_server.aicoin_prompt import read_aicoin_skill
from server.skills_server.prompt_layers import CAPABILITY_INTENTS, CHAT_LEAN_CHANNELS
from server.skills_server.skill_registry import CHARACTER_SLUG, get_registry
from utils.path_tools import get_abs_path

# 兼容旧引用
_CAPABILITY_INTENTS = CAPABILITY_INTENTS


def _registry(character_slug: str | None = None):
    return get_registry(character_slug)


def _read_prompt(relative_path: str) -> str:
    with open(get_abs_path(relative_path), encoding="utf-8") as f:
        return f.read().strip()


def build_system_prompt(
    *,
    intent: str | None = None,
    user_logged_in: bool = False,
    channel: str | None = None,
    developer_name: str | None = None,
    character_slug: str | None = None,
    user_message: str | None = None,
    episode_summary: str = "",
    max_optional_core: int = 3,
) -> str:
    from server.skills_server.openclaw_capabilities import build_openclaw_stack
    from server.skills_server.tavern_persona import build_tavern_persona

    registry = _registry(character_slug)
    intent_key = (intent or "chat").strip().lower()
    if intent_key == "add_son":
        intent_key = "music"
    ch = (channel or "web").strip().lower()
    msg = (user_message or "").strip()
    ep_sum = (episode_summary or "").strip()
    lean_chat = intent_key == "chat" and ch in CHAT_LEAN_CHANNELS
    minimal_tavern = lean_chat or intent_key in CAPABILITY_INTENTS

    parts: list[str] = []

    if intent_key in CAPABILITY_INTENTS:
        tavern, _ = build_tavern_persona(
            registry,
            intent=intent_key,
            channel=ch,
            user_message=msg,
            episode_summary=ep_sum,
            minimal=True,
            include_channel=True,
        )
        if tavern:
            parts.append(tavern)
        openclaw, _ = build_openclaw_stack(
            registry,
            intent=intent_key,
            channel=ch,
            user_logged_in=user_logged_in,
            character_slug=character_slug,
            lean_chat=False,
        )
        if openclaw:
            parts.append(openclaw)
    else:
        # QQ lean：允许 optional，但由 assembler 传入的上限封顶为 1
        opt_max = min(max(0, max_optional_core), 1) if lean_chat else max_optional_core
        tavern, _ = build_tavern_persona(
            registry,
            intent=intent_key,
            channel=ch,
            user_message=msg,
            episode_summary=ep_sum,
            max_optional_core=opt_max,
            include_channel=True,
            minimal=minimal_tavern,
        )
        if tavern:
            parts.append(tavern)
        openclaw, _ = build_openclaw_stack(
            registry,
            intent=intent_key,
            channel=ch,
            user_logged_in=user_logged_in,
            character_slug=character_slug,
            lean_chat=lean_chat,
        )
        if openclaw:
            parts.append(openclaw)

    if intent_key == "commit_user":
        parts.append(_session_context(developer_name))

    return "\n\n---\n\n".join(p for p in parts if p)


def character_lore_path(
    name: str = "lacia_static.yaml",
    *,
    character_slug: str | None = None,
) -> str:
    registry = _registry(character_slug)
    default_name = registry.lore_default.split("/")[-1]
    lore_rel = registry.lore_default if (not name or name == default_name) else name
    if "/" in lore_rel:
        return f"{registry.character_root}/{lore_rel}"
    return f"{registry.character_root}/lore/{lore_rel}"


def _session_context(developer_name: str | None) -> str:
    name = (developer_name or "").strip()
    try:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        time_line = now.strftime("%Y-%m-%d %H:%M") + "（Asia/Shanghai）"
    except Exception:
        time_line = "未知"

    lines = [f"当前时间：{time_line}"]
    if name:
        lines.append(f"开发者称呼：{name}（问名字答此，勿称主人）")
    else:
        lines.append("对话对象为开发者")
    return "【会话】\n" + "\n".join(lines)


def read_prompt(relative_path: str) -> str:
    return _read_prompt(relative_path)


__all__ = [
    "CHARACTER_SLUG",
    "CAPABILITY_INTENTS",
    "_CAPABILITY_INTENTS",
    "build_system_prompt",
    "character_lore_path",
    "read_aicoin_skill",
    "read_prompt",
]

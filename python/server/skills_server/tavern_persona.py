"""酒馆层：角色人设、渠道语气、optional core、lore/recall（不负责工具能力）。"""

from __future__ import annotations

from server.skills_server.optional_core import select_optional_core_files
from server.skills_server.skill_registry import CharacterSkillRegistry
from utils.path_tools import get_abs_path


def _read(registry: CharacterSkillRegistry, rel: str) -> str:
    path = get_abs_path(f"{registry.character_root}/{rel}")
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def build_tavern_persona(
    registry: CharacterSkillRegistry,
    *,
    intent: str,
    channel: str,
    user_message: str,
    episode_summary: str = "",
    max_optional_core: int = 3,
    include_channel: bool = True,
    minimal: bool = False,
) -> tuple[str, list[str]]:
    """返回 (拼接文本, 已加载层名列表)。"""
    ch = (channel or "web").strip().lower()
    intent_key = (intent or "chat").strip().lower()
    if intent_key == "add_son":
        intent_key = "music"

    parts: list[str] = []
    loaded: list[str] = []

    anchor = registry.permanent_file
    if anchor:
        block = _read(registry, anchor)
        if block:
            parts.append(block)
            loaded.append(f"tavern:{anchor}")

    if not minimal:
        for rel in registry.tavern_constant:
            block = _read(registry, rel)
            if block:
                parts.append(block)
                loaded.append(f"tavern_constant:{rel.split('/')[-1]}")

    if not minimal and max_optional_core > 0:
        optional_files = select_optional_core_files(
            registry,
            intent=intent_key,
            haystack=f"{user_message}\n{episode_summary}",
            max_files=max_optional_core,
        )
    else:
        optional_files = []

    for rel in optional_files:
        block = _read(registry, rel)
        if block:
            parts.append(block)
            loaded.append(f"tavern_optional:{rel.split('/')[-1]}")

    if include_channel:
        channel_rel = registry.channel_path(ch)
        if channel_rel:
            block = _read(registry, channel_rel)
            if block:
                parts.append(block)
                loaded.append(f"tavern_channel:{ch}")

    text = "\n\n---\n\n".join(p for p in parts if p)
    return text, loaded

"""core/*.md 按需渐进加载（酒馆式：关键词 / intent 触发，有上限）。"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from server.skills_server.optional_core_types import OptionalCoreMeta

if TYPE_CHECKING:
    from server.skills_server.skill_registry import CharacterSkillRegistry

__all__ = [
    "OptionalCoreMeta",
    "optional_core_enabled",
    "select_optional_core_files",
]


def optional_core_enabled() -> bool:
    return os.getenv("PROMPT_OPTIONAL_CORE_ENABLED", "true").lower() == "true"


def select_optional_core_files(
    registry: CharacterSkillRegistry,
    *,
    intent: str,
    haystack: str,
    max_files: int = 2,
) -> list[str]:
    """返回应插入 permanent 之后的 core 相对路径列表。"""
    if not optional_core_enabled() or not registry.optional_core:
        return []

    intent_key = (intent or "chat").strip().lower()
    if intent_key == "add_son":
        intent_key = "music"
    hay = (haystack or "").lower()

    scored: list[tuple[int, int, str]] = []
    for meta in registry.optional_core:
        score = 0
        if meta.constant:
            score = 100
        elif meta.intents and intent_key in meta.intents:
            score = 80 + meta.priority
        elif meta.keys and hay and any(k in hay for k in meta.keys):
            score = 50 + meta.priority
        if score > 0:
            scored.append((score, meta.priority, meta.file))

    scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
    out: list[str] = []
    seen: set[str] = set()
    for _, _, file_rel in scored:
        if file_rel in seen:
            continue
        seen.add(file_rel)
        out.append(file_rel)
        if len(out) >= max(0, max_files):
            break
    return out

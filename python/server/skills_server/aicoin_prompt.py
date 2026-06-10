"""aicoin capability 分段读取（无 prompt_skills 依赖）。"""

from __future__ import annotations

import re

from server.skills_server.prompt_layers import CAPABILITY_INTENTS
from server.skills_server.skill_registry import get_registry
from utils.path_tools import get_abs_path
from utils.world_lexicon import WORLD_LEXICON_PROMPT

_AICOIN_SECTION_RE = re.compile(r"<!--\s*@section\s+(\w+)\s*-->", re.I)


def read_aicoin_skill(
    section: str | None = None,
    *,
    include_preamble: bool = True,
    character_slug: str | None = None,
) -> str:
    """读取 capabilities/aicoin.md；section 为 web | qq_tone | qq_data | dca_daily。"""
    registry = get_registry(character_slug)
    aicoin_cap = registry.get_for_intent("aicoin")
    if not aicoin_cap:
        raise KeyError("aicoin capability not in manifest")
    path = get_abs_path(registry.capability_path(aicoin_cap))
    raw = path.read_text(encoding="utf-8").strip()
    chunks = _AICOIN_SECTION_RE.split(raw)
    preamble = "\n\n".join(
        p.strip() for p in (chunks[0].strip(), WORLD_LEXICON_PROMPT) if p.strip()
    )
    sections: dict[str, str] = {}
    for i in range(1, len(chunks), 2):
        if i + 1 < len(chunks):
            sections[chunks[i].strip().lower()] = chunks[i + 1].strip()

    if section is None:
        return raw

    key = section.strip().lower()
    body = sections.get(key, "")
    if not body:
        raise KeyError(f"unknown aicoin skill section: {section!r}")
    if include_preamble:
        return "\n\n---\n\n".join(p for p in (preamble, body) if p)
    return body

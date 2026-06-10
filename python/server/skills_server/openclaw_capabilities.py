"""OpenClaw 层：按 intent 只加载当前路由所需能力说明。"""

from __future__ import annotations

from server.skills_server.aicoin_prompt import read_aicoin_skill
from server.skills_server.skill_registry import CharacterSkillRegistry, CapabilityMeta
from utils.path_tools import get_abs_path


def _read_cap(registry: CharacterSkillRegistry, cap: CapabilityMeta) -> str:
    return get_abs_path(registry.capability_path(cap)).read_text(encoding="utf-8").strip()


def build_openclaw_stack(
    registry: CharacterSkillRegistry,
    *,
    intent: str,
    channel: str,
    user_logged_in: bool = False,
    character_slug: str | None = None,
    lean_chat: bool = False,
) -> tuple[str, list[str]]:
    """返回 (拼接文本, 已加载层名列表)。不含渠道块（渠道归酒馆）。"""
    intent_key = (intent or "").strip().lower()
    if intent_key == "add_son":
        intent_key = "music"
    ch = (channel or "web").strip().lower()
    parts: list[str] = []
    loaded: list[str] = []

    brief_rel = registry.openclaw_brief_file
    if brief_rel and not (intent_key == "chat" and lean_chat):
        block = get_abs_path(f"{registry.character_root}/{brief_rel}").read_text(
            encoding="utf-8"
        ).strip()
        if block:
            parts.append(block)
            loaded.append(f"openclaw:{brief_rel}")

    if intent_key == "bug":
        bug_cap = registry.get_for_intent("bug")
        if bug_cap:
            if bug_cap.ops_file:
                ops = get_abs_path(registry.ops_path(bug_cap) or "").read_text(
                    encoding="utf-8"
                ).strip()
                if ops:
                    parts.append(ops)
                    loaded.append("openclaw:ops/bug_ops.md")
            parts.append(_read_cap(registry, bug_cap))
            loaded.append("openclaw:capabilities/bug.md")
        return "\n\n---\n\n".join(p for p in parts if p), loaded

    intent_cap = registry.get_for_intent(intent_key) if intent_key else None

    if intent_key == "chat":
        chat_cap = registry.get_for_intent("chat")
        if chat_cap:
            parts.append(_read_cap(registry, chat_cap))
            loaded.append("openclaw:capabilities/chat_constraints.md")
        if not lean_chat:
            index_rel = "capabilities/service_index.md"
            index_path = get_abs_path(f"{registry.character_root}/{index_rel}")
            if index_path.is_file():
                parts.append(index_path.read_text(encoding="utf-8").strip())
                loaded.append(f"openclaw:{index_rel}")
    elif intent_cap:
        if intent_key == "aicoin":
            parts.append(read_aicoin_skill("web", character_slug=character_slug))
            loaded.append("openclaw:capabilities/aicoin@web")
            if ch == "qq":
                parts.append(
                    read_aicoin_skill(
                        "qq_tone",
                        include_preamble=False,
                        character_slug=character_slug,
                    )
                )
                loaded.append("openclaw:capabilities/aicoin@qq_tone")
        else:
            parts.append(_read_cap(registry, intent_cap))
            loaded.append(f"openclaw:{intent_cap.file}")

    if intent_key == "music" and user_logged_in:
        parts.append("【会话】已登录，查歌单/加歌勿再问登录。")
        loaded.append("openclaw:session_logged_in")

    if intent_key == "commit_user":
        commit_cap = registry.get_for_intent("commit_user")
        if commit_cap:
            parts.append(_read_cap(registry, commit_cap))
            loaded.append("openclaw:capabilities/comment.md")

    text = "\n\n---\n\n".join(p for p in parts if p)
    return text, loaded

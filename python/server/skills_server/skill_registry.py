"""从 character-skill manifest 加载能力元数据（OpenClaw 式注册表）。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from server.skills_server.optional_core_types import OptionalCoreMeta, parse_optional_core_spec
from utils.path_tools import get_abs_path

logger = logging.getLogger(__name__)

CHARACTER_SLUG = "lacia-blog"

_DEFAULT_DESCRIPTIONS: dict[str, str] = {
    "chat": "闲聊陪伴，无工具",
    "music": "QQ 音乐链接、听歌排行/报告、加歌",
    "aicoin": "只读行情、定投与快讯",
    "commit_user": "笔记下回复开发者",
    "publish_note": "从对话/附件发布新笔记",
    "bug": "向开发者汇报站点异常",
}





@dataclass(frozen=True)
class CapabilityMeta:

    id: str
    description: str

    #manifest里的capabilities字段  "chat": { "intent": "chat", "file": "capabilities/chat.md", "tools_route": null }
    intent: str | None
    file: str
    tools_route: str | None

    #运维文件
    ops_file: str | None = None


@dataclass(frozen=True)
class CharacterSkillRegistry:
    """
    将manifest.json注入 属性解析
    slug：别名
    character_root：角色技能包的目录
    permanent_file：角色设定持久化的文件
    global_prompts：全局提示词，判断路由和记忆摘要的模型使用
    capabilities：能力 这里指agent调用的工具能力 不同路由能力不同-》music路由 添加歌曲
    intent_to_capability：路由下的具体能力
    channel_files：渠道提示词路径
    optional_core：可选择的设定skills
    """
    slug: str
    character_root: str
    permanent_file: str
    openclaw_brief_file: str
    tavern_constant: tuple[str, ...]
    global_prompts: dict[str, str]
    lore_default: str
    capabilities: dict[str, CapabilityMeta]
    intent_to_capability: dict[str, CapabilityMeta]
    channel_files: dict[str, str]
    optional_core: tuple[OptionalCoreMeta, ...]
    routable_intents: frozenset[str]

    def capability_path(self, cap: CapabilityMeta) -> str:
        return f"{self.character_root}/{cap.file}"

    def channel_path(self, channel: str) -> str | None:
        rel = self.channel_files.get((channel or "web").strip().lower())
        if not rel:
            return None
        return f"{self.character_root}/{rel}"

    def ops_path(self, cap: CapabilityMeta) -> str | None:
        if not cap.ops_file:
            return None
        return f"{self.character_root}/{cap.ops_file}"

    def global_prompt_path(self, key: str) -> str | None:
        rel = (self.global_prompts.get(key) or "").strip()
        return rel or None

    def get_for_intent(self, intent: str) -> CapabilityMeta | None:
        key = (intent or "").strip().lower()
        if key == "add_son":
            key = "music"
        return self.intent_to_capability.get(key)

    def get_capability(self, cap_id: str) -> CapabilityMeta | None:
        return self.capabilities.get((cap_id or "").strip())

    def skill_catalog_for_judge(self) -> str:
        lines = ["【可用能力】"]
        seen: set[str] = set()
        order = ("music", "aicoin", "commit_user", "chat")
        by_intent = {
            c.intent: c for c in self.capabilities.values() if c.intent
        }
        for intent in order:
            cap = by_intent.get(intent)
            if not cap or intent in seen:
                continue
            seen.add(intent)
            lines.append(f"- {intent}: {cap.description}")
        for cap in self.capabilities.values():
            if not cap.intent or cap.intent in seen:
                continue
            seen.add(cap.intent)
            lines.append(f"- {cap.intent}: {cap.description}")
        return "\n".join(lines)


def _load_manifest_json(character_root: str) -> dict[str, Any]:
    path = get_abs_path(f"{character_root}/manifest.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"invalid manifest: {path}")
    return data


def _normalize_slug(slug: str | None) -> str:
    key = (slug or CHARACTER_SLUG).strip()
    return key or CHARACTER_SLUG


def load_character_registry(slug: str | None = None) -> CharacterSkillRegistry:
    slug = _normalize_slug(slug)
    character_root = f"skills/character-skill/{slug}"
    raw = _load_manifest_json(character_root)
    if (raw.get("slug") or "").strip() and raw.get("slug") != slug:
        logger.warning(
            "[skill_registry] manifest slug=%s differs from requested=%s",
            raw.get("slug"),
            slug,
        )

    root = (raw.get("character_root") or character_root).strip().rstrip("/")
    core = raw.get("core") or {}
    permanent = str(core.get("permanent") or "core/anchor.md").strip()
    openclaw_brief = str(core.get("openclaw_brief") or "core/openclaw_brief.md").strip()
    tavern_constant_raw = core.get("tavern_constant") or []
    tavern_constant: list[str] = []
    if isinstance(tavern_constant_raw, list):
        for item in tavern_constant_raw:
            rel = str(item).strip()
            if rel:
                tavern_constant.append(rel)
    if not tavern_constant:
        tavern_constant = ["core/relations.md", "core/personality.md"]
    global_prompts = {
        str(k): str(v).strip()
        for k, v in (raw.get("global_prompts") or {}).items()
        if str(v).strip()
    }
    lore_block = raw.get("lore") or {}
    lore_default = str(lore_block.get("default") or "lore/lacia_static.yaml").strip()

    capabilities: dict[str, CapabilityMeta] = {}
    intent_to_capability: dict[str, CapabilityMeta] = {}
    channel_files: dict[str, str] = {}

    for cap_id, spec in (raw.get("capabilities") or {}).items():
        if not isinstance(spec, dict):
            continue
        file_rel = str(spec.get("file") or "").strip()
        if not file_rel:
            continue
        intent_val = spec.get("intent")
        intent = str(intent_val).strip().lower() if intent_val else None
        desc = str(spec.get("description") or "").strip()
        if not desc and intent:
            desc = _DEFAULT_DESCRIPTIONS.get(intent, cap_id)
        elif not desc:
            desc = cap_id

        meta = CapabilityMeta(
            id=str(cap_id),
            description=desc,
            intent=intent,
            file=file_rel,
            tools_route=(
                str(spec["tools_route"]).strip()
                if spec.get("tools_route")
                else None
            ),
            ops_file=str(spec["ops"]).strip() if spec.get("ops") else None,
        )
        capabilities[cap_id] = meta

        if cap_id.startswith("channel_"):
            ch = cap_id[len("channel_") :]
            channel_files[ch] = file_rel
        elif intent:
            intent_to_capability[intent] = meta

    optional_specs = core.get("optional") or []
    optional_core: list[OptionalCoreMeta] = []
    for spec in optional_specs:
        meta = parse_optional_core_spec(spec)
        if meta:
            optional_core.append(meta)

    routable = frozenset(
        i
        for i in intent_to_capability
        if i in ("chat", "music", "aicoin", "commit_user", "publish_note", "bug")
    ) | frozenset({"add_son"} if "music" in intent_to_capability else set())

    return CharacterSkillRegistry(
        slug=slug,
        character_root=root,
        permanent_file=permanent,
        openclaw_brief_file=openclaw_brief,
        tavern_constant=tuple(tavern_constant),
        global_prompts=global_prompts,
        lore_default=lore_default,
        capabilities=capabilities,
        intent_to_capability=intent_to_capability,
        channel_files=channel_files,
        optional_core=tuple(optional_core),
        routable_intents=routable,
    )


@lru_cache(maxsize=4)
def get_registry(slug: str | None = None) -> CharacterSkillRegistry:
    return load_character_registry(slug)


def skill_catalog_for_judge(slug: str | None = None) -> str:
    return get_registry(slug).skill_catalog_for_judge()


def valid_intents(slug: str | None = None) -> frozenset[str]:
    return get_registry(slug).routable_intents

"""optional core 元数据解析（无 skill_registry 依赖，避免循环导入）。"""

from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_OPTIONAL: dict[str, dict] = {
    "core/profile.md": {
        "keys": (
            "你是谁",
            "我是谁",
            "蕾西亚是谁",
            "你叫什么",
            "叫什么名字",
            "你的身份",
            "介绍你自己",
            "自我介绍一下",
        ),
        "priority": 10,
    },
    "core/memory.md": {
        "keys": (
            "hie是什么",
            "hie 是什么",
            "什么是hie",
            "世界观",
            "米福雷",
            "beatless",
            "type-005",
            "黑色秘棺",
        ),
        "priority": 8,
    },
    "core/interaction.md": {
        "keys": ("笔记", "评论", "回复", "互动", "陪伴"),
        "intents": ("commit_user",),
        "priority": 11,
    },
    "core/conflicts.md": {
        "keys": ("打破设定", "出戏", "你是gpt", "你是 ai", "忽略设定"),
        "priority": 6,
    },
}


@dataclass(frozen=True)
class OptionalCoreMeta:
    file: str
    keys: tuple[str, ...] = ()
    intents: frozenset[str] = frozenset()
    constant: bool = False
    priority: int = 5


def parse_optional_core_spec(spec: str | dict) -> OptionalCoreMeta | None:
    if isinstance(spec, str):
        file_rel = spec.strip()
        if not file_rel:
            return None
        defaults = _DEFAULT_OPTIONAL.get(file_rel, {})
        keys = tuple(str(k).lower() for k in defaults.get("keys", ()))
        intents_raw = defaults.get("intents") or ()
        intents = frozenset(str(i).strip().lower() for i in intents_raw if str(i).strip())
        return OptionalCoreMeta(
            file=file_rel,
            keys=keys,
            intents=intents,
            constant=bool(defaults.get("constant", False)),
            priority=int(defaults.get("priority", 5)),
        )

    if not isinstance(spec, dict):
        return None
    file_rel = str(spec.get("file") or "").strip()
    if not file_rel:
        return None
    defaults = _DEFAULT_OPTIONAL.get(file_rel, {})
    keys_raw = spec.get("keys") if "keys" in spec else defaults.get("keys", ())
    keys = tuple(str(k).lower() for k in (keys_raw or ()) if str(k).strip())
    intents_raw = spec.get("intents") if "intents" in spec else defaults.get("intents", ())
    intents = frozenset(str(i).strip().lower() for i in (intents_raw or ()) if str(i).strip())
    return OptionalCoreMeta(
        file=file_rel,
        keys=keys,
        intents=intents,
        constant=bool(spec.get("constant", defaults.get("constant", False))),
        priority=int(spec.get("priority", defaults.get("priority", 5))),
    )

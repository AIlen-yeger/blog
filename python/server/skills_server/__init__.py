"""Skills 注册表与 prompt 组装（manifest 驱动）。

子模块请直接 import（如 prompt_assembler、prompt_trace），勿在本包 __init__ 里
提前拉 prompt_assembler，否则会与 prompt_skills 循环导入。
"""

from server.skills_server.optional_core import select_optional_core_files
from server.skills_server.optional_core_types import OptionalCoreMeta
from server.skills_server.skill_registry import (
    CHARACTER_SLUG,
    CapabilityMeta,
    CharacterSkillRegistry,
    get_registry,
    load_character_registry,
    skill_catalog_for_judge,
    valid_intents,
)

__all__ = [
    "CHARACTER_SLUG",
    "CapabilityMeta",
    "CharacterSkillRegistry",
    "OptionalCoreMeta",
    "get_registry",
    "load_character_registry",
    "select_optional_core_files",
    "skill_catalog_for_judge",
    "valid_intents",
]

"""校验 manifest 注册表、optional core 与 assemble_system_prompt。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    from server.prompt_skills import build_system_prompt
    from server.skills_server.optional_core import select_optional_core_files
    from server.skills_server.prompt_assembler import PromptContext, assemble_system_prompt
    from server.skills_server.skill_registry import get_registry, load_character_registry, skill_catalog_for_judge

    # 避免 @lru_cache 读到旧结构
    get_registry.cache_clear()
    reg = load_character_registry()

    assert reg.get_for_intent("music") is not None
    assert reg.get_for_intent("chat") is not None
    assert reg.channel_path("web")
    assert len(reg.optional_core) >= 1
    assert reg.permanent_file.endswith("anchor.md")
    assert any("voice_style" in p for p in reg.tavern_constant), reg.tavern_constant

    from server.skills_server.prompt_assembler import PromptAssembler

    qq_skills = build_system_prompt(
        intent="chat", channel="qq", user_message="你是谁", max_optional_core=1
    )
    assert "角色档案" in qq_skills or "profile" in qq_skills.lower()
    qq_generic = build_system_prompt(
        intent="chat", channel="qq", user_message="你好", max_optional_core=1
    )
    assert len(qq_generic) < len(qq_skills) * 1.2

    catalog = skill_catalog_for_judge()
    assert "【可用能力】" in catalog

    chat = build_system_prompt(intent="chat", channel="web", user_message="你好")
    assert len(chat) > 200
    assert "蕾西亚" in chat or "Lacia" in chat
    assert "纯对话" in chat or "chat_constraints" in chat.lower()
    assert "语气与说法" in chat or "voice_style" in str(reg.tavern_constant)
    assert "宿主能力索引" in chat
    assert "功能清单 · chat 路径（仅列举）" not in chat

    music = build_system_prompt(
        intent="music",
        channel="web",
        user_message="最近听了什么",
        user_logged_in=True,
    )
    assert "capabilities/chat.md" not in music
    assert "功能清单 · chat" not in music
    assert "听歌排行" in music or "QQ 音乐" in music

    note = build_system_prompt(
        intent="commit_user",
        channel="internal",
        user_message="【笔记标题】测试\n【笔记正文】今天心情不错",
    )
    assert len(note) > len(chat) * 0.5

    picked = select_optional_core_files(
        reg,
        intent="commit_user",
        haystack="开发者 笔记 回复",
        max_files=3,
    )
    assert any("interaction" in p for p in picked), picked

    assembled = assemble_system_prompt(
        PromptContext(
            intent="music",
            channel="web",
            user_message="加歌",
            include_lore=False,
            include_recall=False,
        ),
    )
    assert len(assembled) > 100

    print("skill_registry ok")
    print("permanent:", reg.permanent_file)
    print("tavern_constant:", reg.tavern_constant)
    print("optional_core picked (commit_user):", picked)


if __name__ == "__main__":
    main()

"""统一 system 拼装：skills（含 optional core）→ lore → recall。"""

from __future__ import annotations

from dataclasses import dataclass, replace

from server.embedding.embedding_user_memory import get_user_memory
from server.lore.lorebook import Lorebook
from server.prompt_skills import build_system_prompt, character_lore_path
from server.state import AgentState
from utils.judge_intent.quick_judge import should_skip_recall

_lorebooks: dict[str, Lorebook] = {}


def _get_lorebook(character_slug: str | None = None) -> Lorebook:
    path = character_lore_path(character_slug=character_slug)
    if path not in _lorebooks:
        _lorebooks[path] = Lorebook.load_yaml(path)
    return _lorebooks[path]


def build_recall_query(question: str, episode_summary: str) -> str:
    summary = (episode_summary or "").strip()
    if summary:
        return f"{summary}\n{question}".strip()
    return (question or "").strip()


@dataclass
class PromptContext:
    intent: str
    channel: str
    user_message: str
    user_id: int = 0
    user_logged_in: bool = False
    developer_name: str | None = None
    character_slug: str | None = None
    include_lore: bool = False
    include_recall: bool = False
    system_append: str = ""
    max_optional_core: int = 2
    recall_top_k: int | None = None  # None → 按渠道默认


class PromptAssembler:
    """OpenClaw 路由 + 酒馆式 optional core / lore / recall 注入。"""

    def build_system(self, ctx: PromptContext) -> str:
        ch = (ctx.channel or "web").strip().lower()
        intent = (ctx.intent or "chat").strip().lower()

        mem = get_user_memory()
        episode_summary = mem.get_episode(ctx.user_id).running_summary or ""

        system_prompt = build_system_prompt(
            intent=intent,
            user_logged_in=ctx.user_logged_in,
            channel=ch,
            developer_name=ctx.developer_name,
            character_slug=ctx.character_slug,
            user_message=ctx.user_message,
            episode_summary=episode_summary,
            max_optional_core=ctx.max_optional_core,
        )

        if ctx.include_lore:
            lore_block = _get_lorebook(ctx.character_slug).select(
                message=ctx.user_message,
                channel=ch,
                extra_text=episode_summary,
            )
            if lore_block:
                system_prompt += "\n\n---\n\n" + lore_block

        if ctx.include_recall and not should_skip_recall(
            message=ctx.user_message, intent=intent
        ):
            recall_query = build_recall_query(ctx.user_message, episode_summary)
            top_k = ctx.recall_top_k
            if top_k is None:
                top_k = 4 if ch == "qq" else 3
            recall_block = mem.format_recall_for_prompt(
                user_id=ctx.user_id,
                query=recall_query,
                top_k=top_k,
                channel=ch,
            )
            if recall_block:
                system_prompt += "\n\n---\n\n" + recall_block

        append = (ctx.system_append or "").strip()
        if append:
            system_prompt = "\n\n---\n\n".join(
                part for part in (system_prompt, append) if part
            )

        return system_prompt

    def build_chat_system(self, ctx: PromptContext) -> str:
        """闲聊：Web / QQ 均启用 lore + 长期记忆召回；QQ 仍用 lean 酒馆（见 prompt_skills）。"""
        ch = (ctx.channel or "web").strip().lower()
        is_qq = ch == "qq"
        return self.build_system(
            replace(
                ctx,
                include_lore=True,
                include_recall=True,
                max_optional_core=1 if is_qq else min(ctx.max_optional_core, 1),
            ),
        )


_default_assembler = PromptAssembler()


def assemble_system_prompt(ctx: PromptContext) -> str:
    """全路由统一入口（ReAct / chat / 笔记回复等）。"""
    return _default_assembler.build_system(ctx)


def assemble_chat_system(ctx: PromptContext) -> str:
    return _default_assembler.build_chat_system(ctx)


def prompt_context_from_state(
    state: AgentState,
    *,
    intent: str | None = None,
    include_lore: bool = False,
    include_recall: bool = False,
    system_append: str = "",
    max_optional_core: int = 2,
    user_message: str | None = None,
) -> PromptContext:
    return PromptContext(
        intent=(intent or state.get("intent") or "chat"),
        channel=(state.get("channel") or "web").strip().lower(),
        user_message=(user_message if user_message is not None else (state.get("question") or "")).strip(),
        user_id=int(state.get("user_id") or 0),
        user_logged_in=bool((state.get("access_token") or "").strip()),
        developer_name=(state.get("user_name") or "").strip() or None,
        include_lore=include_lore,
        include_recall=include_recall,
        system_append=system_append,
        max_optional_core=max_optional_core,
    )


def assemble_for_state(
    state: AgentState,
    *,
    intent: str | None = None,
    include_lore: bool = False,
    include_recall: bool = False,
    system_append: str = "",
    max_optional_core: int = 2,
    user_message: str | None = None,
) -> str:
    """ReAct / 笔记 / 定时任务等：从 AgentState 一次拼 system。"""
    return assemble_system_prompt(
        prompt_context_from_state(
            state,
            intent=intent,
            include_lore=include_lore,
            include_recall=include_recall,
            system_append=system_append,
            max_optional_core=max_optional_core,
            user_message=user_message,
        ),
    )

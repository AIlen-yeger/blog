"""组装提示词时的分层追踪（OpenClaw capability vs 酒馆 optional/lore/recall）。"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from server.embedding.embedding_user_memory import get_user_memory
from server.lore.lorebook import Lorebook
from server.prompt_skills import build_system_prompt, character_lore_path
from server.skills_server.optional_core import select_optional_core_files
from server.skills_server.prompt_assembler import PromptContext, build_recall_query
from server.skills_server.skill_registry import get_registry
from utils.judge_intent.quick_judge import (
    should_skip_memory_pipeline,
    should_skip_recall,
)


def estimate_tokens(text: str) -> tuple[int, str]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text or "")), "tiktoken/cl100k_base"
    except Exception:
        n = len(text or "")
        return max(1, int(n / 1.7)), "heuristic_chars/1.7"


def _message_text(msg: Any) -> str:
    """将 LangChain 消息压成可计 token 的文本（含 tool_calls / tool 返回）。"""
    from langchain_core.messages import AIMessage, ToolMessage

    parts: list[str] = []
    role = getattr(msg, "type", None) or msg.__class__.__name__
    parts.append(f"[{role}]")
    content = msg.content
    if content is not None:
        if isinstance(content, list):
            parts.append(json.dumps(content, ensure_ascii=False))
        else:
            parts.append(str(content))
    if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
        parts.append(json.dumps(msg.tool_calls, ensure_ascii=False))
    if isinstance(msg, ToolMessage):
        name = getattr(msg, "name", None) or ""
        if name:
            parts.append(f"tool={name}")
    return "\n".join(p for p in parts if p)


def estimate_messages_tokens(messages: list[Any]) -> dict[str, Any]:
    """估算 ReAct / 多轮对话消息列表的 token（本地 tiktoken，非账单精确值）。"""
    rows: list[dict[str, Any]] = []
    total = 0
    by_kind: dict[str, int] = {}
    for i, msg in enumerate(messages):
        text = _message_text(msg)
        tok, _ = estimate_tokens(text)
        total += tok
        kind = getattr(msg, "type", None) or msg.__class__.__name__
        by_kind[kind] = by_kind.get(kind, 0) + tok
        rows.append({"index": i, "kind": kind, "chars": len(text), "tokens": tok})
    _, method = estimate_tokens("")
    return {
        "total_tokens": total,
        "token_method": method,
        "by_kind": by_kind,
        "rows": rows,
    }


def estimate_tools_schema_tokens(tools: list[Any]) -> tuple[int, int]:
    """工具定义 JSON 体量（每轮 ReAct 请求会重复携带 bind_tools schema）。"""
    blobs: list[str] = []
    for t in tools:
        name = getattr(t, "name", None) or str(t)
        desc = getattr(t, "description", None) or ""
        schema = getattr(t, "args_schema", None)
        if schema is not None and hasattr(schema, "model_json_schema"):
            schema_txt = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        else:
            schema_txt = ""
        blobs.append(json.dumps({"name": name, "description": desc, "schema": schema_txt}, ensure_ascii=False))
    joined = "\n".join(blobs)
    tok, _ = estimate_tokens(joined)
    return tok, len(joined)


@dataclass
class LayerRecord:
    category: str  # openclaw | tavern | session
    name: str
    source: str
    chars: int
    tokens: int


@dataclass
class AssembleTrace:
    intent: str
    channel: str
    route_path: str
    include_lore: bool
    include_recall: bool
    skip_memory_pipeline: bool
    skip_recall: bool
    episode_summary_preview: str = ""
    openclaw_capabilities: list[str] = field(default_factory=list)
    tavern_optional_core: list[str] = field(default_factory=list)
    tavern_lore_hit: bool = False
    tavern_recall_hit: bool = False
    layers: list[LayerRecord] = field(default_factory=list)
    system_prompt: str = ""
    system_chars: int = 0
    system_tokens: int = 0
    token_method: str = ""
    timings_ms: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["layers"] = [asdict(x) for x in self.layers]
        return d


def _route_path_label(ctx: PromptContext) -> str:
    if ctx.include_lore and ctx.include_recall:
        return "skills_server.assemble_chat_system"
    if ctx.include_lore:
        return "skills_server.assemble_for_state(lore)"
    return "skills_server.assemble_for_state"


def _plan_prompt_layers(
    registry,
    *,
    intent_key: str,
    channel: str,
    user_message: str,
    episode_summary: str,
    user_logged_in: bool,
    max_optional_core: int,
) -> tuple[list[str], list[str]]:
    """返回 (tavern 层列表, openclaw 层列表)。"""
    from server.skills_server.prompt_layers import CAPABILITY_INTENTS, CHAT_LEAN_CHANNELS
    from server.skills_server.openclaw_capabilities import build_openclaw_stack
    from server.skills_server.tavern_persona import build_tavern_persona

    ch = (channel or "web").strip().lower()
    lean_chat = intent_key == "chat" and ch in CHAT_LEAN_CHANNELS
    minimal = lean_chat or intent_key in CAPABILITY_INTENTS
    _, tavern_loaded = build_tavern_persona(
        registry,
        intent=intent_key,
        channel=ch,
        user_message=user_message,
        episode_summary=episode_summary,
        max_optional_core=0 if minimal else max_optional_core,
        minimal=minimal,
        include_channel=True,
    )
    _, openclaw_loaded = build_openclaw_stack(
        registry,
        intent=intent_key,
        channel=ch,
        user_logged_in=user_logged_in,
        lean_chat=lean_chat,
    )
    if intent_key == "commit_user":
        openclaw_loaded = list(openclaw_loaded) + ["openclaw:session_context"]
    return tavern_loaded, openclaw_loaded


def trace_assemble(ctx: PromptContext) -> AssembleTrace:
    """分步计时并记录 OpenClaw / 酒馆 各层加载情况（不重复调用 LLM）。"""
    registry = get_registry(ctx.character_slug)
    intent = (ctx.intent or "chat").strip().lower()
    if intent == "add_son":
        intent = "music"
    ch = (ctx.channel or "web").strip().lower()
    msg = (ctx.user_message or "").strip()

    trace = AssembleTrace(
        intent=intent,
        channel=ch,
        route_path=_route_path_label(ctx),
        include_lore=ctx.include_lore,
        include_recall=ctx.include_recall,
        skip_memory_pipeline=should_skip_memory_pipeline(msg),
        skip_recall=should_skip_recall(message=msg, intent=intent),
    )

    t0 = time.perf_counter()
    mem = get_user_memory()
    episode_summary = mem.get_episode(ctx.user_id).running_summary or ""
    trace.episode_summary_preview = (episode_summary[:120] + "…") if len(episode_summary) > 120 else episode_summary
    trace.timings_ms["episode_read"] = round((time.perf_counter() - t0) * 1000, 2)

    tavern_layers, openclaw_layers = _plan_prompt_layers(
        registry,
        intent_key=intent,
        channel=ch,
        user_message=msg,
        episode_summary=episode_summary,
        user_logged_in=ctx.user_logged_in,
        max_optional_core=ctx.max_optional_core,
    )
    trace.openclaw_capabilities = list(openclaw_layers)
    trace.tavern_optional_core = [
        x for x in tavern_layers if x.startswith("tavern_optional:")
    ]
    if not trace.tavern_optional_core:
        trace.tavern_optional_core = [
            x.replace("tavern_constant:", "")
            for x in tavern_layers
            if x.startswith("tavern_constant:")
        ]

    t1 = time.perf_counter()
    optional = select_optional_core_files(
        registry,
        intent=intent,
        haystack=f"{msg}\n{episode_summary}",
        max_files=ctx.max_optional_core,
    )
    if not trace.tavern_optional_core:
        trace.tavern_optional_core = list(optional)
    trace.timings_ms["optional_core_select"] = round((time.perf_counter() - t1) * 1000, 2)

    t2 = time.perf_counter()
    base = build_system_prompt(
        intent=intent,
        user_logged_in=ctx.user_logged_in,
        channel=ch,
        developer_name=ctx.developer_name,
        character_slug=ctx.character_slug,
        user_message=msg,
        episode_summary=episode_summary,
        max_optional_core=ctx.max_optional_core,
    )
    trace.timings_ms["build_system_prompt"] = round((time.perf_counter() - t2) * 1000, 2)

    for rel in optional:
        trace.layers.append(
            LayerRecord(
                category="tavern",
                name=f"optional_core:{rel.split('/')[-1]}",
                source=f"{registry.character_root}/{rel}",
                chars=0,
                tokens=0,
            )
        )
    trace.layers.append(
        LayerRecord(
            category="openclaw",
            name="capabilities_stack",
            source="prompt_skills.build_system_prompt",
            chars=len(base),
            tokens=estimate_tokens(base)[0],
        )
    )

    system = base
    t3 = time.perf_counter()
    if ctx.include_lore:
        lore_path = character_lore_path(character_slug=ctx.character_slug)
        lb = Lorebook.load_yaml(lore_path)
        lore_block = lb.select(message=msg, channel=ch, extra_text=episode_summary)
        trace.tavern_lore_hit = bool(lore_block)
        if lore_block:
            system += "\n\n---\n\n" + lore_block
            trace.layers.append(
                LayerRecord(
                    category="tavern",
                    name="lorebook",
                    source=lore_path,
                    chars=len(lore_block),
                    tokens=estimate_tokens(lore_block)[0],
                )
            )
    trace.timings_ms["lore_select"] = round((time.perf_counter() - t3) * 1000, 2)

    t4 = time.perf_counter()
    if ctx.include_recall and not trace.skip_recall:
        rq = build_recall_query(msg, episode_summary)
        recall_block = mem.format_recall_for_prompt(
            user_id=ctx.user_id,
            query=rq,
            top_k=3,
            channel=ch,
        )
        trace.tavern_recall_hit = bool(recall_block)
        if recall_block:
            system += "\n\n---\n\n" + recall_block
            trace.layers.append(
                LayerRecord(
                    category="tavern",
                    name="chroma_recall",
                    source="UserMemory.format_recall_for_prompt",
                    chars=len(recall_block),
                    tokens=estimate_tokens(recall_block)[0],
                )
            )
    trace.timings_ms["recall_query"] = round((time.perf_counter() - t4) * 1000, 2)

    append = (ctx.system_append or "").strip()
    if append:
        system += "\n\n---\n\n" + append
        trace.layers.append(
            LayerRecord(
                category="openclaw",
                name="system_append",
                source="(caller)",
                chars=len(append),
                tokens=estimate_tokens(append)[0],
            )
        )

    trace.system_prompt = system
    trace.system_chars = len(system)
    trace.system_tokens, trace.token_method = estimate_tokens(system)
    trace.timings_ms["assemble_total"] = sum(
        trace.timings_ms.get(k, 0)
        for k in (
            "episode_read",
            "optional_core_select",
            "build_system_prompt",
            "lore_select",
            "recall_query",
        )
    )
    return trace


def trace_to_dict(trace: AssembleTrace, *, include_system_prompt: bool = False) -> dict[str, Any]:
    """默认不含全文 system（省报告体积）；需要时用 include_system_prompt=True。"""
    d = trace.to_dict()
    if include_system_prompt:
        d["system_prompt"] = trace.system_prompt
    return d


def trace_context_for_scenario(
    *,
    scenario_id: str,
    intent: str,
    channel: str,
    question: str,
    user_id: int = 0,
    user_logged_in: bool = False,
    developer_name: str | None = "开发者",
) -> PromptContext:
    """按场景 id 选择 assemble 策略（与 agent_entry 分支对齐）。"""
    intent_l = intent.strip().lower()
    include_lore = False
    include_recall = False

    if intent_l == "chat":
        include_lore = True
        include_recall = True
    elif intent_l == "commit_user":
        include_lore = True

    return PromptContext(
        intent=intent_l,
        channel=channel,
        user_message=question,
        user_id=user_id,
        user_logged_in=user_logged_in,
        developer_name=developer_name,
        include_lore=include_lore,
        include_recall=include_recall,
    )

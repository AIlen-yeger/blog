"""QQ 渠道 AiCoin：① 轻量 ReAct 采集 JSON → ② chat 模型润色为 Kohaku 口语。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from server.agent import ChatModel
from server.prompt_skills import read_prompt
from server.qq_reply_format import qq_aicoin_max_rounds
from server.route_graph.react_subgraph import (
    compile_react_graph,
    count_tool_rounds,
    extract_final_answer,
)
from server.state import AgentState
from server.tools.aicoin_agent_tools import build_aicoin_tools
from service.chat_history import ChatHistoryService
from utils.ahr999 import (
    backfill_facts_from_tools,
    enrich_facts_with_ahr999,
    tool_texts_from_messages,
)
from utils.trace_log import log_event, preview, span

logger = logging.getLogger(__name__)


def _env_two_phase_enabled() -> bool:
    from config.config import _env_bool, ensure_env_loaded

    ensure_env_loaded()
    return _env_bool("QQ_AICOIN_TWO_PHASE", True)


def _build_qq_data_messages(state: AgentState) -> list:
    """数据采集阶段：无闲聊历史，只要工具 + JSON。"""
    question = (state.get("question") or "").strip()
    system = read_prompt("prompt/skills/aicoin_qq_data.md")
    return [
        SystemMessage(content=system),
        HumanMessage(content=question or "查询行情"),
    ]


def parse_market_facts_json(text: str) -> dict[str, Any]:
    """从 ReAct 最终输出解析 JSON；失败则包一层 raw。"""
    raw = (text or "").strip()
    if not raw:
        return {"parse_ok": False, "error": "empty", "raw": ""}

    candidates = [raw]
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if fence:
        candidates.insert(0, fence.group(1).strip())
    brace = re.search(r"\{[\s\S]*\}", raw)
    if brace:
        candidates.insert(0, brace.group(0))

    for piece in candidates:
        try:
            data = json.loads(piece)
            if isinstance(data, dict):
                data["parse_ok"] = True
                return data
        except json.JSONDecodeError:
            continue

    return {"parse_ok": False, "raw": raw[:2000]}


def format_facts_block(facts: dict[str, Any]) -> str:
    return "[行情数据-只读]\n" + json.dumps(facts, ensure_ascii=False)


def _run_data_collect(state: AgentState) -> tuple[dict[str, Any], list]:
    question = (state.get("question") or "").strip()
    tools = build_aicoin_tools(channel="qq", question=question)
    if not tools:
        return {"parse_ok": False, "error": "mcp_disabled"}, []

    max_rounds = qq_aicoin_max_rounds(question)
    graph = compile_react_graph(
        tools=tools,
        build_initial_messages=_build_qq_data_messages,
        subgraph="aicoin_qq_data",
        max_rounds=max_rounds,
    )

    with span("react", subgraph="aicoin_qq_data", max_rounds=max_rounds):
        result = graph.invoke({**state, "messages": []})
    messages = result.get("messages") or []
    final = extract_final_answer(messages) or ""
    facts = parse_market_facts_json(final)
    question = (state.get("question") or "").strip()
    tool_texts = tool_texts_from_messages(messages)
    facts = backfill_facts_from_tools(
        facts,
        tool_texts,
        raw_final=final,
        question=question,
    )
    facts = enrich_facts_with_ahr999(facts, tool_texts, question)
    log_event(
        "qq.aicoin.data_done",
        parse_ok=facts.get("parse_ok"),
        ahr999_ok=facts.get("ahr999_ok"),
        ahr999=facts.get("ahr999"),
        ahr999_note=facts.get("ahr999_note"),
        ahr999_kline_bars=facts.get("ahr999_kline_bars"),
        ahr999_kline_source=facts.get("ahr999_kline_source"),
        rounds=count_tool_rounds(messages),
        tools=len(tools),
        facts_preview=preview(json.dumps(facts, ensure_ascii=False), 400),
    )
    return facts, messages


def _run_chat_polish(
    state: AgentState,
    facts: dict[str, Any],
    chat_model: ChatModel,
) -> str:
    question = (state.get("question") or "").strip()
    developer = (state.get("user_name") or "").strip() or None
    from server.prompt_skills import build_system_prompt

    system = build_system_prompt(
        intent="chat",
        channel="qq",
        developer_name=developer,
    )
    polish_rules = read_prompt("prompt/skills/aicoin_qq.md")
    system = "\n\n---\n\n".join(p for p in (system, polish_rules) if p)

    limit = min(int(state.get("limit") or 4), 4)
    history = []
    session_id = state.get("session_id") or ""
    user_id = int(state.get("user_id") or 0)
    if session_id and user_id and limit > 0:
        history = ChatHistoryService().get_recent_history(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
        )

    ahr999_rule = (
        "若 JSON 含 ahr999 且 ahr999_ok 为 true，可口语提 ahr999 与 ahr999_zone_cn；"
        "若无 ahr999 或 ahr999_ok 为 false，禁止编造 AHR999 数值或 0.45/1.2 区间结论。"
    )
    human = (
        f"用户原话：{question}\n\n"
        f"{format_facts_block(facts)}\n\n"
        "请根据以上**只读**行情数据，用 Kohaku 在 QQ 里的口语回复用户。"
        "数字不得修改或编造；无 Markdown 列表；1～3 句、约 80 字内。"
        f"{ahr999_rule}"
    )
    messages = [
        SystemMessage(content=system),
        *ChatModel._to_lc_messages(history),
        HumanMessage(content=human),
    ]

    with span("qq.aicoin.polish"):
        answer = chat_model.invoke_messages_once(messages)

    log_event(
        "qq.aicoin.polish_done",
        answer_preview=preview(answer, 200),
        model=chat_model.model,
    )
    return answer or "嗯…我这边没组织好说法，你要不稍后再问一次？"


def run_aicoin_qq_two_phase(state: AgentState, chat_model: ChatModel) -> dict:
    """QQ 专用：数据 ReAct + chat 润色。"""
    question = (state.get("question") or "").strip()
    if not question:
        return {"final_answer": "先说一下你想查哪类行情呀～"}

    try:
        facts, _data_msgs = _run_data_collect(state)
        if facts.get("error") == "mcp_disabled":
            return {
                "final_answer": "行情查询功能未开启，请检查 AICOIN_MCP_ENABLED。",
            }

        final = _run_chat_polish(state, facts, chat_model)

        session_id = state.get("session_id") or ""
        user_id = int(state.get("user_id") or 0)
        if session_id:
            ChatHistoryService().save_turn(
                session_id=session_id,
                user_id=user_id,
                user_question=question,
                assistant_answer=final,
            )
            log_event("history.saved", session_id=session_id, channel="qq_aicoin")

        return {
            "final_answer": final,
            "market_facts": facts,
            "pipeline": "qq_two_phase",
        }
    except Exception:
        logger.exception("[aicoin] qq two-phase failed session_id=%s", state.get("session_id"))
        log_event("react.error", subgraph="aicoin_qq", level=logging.ERROR)
        return {"final_answer": "行情助手暂时不可用，请稍后再试。"}

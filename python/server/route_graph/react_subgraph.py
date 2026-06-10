"""ReAct 子图公共能力：模型绑定、工具节点、轮次统计、图编译。"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from config.config import AgentConfig
from server.state import AgentState
from utils.log.token_usage import record_from_response
from utils.log.trace_log import log_event, preview, redact_args, span, tool_result_status

logger = logging.getLogger(__name__)

DEFAULT_MAX_REACT_ROUNDS = 6


def effective_max_react_rounds(default: int = DEFAULT_MAX_REACT_ROUNDS) -> int:
    """测试时可设环境变量 TEST_REACT_MAX_ROUNDS 压低 ReAct 轮次（防 token 爆炸）。"""
    raw = (os.getenv("TEST_REACT_MAX_ROUNDS") or "").strip()
    if raw.isdigit():
        return max(1, min(12, int(raw)))
    return default


def _tool_call_name(tc: Any) -> str:
    if isinstance(tc, dict):
        return str(tc.get("name") or "unknown")
    return str(getattr(tc, "name", None) or "unknown")


def _tool_call_args(tc: Any) -> Any:
    if isinstance(tc, dict):
        return tc.get("args") or {}
    return getattr(tc, "args", None) or {}


def build_bound_model(tools: list) -> Any:
    """ReAct 用模型（默认 DeepSeek）+ bind_tools。"""
    cfg = AgentConfig()
    llm = ChatOpenAI(
        model=cfg.react_model_name,
        base_url=cfg.react_base_url,
        api_key=cfg.react_api_key,
        temperature=cfg.react_temperature,
        timeout=90,
        max_retries=1,
        stream_usage=True,
    )
    return llm.bind_tools(tools)


def count_tool_rounds(messages: list[AnyMessage]) -> int:
    """记录工具调用轮次"""
    return sum(
        1
        for m in messages
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
    )


def extract_final_answer(messages: list[AnyMessage]) -> str:
    """取最后一条无 tool_calls 的 AI 文本。"""
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        if getattr(msg, "tool_calls", None):
            continue
        text = (msg.content or "").strip()
        if text:
            return text
    return ""


def make_logging_tool_node(tools: list, *, subgraph: str) -> Callable[[AgentState], dict]:
    """带 tool.start / tool.end 的 ToolNode。"""
    base = ToolNode(tools)

    def node(state: AgentState) -> dict:
        last = state.get("messages") or []
        pending = []
        if last and isinstance(last[-1], AIMessage):
            pending = getattr(last[-1], "tool_calls", None) or []

        t0 = time.perf_counter()
        out = base.invoke(state)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        tool_msgs = out.get("messages") or []
        for i, tm in enumerate(tool_msgs):
            name = _tool_call_name(pending[i]) if i < len(pending) else "unknown"
            raw = getattr(tm, "content", "") or ""
            text = raw if isinstance(raw, str) else str(raw)
            ok, tool_log_level = tool_result_status(text)
            log_event(
                "tool.end",
                tool_log_level,
                subgraph=subgraph,
                tool=name,
                ok=ok,
                result_preview=preview(text, 400),
                duration_ms=elapsed_ms if i == 0 else None,
            )
        return out

    return node


def make_route_after_agent(*, subgraph: str, max_rounds: int = DEFAULT_MAX_REACT_ROUNDS):
    def _route(state: AgentState) -> str:
        msgs = state.get("messages") or []
        rounds = count_tool_rounds(msgs)
        if rounds >= max_rounds:
            log_event(
                "react.route",
                subgraph=subgraph,
                decision="__end__",
                reason="max_rounds",
                rounds=rounds,
            )
            return "__end__"
        decision = tools_condition(state)
        log_event("react.route", subgraph=subgraph, decision=decision, rounds=rounds)
        return decision

    return _route


def make_react_agent_node(
    *,
    subgraph: str,
    model: Any,
    build_initial_messages: Callable[[AgentState], list[BaseMessage]],
    llm_event: str | None = None,
    llm_result_event: str | None = None,
) -> Callable[[AgentState], dict]:
    """通用 agent 节点：无 messages 时用 build_initial_messages 初始化。"""

    ev_llm = llm_event or f"{subgraph}.react.llm"
    ev_result = llm_result_event or f"{subgraph}.react.llm.result"

    def node(state: AgentState) -> dict:
        msgs = list(state.get("messages") or [])
        if not msgs:
            msgs = build_initial_messages(state)

        round_no = count_tool_rounds(msgs) + 1
        with span(ev_llm, subgraph=subgraph, round=round_no, message_count=len(msgs)):
            ai_msg = model.invoke(msgs)

        record_from_response(
            phase=f"{subgraph}.react",
            model=AgentConfig().react_model_name,
            messages=msgs,
            response=ai_msg,
            trace_id=(state.get("trace_id") or None),
            subgraph=subgraph,
            round=round_no,
        )

        tool_calls = getattr(ai_msg, "tool_calls", None) or []
        for tc in tool_calls:
            log_event(
                "tool.start",
                subgraph=subgraph,
                tool=_tool_call_name(tc),
                args_preview=preview(str(redact_args(_tool_call_args(tc)))),
            )

        log_event(
            ev_result,
            subgraph=subgraph,
            round=round_no,
            has_tool_calls=bool(tool_calls),
            tool_names=[_tool_call_name(tc) for tc in tool_calls],
            content_preview=preview(str(ai_msg.content)),
        )
        return {"messages": [ai_msg]}

    return node


def compile_react_graph(
    *,
    tools: list,
    build_initial_messages: Callable[[AgentState], list[BaseMessage]],
    subgraph: str,
    max_rounds: int = DEFAULT_MAX_REACT_ROUNDS,
) -> Any:
    """START → agent ↔ tools → END 的标准 ReAct 子图。"""
    model = build_bound_model(tools)
    g = StateGraph(AgentState)
    g.add_node(
        "agent",
        make_react_agent_node(
            subgraph=subgraph,
            model=model,
            build_initial_messages=build_initial_messages,
        ),
    )
    g.add_node("tools", make_logging_tool_node(tools, subgraph=subgraph))
    g.add_edge(START, "agent")
    g.add_conditional_edges(
        "agent",
        make_route_after_agent(subgraph=subgraph, max_rounds=max_rounds),
        {"tools": "tools", "__end__": END},
    )
    g.add_edge("tools", "agent")
    return g.compile()

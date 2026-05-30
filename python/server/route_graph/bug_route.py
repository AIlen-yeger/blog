"""Bug 运维子 ReAct：日志排查 + incident 记录。"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from config.config import AgentConfig
from database.mysql.mysql_db import MysqlRepo
from server.agent import ChatModel
from server.prompt_skills import build_system_prompt
from server.route_graph.music_route import (
    _build_bound_model,
    _count_tool_rounds,
    _extract_final_answer,
    make_logging_tool_node,
)
from server.state import AgentState
from server.tools.bug_agent_tools import build_bug_tools
from service.chat_history import ChatHistoryService
from utils.trace_log import bind_trace, log_event, new_trace_id, preview, span

_DEFAULT_HISTORY_LIMIT = AgentConfig().history_limit
MAX_REACT_ROUNDS = 6


def _resolve_bug_ids(state: AgentState) -> tuple[str, str]:
    """返回 (incident_id, bug_session_id)，与 trace 绑定、与普通 chat 隔离。"""
    trace_id = (state.get("trace_id") or "").strip()
    if not trace_id or trace_id == "-":
        trace_id = new_trace_id()
    incident_id = (state.get("incident_id") or "").strip() or f"bug_inc_{trace_id}"
    bug_session_id = (state.get("bug_session_id") or "").strip() or incident_id
    return incident_id, bug_session_id


def _build_initial_messages(state: AgentState) -> list:
    """Bug Ops 系统提示 + 本 incident 排查历史 + 系统任务正文。"""
    system = build_system_prompt(intent="bug", user_logged_in=False)
    _, bug_session_id = _resolve_bug_ids(state)

    msgs: list = [SystemMessage(content=system)]
    limit = int(state.get("limit") or _DEFAULT_HISTORY_LIMIT)
    if bug_session_id:
        history_rows = ChatHistoryService().get_bug_history(
            session_id=bug_session_id,
            limit=limit,
        )
        msgs.extend(ChatModel._to_lc_messages(history_rows))

    msgs.append(HumanMessage(content=state.get("question") or ""))
    return msgs


def bug_agent_node(state: AgentState, *, model) -> dict:
    msgs = list(state.get("messages") or [])
    if not msgs:
        msgs = _build_initial_messages(state)

    round_no = _count_tool_rounds(msgs) + 1
    with span("bug.react.llm", round=round_no, message_count=len(msgs)):
        ai_msg = model.invoke(msgs)

    tool_calls = getattr(ai_msg, "tool_calls", None) or []
    log_event(
        "bug.react.llm.result",
        round=round_no,
        has_tool_calls=bool(tool_calls),
        tool_names=[tc.get("name") for tc in tool_calls],
        content_preview=preview(str(ai_msg.content)),
    )
    return {"messages": [ai_msg]}


def _route_after_agent(state: AgentState) -> str:
    msgs = state.get("messages") or []
    rounds = _count_tool_rounds(msgs)
    if rounds >= MAX_REACT_ROUNDS:
        log_event("bug.route", decision="__end__", reason="max_rounds", rounds=rounds)
        return "__end__"
    decision = tools_condition(state)
    log_event("bug.route", decision=decision, rounds=rounds)
    return decision


@lru_cache(maxsize=8)
def compile_bug_react_graph(mode: str = "general"):
    tools = build_bug_tools(mode=mode)
    model = _build_bound_model(tools)

    def agent_node(state: AgentState) -> dict:
        return bug_agent_node(state, model=model)

    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", make_logging_tool_node(tools))
    g.add_edge(START, "agent")
    g.add_conditional_edges(
        "agent",
        _route_after_agent,
        {"tools": "tools", "__end__": END},
    )
    g.add_edge("tools", "agent")
    return g.compile()


def _save_bug_turn(
    state: AgentState,
    *,
    question: str,
    final: str,
    incident_id: str,
    bug_session_id: str,
) -> dict:
    user_id = int(state.get("user_id") or 0)
    if bug_session_id:
        ChatHistoryService().save_bug_turn(
            session_id=bug_session_id,
            user_id=user_id,
            incident_id=incident_id,
            user_question=question,
            assistant_answer=final,
        )
        log_event(
            "history.saved",
            session_id=bug_session_id,
            incident_id=incident_id,
            channel="bug",
        )
    return {"final_answer": final}


def run_bug_react(state: AgentState) -> dict:
    """Bug Ops 内部 ReAct 入口（定时巡检 / 错误告警 / 运维手动触发）。"""
    bind_trace(
        trace_id=state.get("trace_id") or None,
        session_id=state.get("session_id") or None,
        user_id=int(state.get("user_id") or 0),
        intent="bug",
    )

    question = (state.get("question") or "").strip()
    if not question:
        log_event("bug.skip", reason="empty_task")
        return {"final_answer": "empty task"}

    incident_id, bug_session_id = _resolve_bug_ids(state)
    log_event(
        "bug.context",
        incident_id=incident_id,
        bug_session_id=bug_session_id,
        trace_id=state.get("trace_id"),
    )
    source = (state.get("source") or state.get("trigger") or "log_alert").strip()
    MysqlRepo().ensure_incident(
        incident_id=incident_id,
        session_id=bug_session_id,
        trace_id=(state.get("trace_id") or "").strip() or None,
        user_id=int(state.get("user_id") or 0),
        symptoms=preview(question, 500),
        source=source,
    )

    messages: list = []
    with span("bug.react", incident_id=incident_id):
        try:
            graph = compile_bug_react_graph("general")
            result = graph.invoke(
                {
                    **state,
                    "incident_id": incident_id,
                    "bug_session_id": bug_session_id,
                }
            )
            messages = result.get("messages") or []
        except Exception:
            log_event("bug.error", incident_id=incident_id, level=logging.ERROR)
            return {"final_answer": "运维助手处理失败，请稍后重试或查看 error.jsonl。"}

    final = _extract_final_answer(messages) or "排查完成。"
    rounds = _count_tool_rounds(messages)
    log_event(
        "bug.done",
        rounds=rounds,
        final_preview=preview(final),
        incident_id=incident_id,
        message_count=len(messages),
    )
    return {
        **_save_bug_turn(
            state,
            question=question,
            final=final,
            incident_id=incident_id,
            bug_session_id=bug_session_id,
        ),
        "messages": messages,
        "incident_id": incident_id,
        "bug_session_id": bug_session_id,
    }

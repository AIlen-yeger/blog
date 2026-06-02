"""Bug 运维子 ReAct：日志排查 + incident 记录。"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage

from config.config import AgentConfig
from database.mysql.mysql_db import MysqlRepo
from server.agent import ChatModel
from server.prompt_skills import build_system_prompt
from server.route_graph.react_subgraph import (
    DEFAULT_MAX_REACT_ROUNDS,
    compile_react_graph,
    count_tool_rounds,
    extract_final_answer,
)
from server.state import AgentState
from server.tools.bug_agent_tools import build_bug_tools
from service.chat_history import ChatHistoryService
from utils.trace_log import bind_trace, log_event, new_trace_id, preview, span

_DEFAULT_HISTORY_LIMIT = AgentConfig().history_limit


def _resolve_bug_ids(state: AgentState) -> tuple[str, str]:
    trace_id = (state.get("trace_id") or "").strip()
    if not trace_id or trace_id == "-":
        trace_id = new_trace_id()
    incident_id = (state.get("incident_id") or "").strip() or f"bug_inc_{trace_id}"
    bug_session_id = (state.get("bug_session_id") or "").strip() or incident_id
    return incident_id, bug_session_id


def _build_initial_messages(state: AgentState) -> list:
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


@lru_cache(maxsize=8)
def _bug_react_graph(mode: str = "general"):
    return compile_react_graph(
        tools=build_bug_tools(mode=mode),
        build_initial_messages=_build_initial_messages,
        subgraph="bug",
        max_rounds=DEFAULT_MAX_REACT_ROUNDS,
    )


def run_bug_react(state: AgentState) -> dict:
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

    payload = {**state, "incident_id": incident_id, "bug_session_id": bug_session_id}
    try:
        with span("react", subgraph="bug"):
            result = _bug_react_graph("general").invoke(payload)
        messages = result.get("messages") or []
    except Exception:
        log_event("bug.error", incident_id=incident_id, level=logging.ERROR)
        return {"final_answer": "运维助手处理失败，请稍后重试或查看 error.jsonl。"}

    final = extract_final_answer(messages) or "排查完成。"
    log_event(
        "bug.done",
        rounds=count_tool_rounds(messages),
        final_preview=preview(final),
        incident_id=incident_id,
        message_count=len(messages),
    )

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

    return {
        "final_answer": final,
        "messages": messages,
        "incident_id": incident_id,
        "bug_session_id": bug_session_id,
    }

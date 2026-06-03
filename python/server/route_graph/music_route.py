"""Music 意图子 ReAct：由 run_music_react 对外暴露。"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from config.config import AgentConfig
from server.agent import ChatModel
from server.prompt_skills import build_system_prompt
from server.route_graph.react_subgraph import (
    DEFAULT_MAX_REACT_ROUNDS,
    compile_react_graph,
    count_tool_rounds,
    extract_final_answer,
)
from server.state import AgentState
from server.tools.music_agent_tools import build_music_tools, detect_music_task_mode
from service.chat_history import ChatHistoryService
from utils.trace_log import bind_trace, log_event, preview, span

_DEFAULT_HISTORY_LIMIT = AgentConfig().history_limit
logger = logging.getLogger(__name__)


def _build_initial_messages(state: AgentState) -> list:
    logged_in = bool((state.get("access_token") or "").strip())
    system = build_system_prompt(
        intent="music",
        user_logged_in=logged_in,
        channel=(state.get("channel") or "web").strip().lower(),
        developer_name=(state.get("user_name") or "").strip() or None,
    )
    msgs: list = [SystemMessage(content=system)]
    session_id = state.get("session_id") or ""
    user_id = int(state.get("user_id") or 0)
    limit = int(state.get("limit") or _DEFAULT_HISTORY_LIMIT)
    if session_id and user_id:
        history_rows = ChatHistoryService().get_recent_history(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
        )
        msgs.extend(ChatModel._to_lc_messages(history_rows))
    msgs.append(HumanMessage(content=state.get("question") or ""))
    return msgs


def run_music_react(state: AgentState) -> dict:
    bind_trace(
        trace_id=state.get("trace_id") or None,
        session_id=state.get("session_id") or None,
        user_id=int(state.get("user_id") or 0),
        intent="music",
    )

    question = (state.get("question") or "").strip()
    if not question:
        log_event("react.skip", subgraph="music", reason="empty_question")
        return {"final_answer": "请先描述你的音乐相关需求。"}

    token = (state.get("access_token") or "").strip()
    mode = detect_music_task_mode(question)
    graph = compile_react_graph(
        tools=build_music_tools(token, mode=mode),
        build_initial_messages=_build_initial_messages,
        subgraph="music",
        max_rounds=DEFAULT_MAX_REACT_ROUNDS,
    )

    try:
        with span("react", subgraph="music"):
            result = graph.invoke(state)
        messages = result.get("messages") or []
    except Exception:
        logger.exception("[music] react failed session_id=%s", state.get("session_id"))
        log_event("react.error", subgraph="music", level=logging.ERROR)
        return {"final_answer": "音乐助手暂时不可用，请稍后再试。"}

    final = extract_final_answer(messages) or "处理完成。"
    log_event(
        "react.done",
        subgraph="music",
        rounds=count_tool_rounds(messages),
        final_preview=preview(final),
        message_count=len(messages),
    )

    session_id = state.get("session_id") or ""
    user_id = int(state.get("user_id") or 0)
    if session_id:
        ChatHistoryService().save_turn(
            session_id=session_id,
            user_id=user_id,
            user_question=question,
            assistant_answer=final,
        )
        log_event("history.saved", session_id=session_id, channel="music")

    return {"final_answer": final, "messages": messages}

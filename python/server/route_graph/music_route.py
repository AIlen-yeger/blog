"""Music 意图子 ReAct：由 run_music_react 对外暴露。"""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from config.config import AgentConfig
from server.agent import ChatModel
from server.skills_server.prompt_assembler import assemble_for_state
from server.route_graph.react_subgraph import (
    effective_max_react_rounds,
    compile_react_graph,
    count_tool_rounds,
    extract_final_answer,
)
from server.state import AgentState
from server.tools.music_agent_tools import build_music_tools, detect_music_task_mode
from service.chat_history import ChatHistoryService
from utils.log.token_usage import log_prompt_assembled, record_react_conversation, request_token_summary_fields
from utils.log.trace_log import bind_trace, log_event, preview, span

_DEFAULT_HISTORY_LIMIT = AgentConfig().history_limit
logger = logging.getLogger(__name__)

_WEB_MUSIC_PRESENT_APPEND = """【Web 桌宠 · 转述工具结果】
以蕾西亚第一人称口语转述，约 1～3 句；禁止 Markdown 表格/列表/标题/奖牌 emoji；歌名与次数融入句子即可。语气见 core/prompt.md，勿写成客服清单。"""


def _rank_rows_from_messages(messages: list) -> list[str]:
    rows: list[str] = []
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        raw = msg.content
        text = raw if isinstance(raw, str) else str(raw or "")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, list):
            continue
        for item in data[:5]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "").strip()
            if not title:
                continue
            artist = str(item.get("artist") or "").strip()
            count = item.get("weeklyPlayCount", item.get("playCount"))
            if artist and count is not None:
                rows.append(f"《{title}》{artist} {count} 次")
            elif artist:
                rows.append(f"《{title}》{artist}")
            else:
                rows.append(f"《{title}》")
    return rows


def _polish_web_music_answer(final: str, messages: list) -> str:
    """Web 桌宠：去掉 Markdown 表格，用口语短句转述排行（数据仍来自 tool）。"""
    if "|" not in final and "🥇" not in final and "🥈" not in final:
        return final
    ranks = _rank_rows_from_messages(messages)
    if not ranks:
        return final

    if len(ranks) == 1:
        body = f"近一周听得最多的是 {ranks[0]}。"
    elif len(ranks) == 2:
        body = f"近一周你常听的是 {ranks[0]}，以及 {ranks[1]}。"
    else:
        body = f"近一周听得比较多的是 {'、'.join(ranks[:3])}。"

    closing = ""
    for line in final.splitlines():
        s = line.strip()
        if not s or s.startswith("|") or set(s) <= {"|", "-", ":", " "}:
            continue
        if "？" in s or "吗" in s:
            closing = s
            break
    if not closing:
        closing = "若想了解某首的背景，或要把新歌加进歌单，告诉我即可。"
    return body + closing


def _build_initial_messages(state: AgentState) -> list:
    channel = (state.get("channel") or "web").strip().lower()
    append = _WEB_MUSIC_PRESENT_APPEND if channel == "web" else ""
    system = assemble_for_state(state, intent="music", system_append=append)
    log_prompt_assembled(
        phase="music",
        system_prompt=system,
        intent="music",
        channel=channel,
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
        max_rounds=effective_max_react_rounds(),
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
    ch = (state.get("channel") or "web").strip().lower()
    if ch == "web":
        final = _polish_web_music_answer(final, messages)
    rounds = count_tool_rounds(messages)
    record_react_conversation(
        subgraph="music",
        model=AgentConfig().react_model_name,
        messages=messages,
        tool_rounds=rounds,
    )
    log_event(
        "react.done",
        subgraph="music",
        rounds=rounds,
        final_preview=preview(final),
        message_count=len(messages),
        **request_token_summary_fields(state.get("trace_id") or None),
    )

    session_id = state.get("session_id") or ""
    user_id = int(state.get("user_id") or 0)
    ch = (state.get("channel") or "web").strip().lower()
    if session_id:
        ChatHistoryService().save_turn(
            session_id=session_id,
            user_id=user_id,
            user_question=question,
            assistant_answer=final,
            channel=ch,
        )
        log_event("history.saved", session_id=session_id, channel=ch)

    return {"final_answer": final, "messages": messages}

"""Music 意图子 ReAct：agent ↔ tools 循环，由 run_music_react 对外暴露。"""

from __future__ import annotations

import json
import logging
import time
from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from config.config import AgentConfig
from server.agent import ChatModel
from server.prompt_skills import build_system_prompt
from server.state import AgentState
from server.tools.music_agent_tools import build_music_tools, detect_music_task_mode
from service.chat_history import ChatHistoryService
from utils.qq.qq_music_tools import (
    parse_qq_share_with_meta,
    save_music_track,
)
from utils.trace_log import (
    answer_log_fields,
    bind_trace_from_state,
    log_event,
    preview,
    record_model,
    redact_args,
    run_in_trace_context,
    span,
    tool_result_status,
)

_DEFAULT_HISTORY_LIMIT = AgentConfig().history_limit

logger = logging.getLogger(__name__)

MAX_REACT_ROUNDS = 6


def _react_model_name() -> str:
    return AgentConfig().react_model_name


def _build_bound_model(tools: list):
    cfg = AgentConfig()
    llm = ChatOpenAI(
        model=cfg.react_model_name,
        base_url=cfg.react_base_url,
        api_key=cfg.react_api_key,
        temperature=cfg.react_temperature,
        timeout=90,
        max_retries=1,
    )
    return llm.bind_tools(tools)


def _execute_model_name() -> str:
    """日志兼容：ReAct 实际模型名。"""
    return _react_model_name()


def _count_tool_rounds(messages: list) -> int:
    return sum(
        1
        for m in messages
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
    )


def _build_initial_messages(state: AgentState, *, task_mode: str = "general") -> list:
    """角色设定 + 音乐技能（按需）+ 会话历史 + 当前问题。"""
    logged_in = bool((state.get("access_token") or "").strip())
    system = build_system_prompt(intent="music", user_logged_in=logged_in)

    msgs: list = [SystemMessage(content=system)]

    session_id = state.get("session_id") or ""
    user_id = int(state.get("user_id") or 0)
    limit = int(state.get("limit") or _DEFAULT_HISTORY_LIMIT)
    if task_mode == "add":
        limit = min(limit, 2)
    if session_id:
        history_rows = ChatHistoryService().get_recent_history(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
        )
        msgs.extend(ChatModel._to_lc_messages(history_rows))

    msgs.append(HumanMessage(content=state.get("question") or ""))
    return msgs


def music_agent_node(state: AgentState, *, model, task_mode: str = "general") -> dict:
    """ReAct 中的模型节点：决定直接回复或发起 tool_calls。"""
    msgs = list(state.get("messages") or [])
    if not msgs:
        msgs = _build_initial_messages(state, task_mode=task_mode)

    round_no = _count_tool_rounds(msgs) + 1
    model_name = _execute_model_name()
    record_model(model_name)
    with span("react.llm", round=round_no, message_count=len(msgs), model=model_name):
        ai_msg = model.invoke(msgs)

    tool_calls = getattr(ai_msg, "tool_calls", None) or []
    log_event(
        "react.llm.result",
        round=round_no,
        model=model_name,
        has_tool_calls=bool(tool_calls),
        tool_names=[tc.get("name") for tc in tool_calls],
        content_preview=preview(str(ai_msg.content)),
    )
    return {"messages": [ai_msg]}


def _route_after_agent(state: AgentState) -> str:
    msgs = state.get("messages") or []
    rounds = _count_tool_rounds(msgs)
    if rounds >= MAX_REACT_ROUNDS:
        log_event("react.route", decision="__end__", reason="max_rounds", rounds=rounds)
        return "__end__"
    decision = tools_condition(state)
    log_event("react.route", decision=decision, rounds=rounds)
    return decision


@lru_cache(maxsize=128)
def compile_music_react_graph(access_token: str, mode: str = "general"):
    """按 access_token 与任务模式编译子图（token / 模式不同则工具集不同）。"""
    tools = build_music_tools(access_token, mode=mode)
    model = _build_bound_model(tools)
    task_mode = mode

    def agent_node(state: AgentState) -> dict:
        return music_agent_node(state, model=model, task_mode=task_mode)

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


def _extract_final_answer(messages: list) -> str:
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        content = msg.content
        if not content:
            continue
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text") or ""))
                elif isinstance(block, str):
                    parts.append(block)
            text = "".join(parts).strip()
            if text:
                return text
    return ""


def _save_music_turn(state: AgentState, *, question: str, final: str) -> dict:
    bind_trace_from_state(state, intent="music")
    session_id = state.get("session_id") or ""
    user_id = int(state.get("user_id") or 0)
    if session_id:
        ChatHistoryService().save_turn(
            session_id=session_id,
            user_id=user_id,
            user_question=question,
            assistant_answer=final,
        )
        log_event("history.saved", session_id=session_id)
    return {"final_answer": final}


def should_polish_music_final(final: str) -> bool:
    """短句/操作结果不润色，长分析才交给 DeepSeek。"""
    text = (final or "").strip()
    if len(text) < 60:
        return False
    if text.startswith(("已添加：", "音乐助手处理失败", "请输入", "已识别")):
        return False
    return True


def _finish_music_result(state: AgentState, *, question: str, final: str) -> dict:
    """千问草稿：可选 defer 保存，由 DeepSeek 润色后再落库。"""
    if AgentConfig().music_final_via_chat and should_polish_music_final(final):
        return {"final_answer": final, "polish": True}
    return {**_save_music_turn(state, question=question, final=final), "polish": False}


def _react_add_save_succeeded(messages: list) -> bool:
    """ReAct 是否已完成保存（含「已在列表」等业务结果）。"""
    for msg in messages or []:
        if not isinstance(msg, ToolMessage):
            continue
        if getattr(msg, "name", None) != "save_music_track_tool":
            continue
        try:
            data = json.loads(str(msg.content))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if data.get("id"):
            return True
        hint = str(data.get("message") or "")
        if "已在" in hint or "已存在" in hint:
            return True
    return False


def _add_fallback_reason(task_mode: str, messages: list, *, invoke_failed: bool) -> str | None:
    """加歌场景下判断是否需要降级到固定解析链路。"""
    if task_mode != "add":
        return None
    if invoke_failed:
        return "invoke_error"
    if _count_tool_rounds(messages) == 0:
        return "no_tool_calls"
    if not _react_add_save_succeeded(messages):
        return "save_not_completed"
    return None


def run_music_add_direct(state: AgentState, *, reason: str = "unknown") -> dict:
    """加歌降级链路：解析链接 → 拉元数据 → 保存（ReAct 失败时自动触发）。"""
    log_event("react.fallback", subgraph="music", reason=reason, model=_execute_model_name())
    question = (state.get("question") or "").strip()
    access_token = (state.get("access_token") or "").strip()

    with span("music.add_direct", question_preview=preview(question)):
        log_event("tool.start", tool="parse_qq_share_url", args={"share_url": preview(question, 120)})

        meta = parse_qq_share_with_meta(question)
        if meta.get("message"):
            log_event(
                "tool.end",
                tool="parse_qq_share_url",
                ok=False,
                level=logging.ERROR,
                result_preview=preview(str(meta.get("message")), 200),
            )
            hint = meta.get("hint") or ""
            detail = meta.get("detail") or ""
            msg = meta["message"]
            if hint:
                msg = f"{msg}（{hint}）"
            if detail:
                msg = f"{msg} [{detail}]"
            return _save_music_turn(state, question=question, final=msg)

        song_id = meta.get("songId")
        title = (meta.get("title") or "").strip() or f"QQ #{song_id}"
        artist = (meta.get("artist") or "").strip()
        share_url = meta.get("shareUrl") or question

        log_event(
            "tool.end",
            tool="parse_qq_share_url",
            ok=True,
            result_preview=preview(
                f"songId={song_id} title={title} artist={artist}",
                200,
            ),
        )

        if not access_token:
            return _save_music_turn(
                state,
                question=question,
                final=f"已识别《{title}》· {artist}。登录后我可以帮你保存到播放列表。",
            )

        log_event(
            "tool.start",
            tool="save_music_track_tool",
            args=redact_args(
                {
                    "title": title,
                    "artist": artist,
                    "qq_song_id": song_id,
                    "share_url": share_url,
                }
            ),
        )

        saved = save_music_track(
            access_token=access_token,
            title=title,
            artist=artist,
            qq_song_id=song_id,
            duration_sec=meta.get("durationSec"),
            share_url=share_url,
        )

        label = f"《{title}》· {artist}" if artist else f"《{title}》"

        if saved.get("message") and not saved.get("id"):
            log_event(
                "tool.end",
                tool="save_music_track_tool",
                ok=False,
                result_preview=preview(str(saved.get("message")), 200),
            )
            err = str(saved.get("message") or "")
            if "已在" in err or "已存在" in err:
                return _save_music_turn(
                    state,
                    question=question,
                    final=f"{label} 已在你的播放列表里啦。",
                )
            return _save_music_turn(state, question=question, final=err)

        log_event(
            "tool.end",
            tool="save_music_track_tool",
            ok=True,
            result_preview=preview(f"saved id={saved.get('id')} {label}", 200),
        )
        log_event(
            "react.done",
            subgraph="music",
            mode="add_fallback",
            model=_execute_model_name(),
            song_id=song_id,
            title=title,
            artist=artist,
            fallback_reason=reason,
        )
        return _save_music_turn(
            state,
            question=question,
            final=f"已添加：{label}",
        )


def run_music_react(state: AgentState) -> dict:
    """Music 子 ReAct 入口：invoke 子图并返回 final_answer。"""
    bind_trace_from_state(state, intent="music")

    access_token = (state.get("access_token") or "").strip()
    question = (state.get("question") or "").strip()
    if not question:
        log_event("react.skip", reason="empty_question")
        return {"final_answer": "请输入你的问题或 QQ 音乐分享链接。"}

    task_mode = detect_music_task_mode(question)
    log_event("react.task_mode", subgraph="music", task_mode=task_mode)

    messages: list = []
    invoke_failed = False

    with span("react", subgraph="music", logged_in=bool(access_token), task_mode=task_mode):
        try:
            graph = compile_music_react_graph(access_token, task_mode)
            result = run_in_trace_context(
                graph.invoke,
                {
                    "question": question,
                    "access_token": access_token,
                    "session_id": state.get("session_id") or "",
                    "user_id": state.get("user_id") or 0,
                    "trace_id": state.get("trace_id") or "",
                },
            )
            messages = result.get("messages") or []
        except Exception:
            invoke_failed = True
            logger.exception("[music_react] invoke failed")
            log_event("react.error", subgraph="music", model=_execute_model_name())

    fallback_reason = _add_fallback_reason(
        task_mode, messages, invoke_failed=invoke_failed
    )
    if fallback_reason:
        fallback_result = run_music_add_direct(state, reason=fallback_reason)
        return {**fallback_result, "messages": messages}

    if invoke_failed:
        return _finish_music_result(
            state,
            question=question,
            final="音乐助手处理失败，请稍后重试。",
        )

    final = _extract_final_answer(messages)
    final = final or "处理完成。"
    rounds = _count_tool_rounds(messages)

    log_event(
        "react.done",
        subgraph="music",
        rounds=rounds,
        model=_execute_model_name(),
        message_count=len(messages),
        mode="react",
        polish_deferred=AgentConfig().music_final_via_chat and should_polish_music_final(final),
        **answer_log_fields(final),
    )

    return {
        **_finish_music_result(state, question=question, final=final),
        "messages": messages,
    }


def make_logging_tool_node(tools: list):
    base = ToolNode(tools, handle_tool_errors=True)

    def _node(state: AgentState) -> dict:
        last = (state.get("messages") or [])[-1]
        tool_calls = getattr(last, "tool_calls", None) or []
        for tc in tool_calls:
            log_event(
                "tool.start",
                tool=tc.get("name"),
                args=redact_args(tc.get("args") or {}),
            )
        t0 = time.perf_counter()
        try:
            result = base.invoke(state)
        except Exception as exc:
            latency = int((time.perf_counter() - t0) * 1000)
            for tc in tool_calls:
                log_event(
                    "tool.error",
                    tool=tc.get("name"),
                    latency_ms=latency,
                    error=str(exc),
                    level=logging.ERROR,
                )
            raise

        latency = int((time.perf_counter() - t0) * 1000)
        for msg in result.get("messages") or []:
            if not isinstance(msg, ToolMessage):
                continue
            content = str(msg.content)
            ok, level = tool_result_status(content)
            log_event(
                "tool.end",
                tool=getattr(msg, "name", None),
                latency_ms=latency,
                ok=ok,
                level=level,
                result_preview=preview(content, 300),
            )
        return result

    return _node
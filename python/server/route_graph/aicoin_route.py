"""AiCoin 意图子 ReAct：由 run_aicoin_react 对外暴露。"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from config.config import AgentConfig
from server.agent import ChatModel
from server.skills_server.prompt_assembler import assemble_for_state
from server.qq.market_pipeline import env_two_phase_enabled
from server.qq.reply_format import (
    build_qq_aicoin_system_append,
    format_qq_market_reply,
    qq_aicoin_max_rounds,
)
from server.route_graph.react_subgraph import (
    effective_max_react_rounds,
    compile_react_graph,
    count_tool_rounds,
    extract_final_answer,
)
from server.state import AgentState
from server.tools.aicoin_agent_tools import build_aicoin_tools
from service.chat_history import ChatHistoryService
from utils.log.token_usage import (
    log_prompt_assembled,
    record_react_conversation,
    request_token_summary_fields,
)
from utils.log.trace_log import bind_trace, log_event, preview, span
from utils.world_lexicon import apply_world_lexicon

_DEFAULT_AICOIN_HISTORY_LIMIT = 4

logger = logging.getLogger(__name__)


def _build_initial_messages(state: AgentState) -> list:
    channel = (state.get("channel") or "web").strip().lower()
    question = (state.get("question") or "").strip()
    append = build_qq_aicoin_system_append(question) if channel == "qq" else ""
    system = assemble_for_state(state, intent="aicoin", system_append=append)
    log_prompt_assembled(
        phase="aicoin",
        system_prompt=system,
        intent="aicoin",
        channel=channel,
    )
    msgs: list = [SystemMessage(content=system)]
    session_id = state.get("session_id") or ""
    user_id = int(state.get("user_id") or 0)
    limit = int(state.get("limit") or _DEFAULT_AICOIN_HISTORY_LIMIT)
    limit = max(0, min(limit, 8))
    if session_id and user_id and limit > 0:
        history_rows = ChatHistoryService().get_recent_history(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
        )
        msgs.extend(ChatModel._to_lc_messages(history_rows))
    msgs.append(HumanMessage(content=state.get("question") or ""))
    return msgs


def run_aicoin_react(
    state: AgentState,
    *,
    chat_model: ChatModel | None = None,
) -> dict:
    bind_trace(
        trace_id=state.get("trace_id") or None,
        session_id=state.get("session_id") or None,
        user_id=int(state.get("user_id") or 0),
        intent="aicoin",
    )

    question = (state.get("question") or "").strip()
    if not question:
        log_event("react.skip", subgraph="aicoin", reason="empty_question")
        return {"final_answer": "请先描述你想查询的行情或资讯。"}

    channel = (state.get("channel") or "web").strip().lower()

    if channel == "qq" and env_two_phase_enabled() and chat_model is not None:
        from server.qq.market_pipeline import run_aicoin_qq_two_phase

        return run_aicoin_qq_two_phase(state, chat_model)

    tools = build_aicoin_tools(channel=channel, question=question)
    if not tools:
        import os

        from utils.mcp.registry import is_mcp_enabled, reload_mcp_configs

        reload_mcp_configs()
        tools = build_aicoin_tools(channel=channel, question=question)
    if not tools:
        env_raw = os.getenv("AICOIN_MCP_ENABLED", "")
        enabled_now = is_mcp_enabled("aicoin")
        log_event(
            "react.skip",
            subgraph="aicoin",
            reason="mcp_disabled",
            env_aicoin=env_raw or "(unset)",
            registry_enabled=enabled_now,
        )
        if (env_raw or "").strip().lower() in ("1", "true", "yes", "on"):
            hint = "AICOIN_MCP_ENABLED 已为 true，请重启 blog-agent（Python）进程使配置生效。"
        else:
            hint = "请在 python/.env 设置 AICOIN_MCP_ENABLED=true，并确认 config/mcp_servers.json 含 aicoin。"
        return {"final_answer": f"行情查询功能未开启（{hint}）"}

    max_rounds = (
        qq_aicoin_max_rounds(question)
        if channel == "qq"
        else effective_max_react_rounds()
    )

    graph = compile_react_graph(
        tools=tools,
        build_initial_messages=_build_initial_messages,
        subgraph="aicoin",
        max_rounds=max_rounds,
    )

    try:
        with span("react", subgraph="aicoin"):
            result = graph.invoke(state)
        messages = result.get("messages") or []
    except Exception:
        logger.exception("[aicoin] react failed session_id=%s", state.get("session_id"))
        log_event("react.error", subgraph="aicoin", level=logging.ERROR)
        return {"final_answer": "行情助手暂时不可用，请稍后再试。"}

    raw = extract_final_answer(messages) or "处理完成。"
    final = format_qq_market_reply(raw) if channel == "qq" else apply_world_lexicon(raw)
    rounds = count_tool_rounds(messages)
    record_react_conversation(
        subgraph="aicoin",
        model=AgentConfig().react_model_name,
        messages=messages,
        tool_rounds=rounds,
    )
    log_event(
        "react.done",
        subgraph="aicoin",
        channel=channel,
        max_rounds=max_rounds,
        tool_count=len(tools),
        rounds=rounds,
        final_preview=preview(final),
        message_count=len(messages),
        **request_token_summary_fields(),
    )

    session_id = state.get("session_id") or ""
    user_id = int(state.get("user_id") or 0)
    if session_id:
        ch = (channel or "web").strip().lower()
        ChatHistoryService().save_turn(
            session_id=session_id,
            user_id=user_id,
            user_question=question,
            assistant_answer=final,
            channel=ch,
        )
        log_event("history.saved", session_id=session_id, channel=ch)

    return {"final_answer": final, "messages": messages}

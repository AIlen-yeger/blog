"""笔记发布后：总结笔记 + 结合近期聊天写 Kohaku 回复，并入库。"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from config.config import AgentConfig
from server.agent import ChatModel
from server.prompt_skills import build_system_prompt
from server.state import AgentState
from server.tools.comment_agent_tools import save_note_agent_reply_impl
from service.chat_history import ChatHistoryService
from utils.trace_log import bind_trace, log_event, preview, span

logger = logging.getLogger(__name__)
_DEFAULT_HISTORY_LIMIT = AgentConfig().history_limit


def _format_note_question(state: AgentState) -> str:
    """用户消息：结构化笔记正文（Java 传入的 question 或 state 字段）。"""
    title = (state.get("note_title") or "").strip()
    body = (state.get("question") or "").strip()
    if title and body and title not in body[:80]:
        return f"【笔记标题】{title}\n\n【笔记正文】\n{body}"
    if body.startswith("【笔记"):
        return body
    if title:
        return f"【笔记标题】{title}\n\n【笔记正文】\n{body}"
    return body or "（笔记内容为空）"


def run_note_comment(state: AgentState) -> dict:
    """
    commit_user 意图：一次性生成回复并保存到 Java notes.agent_reply。
    调用方应设置 note_id、question（正文）、session_id、user_id。
    """
    bind_trace(
        trace_id=state.get("trace_id") or None,
        session_id=state.get("session_id") or None,
        user_id=int(state.get("user_id") or 0),
        intent="commit_user",
    )

    note_id = (state.get("note_id") or "").strip()
    job_id = (state.get("job_id") or "").strip()
    if not note_id:
        log_event("note.comment.skip", reason="missing_note_id")
        return {"final_answer": "", "saved": False}
    if not job_id:
        log_event("note.comment.skip", reason="missing_job_id", note_id=note_id)
        return {"final_answer": "", "saved": False}

    question = _format_note_question(state)
    session_id = state.get("session_id") or ""
    user_id = int(state.get("user_id") or 0)
    limit = int(state.get("limit") or _DEFAULT_HISTORY_LIMIT)
    channel = (state.get("channel") or "internal").strip().lower()

    system = build_system_prompt(
        intent="commit_user",
        channel=channel,
        developer_name=(state.get("user_name") or "").strip() or None,
    )
    history_svc = ChatHistoryService()
    messages = [
        SystemMessage(content=system),
        *ChatModel._to_lc_messages(
            history_svc.get_recent_history(
                session_id=session_id,
                user_id=user_id,
                limit=limit,
            )
        ),
        HumanMessage(content=question),
    ]

    reply = ""
    try:
        with span("note.comment.llm", note_id=note_id):
            reply = ChatModel().invoke_messages_once(messages)
    except Exception:
        logger.exception("[note.comment] llm failed note_id=%s", note_id)
        log_event("note.comment.error", note_id=note_id, level=logging.ERROR)
        return {"final_answer": "生成笔记回复失败，请稍后刷新查看。", "saved": False}

    if not reply:
        reply = "我读完了这篇笔记，想跟你说几句心里话，但一时组织不好语言——晚点再来看看好吗？"

    save_result = save_note_agent_reply_impl(
        note_id=note_id,
        agent_reply=reply,
        job_id=job_id,
    )
    saved = bool(save_result.get("ok"))

    if session_id and user_id > 0:
        history_svc.save_turn(
            session_id=session_id,
            user_id=user_id,
            user_question=question[:2000],
            assistant_answer=reply,
        )

    log_event(
        "note.comment.done",
        note_id=note_id,
        job_id=job_id,
        saved=saved,
        final_preview=preview(reply, 200),
        reply_length=len(reply),
    )
    return {
        "final_answer": reply,
        "saved": saved,
        "note_id": note_id,
        "save_result": save_result,
    }

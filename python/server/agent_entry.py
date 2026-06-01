"""
Agent 统一入口（方案 A）：
  1. LangGraph 路由器只做意图识别
  2. chat → 流式 ChatModel.chat（SSE）或非流式 chat_once（QQ 等）
  3. 其它意图 → 工具子图 / invoke
"""

import json
import logging
from typing import Iterator

from config.config import AgentConfig
from server.application_graph import AgentLangGraph, intent_from_question
from server.route_graph.music_route import run_music_react
from server.state import AgentState
from utils.trace_log import (
    bind_trace,
    bind_trace_from_state,
    log_event,
    new_trace_id,
    preview,
    record_model,
    span,
)

_DEFAULT_HISTORY_LIMIT = AgentConfig().history_limit

logger = logging.getLogger(__name__)


def _format_sse(payload: dict) -> str:
    """模块级 SSE 格式化；热重载时避免旧 generator 引用失效的函数对象。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_done() -> str:
    return "data: [DONE]\n\n"


class AgentEntry:
    def __init__(self) -> None:
        self._graph_agent = AgentLangGraph()

    @property
    def chat_model(self):
        return self._graph_agent.chat_model

    def classify_intent(self, state: AgentState) -> str:
        return self._graph_agent.classify_intent(state)

    def _build_state(
        self,
        *,
        question: str,
        session_id: str,
        user_id: int,
        limit: int,
        access_token: str,
        trace_id: str,
        channel: str,
    ) -> AgentState:
        return {
            "question": question,
            "session_id": session_id,
            "user_id": user_id,
            "limit": limit,
            "access_token": access_token,
            "trace_id": trace_id,
            "channel": channel,
        }

    def _classify_with_fallback(self, state: AgentState) -> str:
        question = state.get("question") or ""
        session_id = state.get("session_id") or ""
        trace_id = state.get("trace_id") or ""
        with span("intent.classify"):
            try:
                return self.classify_intent(state) or "chat"
            except Exception:
                logger.exception(
                    "[agent] classify_intent failed session_id=%s trace_id=%s",
                    session_id,
                    trace_id,
                )
                intent = intent_from_question(question) or "chat"
                log_event(
                    "intent.fallback",
                    reason="classify_exception",
                    intent=intent,
                    question_preview=preview(question, 120),
                )
                return intent

    def _log_intent_classified(self, intent: str, question: str) -> None:
        bind_trace(intent=intent)
        record_model(AgentConfig().judge_model_name)
        log_event(
            "intent.classified",
            intent=intent,
            model=AgentConfig().judge_model_name,
            question_preview=preview(question, 120),
        )

    def _resolve_reply(self, state: AgentState, *, intent: str) -> str:
        """非流式总出口：QQ / 脚本等 channel!=web 时使用。"""
        question = state["question"]
        session_id = state["session_id"]
        user_id = state["user_id"]
        limit = state.get("limit") or _DEFAULT_HISTORY_LIMIT
        trace_id = state.get("trace_id") or ""

        channel = (state.get("channel") or "web").strip().lower()

        if intent == "chat":
            return self._chat_once(
                question=question,
                session_id=session_id,
                user_id=user_id,
                limit=limit,
                trace_id=trace_id,
                channel=channel,
            )

        if intent in ("music", "add_son"):
            result = run_music_react(state)
            final = (result.get("final_answer") or "").strip() or "处理完成"
            if result.get("polish"):
                log_event("music.polish.start", draft_length=len(final))
                return self._music_polish_once(
                    question=question,
                    draft=final,
                    session_id=session_id,
                    user_id=user_id,
                    limit=limit,
                    trace_id=trace_id,
                    channel=channel,
                )
            return final

        if intent == "commit_user":
            return "笔记回复功能开发中，敬请期待。"

        return self._chat_once(
            question=question,
            session_id=session_id,
            user_id=user_id,
            limit=limit,
            trace_id=trace_id,
            channel=channel,
        )

    def run_once(
        self,
        *,
        question: str,
        session_id: str,
        user_id: int = 0,
        limit: int | None = None,
        access_token: str = "",
        trace_id: str = "",
        channel: str = "qq",
    ) -> str:
        """非流式一次性回复；QQ 桥接使用 channel=qq。"""
        tid = trace_id or new_trace_id()
        lim = limit or _DEFAULT_HISTORY_LIMIT
        state = self._build_state(
            question=question,
            session_id=session_id,
            user_id=user_id,
            limit=lim,
            access_token=access_token,
            trace_id=tid,
            channel=channel,
        )
        bind_trace(
            trace_id=tid,
            session_id=session_id,
            user_id=user_id,
        )
        intent = self._classify_with_fallback(state)
        state["intent"] = intent
        self._log_intent_classified(intent, question)
        bind_trace_from_state(state, intent=intent)
        return self._resolve_reply(state, intent=intent)

    def stream_sse(
        self,
        *,
        question: str,
        session_id: str,
        user_id: int,
        limit: int = _DEFAULT_HISTORY_LIMIT,
        access_token: str = "",
        trace_id: str = "",
    ) -> Iterator[str]:
        """供 FastAPI StreamingResponse 使用（桌宠等 web 渠道）。"""
        state = self._build_state(
            question=question,
            session_id=session_id,
            user_id=user_id,
            limit=limit,
            access_token=access_token,
            trace_id=trace_id,
            channel="web",
        )
        bind_trace(
            trace_id=trace_id or None,
            session_id=session_id,
            user_id=user_id,
        )

        intent = self._classify_with_fallback(state)
        self._log_intent_classified(intent, question)
        yield _format_sse({"type": "meta", "intent": intent})

        bind_trace_from_state(state, intent=intent)
        state["intent"] = intent

        channel = (state.get("channel") or "web").strip().lower()

        if intent == "chat":
            yield from self._stream_chat(
                question=question,
                session_id=session_id,
                user_id=user_id,
                limit=limit,
                trace_id=trace_id,
                channel=channel,
            )
            return

        if intent in ("music", "add_son"):
            result = run_music_react(state)
            final = result.get("final_answer") or "处理完成"
            if result.get("polish"):
                log_event("music.polish.start", draft_length=len(final))
                yield from self._stream_music_polish(
                    question=question,
                    draft=final,
                    session_id=session_id,
                    user_id=user_id,
                    limit=limit,
                    trace_id=trace_id,
                    channel=channel,
                )
                return
            yield _format_sse({"type": "message", "content": final})
            yield _sse_done()
            return

        if intent == "commit_user":
            yield _format_sse(
                {
                    "type": "message",
                    "content": "笔记回复功能开发中，敬请期待。",
                }
            )
            yield _sse_done()
            return

        yield from self._stream_chat(
            question=question,
            session_id=session_id,
            user_id=user_id,
            limit=limit,
            trace_id=trace_id,
            channel=channel,
        )

    def _chat_once(
        self,
        *,
        question: str,
        session_id: str,
        user_id: int,
        limit: int,
        trace_id: str = "",
        channel: str = "qq",
    ) -> str:
        bind_trace_from_state(
            {"trace_id": trace_id, "session_id": session_id, "user_id": user_id},
            intent="chat",
        )
        try:
            return self.chat_model.chat_once(
                question=question,
                session_id=session_id,
                user_id=user_id,
                limit=limit,
                trace_id=trace_id,
                channel=channel,
            )
        except Exception as exc:
            logger.exception("[agent] chat_once failed session_id=%s", session_id)
            return f"对话失败：{exc}"

    def _music_polish_once(
        self,
        *,
        question: str,
        draft: str,
        session_id: str,
        user_id: int,
        limit: int,
        trace_id: str = "",
        channel: str = "web",
    ) -> str:
        bind_trace_from_state(
            {"trace_id": trace_id, "session_id": session_id, "user_id": user_id},
            intent="music",
        )
        try:
            return self.chat_model.rewrite_music_once(
                question=question,
                draft=draft,
                session_id=session_id,
                user_id=user_id,
                limit=limit,
                trace_id=trace_id,
                channel=channel,
            )
        except Exception as exc:
            logger.exception("[agent] music polish_once failed session_id=%s", session_id)
            return draft.strip() or f"回复润色失败：{exc}"

    def _stream_chat(
        self,
        *,
        question: str,
        session_id: str,
        user_id: int,
        limit: int,
        trace_id: str = "",
        channel: str = "web",
    ) -> Iterator[str]:
        bind_trace_from_state(
            {"trace_id": trace_id, "session_id": session_id, "user_id": user_id},
            intent="chat",
        )
        try:
            for chunk in self.chat_model.chat(
                question=question,
                session_id=session_id,
                user_id=user_id,
                limit=limit,
                trace_id=trace_id,
                channel=channel,
            ):
                if isinstance(chunk, dict):
                    yield _format_sse(chunk)
                else:
                    yield _format_sse({"type": "message", "content": str(chunk)})
        except Exception as exc:
            logger.exception("[agent] chat stream failed session_id=%s", session_id)
            yield _format_sse({"code": 50000, "message": f"对话失败：{exc}"})
        yield _sse_done()

    def _stream_music_polish(
        self,
        *,
        question: str,
        draft: str,
        session_id: str,
        user_id: int,
        limit: int,
        trace_id: str = "",
        channel: str = "web",
    ) -> Iterator[str]:
        """千问草稿 → DeepSeek 流式润色。"""
        bind_trace_from_state(
            {"trace_id": trace_id, "session_id": session_id, "user_id": user_id},
            intent="music",
        )
        try:
            for chunk in self.chat_model.rewrite_music_stream(
                question=question,
                draft=draft,
                session_id=session_id,
                user_id=user_id,
                limit=limit,
                trace_id=trace_id,
                channel=channel,
            ):
                if isinstance(chunk, dict):
                    yield _format_sse(chunk)
                else:
                    yield _format_sse({"type": "message", "content": str(chunk)})
        except Exception as exc:
            logger.exception("[agent] music polish failed session_id=%s", session_id)
            yield _format_sse({"code": 50000, "message": f"回复润色失败：{exc}"})
        yield _sse_done()


_agent_entry: AgentEntry | None = None


def get_agent_entry() -> AgentEntry:
    global _agent_entry
    if _agent_entry is None:
        _agent_entry = AgentEntry()
    return _agent_entry

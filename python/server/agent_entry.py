"""
Agent 统一入口：run() = 组请求 → judge 意图 → 按 intent×channel 执行分支。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Literal

from config.config import AgentConfig
from server.intent_router import IntentRouter, intent_from_question
from server.route_graph.comment_route import run_note_comment
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
_STREAM_CHUNK_CHARS = 12

logger = logging.getLogger(__name__)

OutputMode = Literal["stream", "once"]


def _format_sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_done() -> str:
    return "data: [DONE]\n\n"


def canonical_intent(intent: str) -> str:
    key = (intent or "chat").strip().lower()
    return "music" if key == "add_son" else key


def output_mode_for(intent: str, channel: str) -> OutputMode:
    ch = (channel or "web").strip().lower()
    it = canonical_intent(intent)
    if ch == "web" and it in ("chat", "music"):
        return "stream"
    return "once"


@dataclass
class AgentReplyResult:
    intent: str
    output_mode: OutputMode
    channel: str
    text: str | None = None
    _body_stream: Iterator[str] | None = None

    def plain_text(self) -> str:
        if self.text is not None:
            return self.text
        raise RuntimeError(
            f"intent={self.intent} channel={self.channel} 为流式结果，请用 iter_sse()"
        )

    def iter_sse(self) -> Iterator[str]:
        yield _format_sse({"type": "meta", "intent": self.intent})
        if self.output_mode == "once":
            yield _format_sse({"type": "message", "content": self.text or ""})
            yield _sse_done()
            return
        if self._body_stream is not None:
            yield from self._body_stream
            return
        yield _sse_done()


class AgentEntry:
    def __init__(self) -> None:
        self._router = IntentRouter()


    @property
    def chat_model(self):
        return self._router.chat_model

    def run(
        self,
        *,
        question: str,
        session_id: str,
        user_id: int = 0,
        limit: int | None = None,
        access_token: str = "",
        trace_id: str = "",
        channel: str = "web",
        force_intent: str = "",
        note_id: str = "",
        note_title: str = "",
    ) -> AgentReplyResult:
        ch = (channel or "web").strip().lower()
        tid = trace_id or new_trace_id()
        state: AgentState = {
            "question": question,
            "session_id": session_id,
            "user_id": user_id,
            "limit": limit or _DEFAULT_HISTORY_LIMIT,
            "access_token": access_token,
            "trace_id": tid,
            "channel": ch,
            "note_id": (note_id or "").strip(),
            "note_title": (note_title or "").strip(),
        }

        bind_trace(trace_id=tid, session_id=session_id, user_id=user_id)

        forced = canonical_intent(force_intent) if (force_intent or "").strip() else ""
        if forced:
            intent = forced
            log_event(
                "intent.forced",
                intent=intent,
                question_preview=preview(question, 120),
            )
        else:
            # 1. 意图 judge（失败则用关键词兜底）
            with span("intent.classify"):
                try:
                    intent = canonical_intent(self._router.classify_intent(state))
                except Exception:
                    logger.exception(
                        "[agent] intent classify failed session_id=%s trace_id=%s",
                        session_id,
                        tid,
                    )
                    intent = canonical_intent(intent_from_question(question) or "chat")
                    log_event(
                        "intent.fallback",
                        reason="classify_exception",
                        intent=intent,
                        question_preview=preview(question, 120),
                    )

        state["intent"] = intent
        bind_trace_from_state(state, intent=intent)
        record_model(AgentConfig().judge_model_name)
        log_event(
            "intent.classified",
            intent=intent,
            model=AgentConfig().judge_model_name,
            question_preview=preview(question, 120),
        )

        # 2. intent × channel → 输出形态 + 分支执行
        mode = output_mode_for(intent, ch)
        log_event("reply.route", intent=intent, channel=ch, output_mode=mode)

        if mode == "once":
            handler = self._ONCE_HANDLERS.get(intent, self._once_chat)
            return AgentReplyResult(
                intent=intent,
                output_mode="once",
                channel=ch,
                text=handler(self, state),
            )

        stream_handler = self._STREAM_HANDLERS.get(intent, self._stream_chat)
        return AgentReplyResult(
            intent=intent,
            output_mode="stream",
            channel=ch,
            _body_stream=stream_handler(self, state),
        )

    def _once_chat(self, state: AgentState) -> str:
        bind_trace_from_state(state, intent="chat")
        try:
            return self.chat_model.chat_once(
                question=state["question"],
                session_id=state["session_id"],
                user_id=state["user_id"],
                limit=int(state.get("limit") or _DEFAULT_HISTORY_LIMIT),
                trace_id=state.get("trace_id") or "",
                channel=(state.get("channel") or "qq").strip().lower(),
            )
        except Exception as exc:
            logger.exception("[agent] chat failed session_id=%s", state.get("session_id"))
            return f"对话失败：{exc}"

    def _once_music(self, state: AgentState) -> str:
        bind_trace_from_state(state, intent="music")
        try:
            result = run_music_react(state)
            return (result.get("final_answer") or "").strip() or "处理完成"
        except Exception:
            logger.exception("[agent] music failed session_id=%s", state.get("session_id"))
            return "音乐助手暂时不可用，请稍后再试。"

    def _once_commit_user(self, state: AgentState) -> str:
        result = run_note_comment(state)
        return (result.get("final_answer") or "").strip() or "笔记回复生成失败，请稍后刷新。"

    def run_note_comment_job(
        self,
        *,
        note_id: str,
        question: str,
        note_title: str = "",
        session_id: str = "",
        user_id: int = 0,
        limit: int | None = None,
        trace_id: str = "",
        job_id: str = "",
    ) -> dict:
        """笔记发布后内部任务：生成 Kohaku 回复并写入 Java notes.agent_reply。"""
        tid = trace_id or new_trace_id()
        state: AgentState = {
            "question": question,
            "session_id": session_id,
            "user_id": user_id,
            "limit": limit or _DEFAULT_HISTORY_LIMIT,
            "trace_id": tid,
            "channel": "internal",
            "intent": "commit_user",
            "note_id": (note_id or "").strip(),
            "note_title": (note_title or "").strip(),
            "job_id": (job_id or "").strip(),
        }
        bind_trace(trace_id=tid, session_id=session_id, user_id=user_id, intent="commit_user")
        return run_note_comment(state)












    def _stream_chat(self, state: AgentState) -> Iterator[str]:
        bind_trace_from_state(state, intent="chat")
        try:
            for chunk in self.chat_model.chat(
                question=state["question"],
                session_id=state["session_id"],
                user_id=state["user_id"],
                limit=int(state.get("limit") or _DEFAULT_HISTORY_LIMIT),
                trace_id=state.get("trace_id") or "",
                channel=(state.get("channel") or "web").strip().lower(),
            ):
                if isinstance(chunk, dict):
                    yield _format_sse(chunk)
                else:
                    yield _format_sse({"type": "message", "content": str(chunk)})
        except Exception as exc:
            logger.exception("[agent] chat stream failed session_id=%s", state.get("session_id"))
            yield _format_sse({"code": 50000, "message": f"对话失败：{exc}"})
        yield _sse_done()

    def _stream_music(self, state: AgentState) -> Iterator[str]:
        bind_trace_from_state(state, intent="music")
        try:
            result = run_music_react(state)
            final = (result.get("final_answer") or "").strip() or "处理完成"
            body = (final or "").strip()
            for i in range(0, len(body), _STREAM_CHUNK_CHARS):
                yield _format_sse({"type": "delta", "content": body[i : i + _STREAM_CHUNK_CHARS]})
            if not body:
                yield _format_sse({"type": "delta", "content": ""})
        except Exception as exc:
            logger.exception("[agent] music stream failed session_id=%s", state.get("session_id"))
            yield _format_sse({"code": 50000, "message": f"音乐助手失败：{exc}"})
        yield _sse_done()

    _ONCE_HANDLERS: dict[str, Callable[["AgentEntry", AgentState], str]] = {
        "chat": _once_chat,
        "music": _once_music,
        "commit_user": _once_commit_user,
    }

    _STREAM_HANDLERS: dict[str, Callable[["AgentEntry", AgentState], Iterator[str]]] = {
        "chat": _stream_chat,
        "music": _stream_music,
    }


_agent_entry: AgentEntry | None = None


def get_agent_entry() -> AgentEntry:
    global _agent_entry
    if _agent_entry is None:
        _agent_entry = AgentEntry()
    return _agent_entry

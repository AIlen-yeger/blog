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
from server.embedding.embedding_user_memory import get_user_memory
from server.aicoin_access import aicoin_allowed_for_state
from server.intent_dispatch import intent_output_mode, run_intent_step
from server.intent_router import IntentRouter, intent_from_question
from server.route_graph.comment_route import run_note_comment
from server.route_graph.orchestrator_graph import (
    effective_orchestrator_mode,
    resolve_execution_mode,
    resolve_orchestrator_tasks,
    run_orchestrator_step,
    should_delegate_chat,
    should_emit_plan_ui,
    should_use_orchestrator,
)
from server.state import AgentState
from utils.judge_intent.quick_judge import should_skip_memory_pipeline
from utils.log.token_usage import begin_request_tokens, finish_request_tokens
from utils.log.trace_log import (
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
    if ch == "web" and it == "orchestrate":
        return "stream"
    if ch == "web" and intent_output_mode(it) == "stream":
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

    def collect_plain_text(self) -> str:
        """同步场景（QQ poller 等）：一次性消费流式 SSE 并拼接正文。"""
        if self.text is not None:
            return (self.text or "").strip()
        parts: list[str] = []
        for chunk in self.iter_sse():
            line = chunk.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            kind = obj.get("type")
            if kind in ("message", "delta"):
                content = obj.get("content")
                if content:
                    parts.append(str(content))
            elif obj.get("message") and kind not in ("plan", "plan_step", "meta", "action_preview"):
                parts.append(str(obj.get("message")))
        return "".join(parts).strip()

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
        user_name: str = "",
        account: str = "",
        user_role: str = "",
        friend_qq: str = "",
        attachments: list | None = None,
        execution_mode: str = "auto",
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
            "user_name": (user_name or "").strip(),
            "account": (account or "").strip(),
            "user_role": (user_role or "").strip().lower(),
            "friend_qq": "".join(c for c in (friend_qq or "").strip() if c.isdigit()),
            "note_id": (note_id or "").strip(),
            "note_title": (note_title or "").strip(),
            "attachments": list(attachments or []),
            "execution_mode": resolve_execution_mode(
                {"execution_mode": (execution_mode or "auto").strip().lower()}
            ),
        }

        bind_trace(trace_id=tid, session_id=session_id, user_id=user_id)
        begin_request_tokens(tid)

        #测试/调试强制路由，跳过 judge
        forced = canonical_intent(force_intent) if (force_intent or "").strip() else ""

        use_orchestrator = forced == "orchestrate" or (
            not forced and should_use_orchestrator(state)
        )
        if use_orchestrator:
            orch_mode = effective_orchestrator_mode(
                state, force_orchestrate=(forced == "orchestrate")
            )
            tasks = resolve_orchestrator_tasks(state)
            if not should_delegate_chat(tasks, orch_mode):
                return AgentReplyResult(
                    intent="orchestrate",
                    output_mode="stream",
                    channel=ch,
                    _body_stream=self._stream_orchestrator_live(state, tasks, orch_mode),
                )

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

        if intent == "aicoin" and not aicoin_allowed_for_state(state):
            log_event(
                "intent.downgrade",
                from_intent="aicoin",
                intent="chat",
                reason="aicoin_not_allowed",
                account_preview=preview((state.get("account") or ""), 40),
                user_role=state.get("user_role") or "",
            )
            intent = "chat"

        state["intent"] = intent
        bind_trace_from_state(state, intent=intent)
        record_model(AgentConfig().judge_model_name)
        log_event(
            "intent.classified",
            intent=intent,
            model=AgentConfig().judge_model_name,
            question_preview=preview(question, 120),
        )

        if intent == "chat" and not should_skip_memory_pipeline(question):
            try:
                get_user_memory().process_user_message(
                    question,
                    user_id=user_id,
                    channel=ch,
                )
            except Exception:
                logger.exception(
                    "[agent] memory pipeline failed user_id=%s session_id=%s",
                    user_id,
                    session_id,
                )

        # 2. intent × channel → 输出形态 + 分支执行
        mode = output_mode_for(intent, ch)
        log_event("reply.route", intent=intent, channel=ch, output_mode=mode)


        #上面确认路由，经过路由模型判断，下面是根据流式还是非流式来选择执行对应路由下的方法
        if mode == "once":
            handler = self._ONCE_HANDLERS.get(intent, self._once_chat)
            result = AgentReplyResult(
                intent=intent,
                output_mode="once",
                channel=ch,
                text=handler(self, state),
            )
            finish_request_tokens(tid)
            return result

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
                intent=state.get("intent") or "chat",
                trace_id=state.get("trace_id") or "",
                channel=(state.get("channel") or "qq").strip().lower(),
                developer_name=(state.get("user_name") or "").strip(),
                user_logged_in=bool((state.get("access_token") or "").strip()),
            )
        except Exception as exc:
            logger.exception("[agent] chat failed session_id=%s", state.get("session_id"))
            return f"对话失败：{exc}"

    def _once_music(self, state: AgentState) -> str:
        result = run_intent_step(state, "music", chat_model=self.chat_model)
        if result.ok:
            return (result.text or "").strip() or "处理完成"
        return result.text or "音乐助手暂时不可用，请稍后再试。"

    def _once_commit_user(self, state: AgentState) -> str:
        result = run_intent_step(state, "commit_user", chat_model=self.chat_model)
        return (result.text or "").strip() or "笔记回复生成失败，请稍后刷新。"

    def _once_aicoin(self, state: AgentState) -> str:
        result = run_intent_step(state, "aicoin", chat_model=self.chat_model)
        if result.ok:
            return (result.text or "").strip() or "处理完成"
        return result.text or "行情助手暂时不可用，请稍后再试。"




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
        """笔记发布后内部任务：生成蕾西亚回复并写入 Java notes.agent_reply。"""
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
        begin_request_tokens(tid)
        return run_note_comment(state)


    def _stream_aicoin(self, state: AgentState) -> Iterator[str]:
        yield from self._stream_intent_step(state, "aicoin", error_label="行情助手失败")

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
                developer_name=(state.get("user_name") or "").strip(),
                intent=state.get("intent") or "chat",
                user_logged_in=bool((state.get("access_token") or "").strip()),
            ):
                if isinstance(chunk, dict):
                    yield _format_sse(chunk)
                else:
                    yield _format_sse({"type": "message", "content": str(chunk)})
        except Exception as exc:
            logger.exception("[agent] chat stream failed session_id=%s", state.get("session_id"))
            yield _format_sse({"code": 50000, "message": f"对话失败：{exc}"})
        yield _sse_done()

    def _stream_publish_note(self, state: AgentState) -> Iterator[str]:
        try:
            result = run_intent_step(state, "publish_note", chat_model=self.chat_model)
            yield from self._emit_preview_stream(
                intent="publish_note",
                message=result.text or "",
                preview=result.preview,
                action=result.action or "publish_note",
            )
        except Exception as exc:
            logger.exception("[agent] publish_note stream failed session_id=%s", state.get("session_id"))
            yield _format_sse({"code": 50000, "message": f"笔记预览失败：{exc}"})
            yield _sse_done()

    def _stream_orchestrator_live(
        self,
        state: AgentState,
        tasks: list[dict],
        mode: str,
    ) -> Iterator[str]:
        bind_trace_from_state(state, intent="orchestrate")
        try:
            if should_emit_plan_ui(tasks, mode):
                yield _format_sse(
                    {
                        "type": "plan",
                        "steps": [
                            {
                                "id": t["id"],
                                "intent": t["intent"],
                                "title": t["title"],
                                "status": "pending",
                            }
                            for t in tasks
                        ],
                    }
                )

            agent_state: AgentState = {
                "question": state.get("question") or "",
                "session_id": state.get("session_id") or "",
                "user_id": int(state.get("user_id") or 0),
                "limit": int(state.get("limit") or _DEFAULT_HISTORY_LIMIT),
                "access_token": state.get("access_token") or "",
                "channel": state.get("channel") or "web",
                "user_name": state.get("user_name") or "",
                "account": state.get("account") or "",
                "user_role": state.get("user_role") or "",
                "trace_id": state.get("trace_id") or "",
                "attachments": state.get("attachments") or [],
                "execution_mode": mode,
            }

            parts: list[str] = []
            pending_preview: dict | None = None
            pending_action = ""
            prior_results: list[dict] = []

            for task in tasks:
                step_id = str(task.get("id") or "")
                if step_id:
                    yield _format_sse(
                        {"type": "plan_step", "stepId": step_id, "status": "running"}
                    )
                try:
                    result = run_orchestrator_step(
                        agent_state,
                        task,
                        prior_results=prior_results,
                        chat_model=self.chat_model,
                    )
                    if result.get("preview"):
                        pending_preview = result.get("preview")
                        pending_action = str(result.get("action") or "publish_note")
                    text = str(result.get("text") or "")
                    parts.append(text)
                    prior_results.append(
                        {
                            "intent": task.get("intent"),
                            "text": text,
                            "ok": bool(result.get("ok", True)),
                        }
                    )
                    status = "done" if result.get("ok", True) else "failed"
                    if step_id:
                        yield _format_sse(
                            {
                                "type": "plan_step",
                                "stepId": step_id,
                                "status": status,
                                "summary": str(result.get("summary") or ""),
                            }
                        )
                except Exception:
                    logger.exception(
                        "[agent] orchestrator step failed intent=%s",
                        task.get("intent"),
                    )
                    parts.append("该步骤处理失败，请稍后重试。")
                    prior_results.append(
                        {
                            "intent": task.get("intent"),
                            "text": "该步骤处理失败",
                            "ok": False,
                        }
                    )
                    if step_id:
                        yield _format_sse(
                            {
                                "type": "plan_step",
                                "stepId": step_id,
                                "status": "failed",
                                "summary": "处理失败",
                            }
                        )

            body = "\n\n".join(p for p in parts if p).strip() or "处理完成。"
            for i in range(0, len(body), _STREAM_CHUNK_CHARS):
                yield _format_sse({"type": "delta", "content": body[i : i + _STREAM_CHUNK_CHARS]})
            if pending_preview and pending_action:
                yield _format_sse(
                    {
                        "type": "action_preview",
                        "action": pending_action,
                        "data": pending_preview,
                    }
                )
            yield _sse_done()
        except Exception:
            logger.exception("[agent] orchestrator stream failed")
            yield _format_sse({"code": 50000, "message": "编排暂时不可用，请稍后重试"})
            yield _sse_done()

    def _emit_preview_stream(
        self,
        *,
        intent: str,
        message: str,
        preview: dict | None,
        action: str,
    ) -> Iterator[str]:
        yield _format_sse({"type": "meta", "intent": intent})
        body = (message or "").strip()
        for i in range(0, len(body), _STREAM_CHUNK_CHARS):
            yield _format_sse({"type": "delta", "content": body[i : i + _STREAM_CHUNK_CHARS]})
        if preview and action:
            yield _format_sse(
                {
                    "type": "action_preview",
                    "action": action,
                    "data": preview,
                }
            )
        yield _sse_done()

    def _stream_intent_step(
        self,
        state: AgentState,
        intent: str,
        *,
        error_label: str,
    ) -> Iterator[str]:
        bind_trace_from_state(state, intent=intent)
        try:
            result = run_intent_step(state, intent, chat_model=self.chat_model)
            body = (result.text or "").strip()
            for i in range(0, len(body), _STREAM_CHUNK_CHARS):
                yield _format_sse({"type": "delta", "content": body[i : i + _STREAM_CHUNK_CHARS]})
            if not body:
                yield _format_sse({"type": "delta", "content": ""})
        except Exception as exc:
            logger.exception(
                "[agent] %s stream failed session_id=%s", intent, state.get("session_id")
            )
            yield _format_sse({"code": 50000, "message": f"{error_label}：{exc}"})
        yield _sse_done()

    def _stream_music(self, state: AgentState) -> Iterator[str]:
        yield from self._stream_intent_step(state, "music", error_label="音乐助手失败")

    _ONCE_HANDLERS: dict[str, Callable[["AgentEntry", AgentState], str]] = {
        "chat": _once_chat,
        "music": _once_music,
        "commit_user": _once_commit_user,
        "aicoin": _once_aicoin,
    }

    _STREAM_HANDLERS: dict[str, Callable[["AgentEntry", AgentState], Iterator[str]]] = {
        "chat": _stream_chat,
        "music": _stream_music,
        "aicoin": _stream_aicoin,
        "publish_note": _stream_publish_note,
    }


_agent_entry: AgentEntry | None = None


def get_agent_entry() -> AgentEntry:
    global _agent_entry
    if _agent_entry is None:
        _agent_entry = AgentEntry()
    return _agent_entry

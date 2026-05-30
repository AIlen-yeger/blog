"""
Agent 统一入口（方案 A）：
  1. LangGraph 路由器只做意图识别
  2. chat → 直接流式 ChatModel.chat（SSE）
  3. 其它意图 → 暂返回提示，后续再接工具子图 / invoke
"""

import json
import logging
from typing import Iterator

from config.config import AgentConfig
from server.application_graph import AgentLangGraph
from utils.trace_log import bind_trace, span, log_event, record_model

_DEFAULT_HISTORY_LIMIT = AgentConfig().history_limit
from server.route_graph.music_route import run_music_react
from server.state import AgentState

logger = logging.getLogger(__name__)


def _sse_line(payload: dict) -> str:
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
        """供 FastAPI StreamingResponse 使用。"""
        state: AgentState = {
            "question": question,
            "session_id": session_id,
            "user_id": user_id,
            "limit": limit,
            "access_token": access_token,
            "trace_id": trace_id,
        }
        bind_trace(
            trace_id=trace_id or None,
            session_id=session_id,
            user_id=user_id,
        )

        with span("intent.classify"):
            try:
                intent = self.classify_intent(state)
            except Exception:
                logger.exception(
                    "[agent] classify_intent failed session_id=%s trace_id=%s",
                    session_id,
                    trace_id,
                )
                intent = "chat"

        bind_trace(intent=intent)
        execute_model = AgentConfig().execute_model_name
        record_model(execute_model)
        log_event("intent.classified", intent=intent, model=execute_model)
        yield _sse_line({"type": "meta", "intent": intent})

        if intent == "chat":
            yield from self._stream_chat(
                question=question,
                session_id=session_id,
                user_id=user_id,
                limit=limit,
            )
            return

        if intent in ("music", "add_son"):
            result = run_music_react(state)
            yield _sse_line(
                {
                    "type": "message",
                    "content": result.get("final_answer") or "处理完成",
                }
            )
            yield _sse_done()
            return

        if intent == "commit_user":
            yield _sse_line(
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
        )

    def _stream_chat(
        self,
        *,
        question: str,
        session_id: str,
        user_id: int,
        limit: int,
    ) -> Iterator[str]:
        try:
            for chunk in self.chat_model.chat(
                question=question,
                session_id=session_id,
                user_id=user_id,
                limit=limit,
            ):
                yield _sse_line(chunk)
        except Exception as exc:
            logger.exception("[agent] chat stream failed session_id=%s", session_id)
            yield _sse_line({"code": 50000, "message": f"对话失败：{exc}"})
        yield _sse_done()


_agent_entry: AgentEntry | None = None


def get_agent_entry() -> AgentEntry:
    global _agent_entry
    if _agent_entry is None:
        _agent_entry = AgentEntry()
    return _agent_entry

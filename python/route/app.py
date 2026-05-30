import json
import logging
import os
from typing import Iterator

from fastapi import APIRouter, Body, Header
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from config.config import AgentConfig
from server.agent_entry import get_agent_entry
from utils.trace_log import bind_trace, new_trace_id, preview, span

_DEFAULT_HISTORY_LIMIT = AgentConfig().history_limit

router = APIRouter()
logger = logging.getLogger(__name__)

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    limit: int = Field(default=_DEFAULT_HISTORY_LIMIT, ge=1, le=50)
    session_id: str = Field(validation_alias=AliasChoices("session_id", "sessionId"))
    question: str
    account: str = ""
    user_name: str = Field(default="", validation_alias=AliasChoices("user_name", "userName"))
    user_id: int = Field(default=0, validation_alias=AliasChoices("user_id", "userId"))
    access_token: str = Field(default="", validation_alias=AliasChoices("access_token", "accessToken"))


def _safe_chat_stream(body: ChatRequest, trace_id: str) -> Iterator[str]:
    """Graph 判意图 → chat 走流式，其它分支暂返回占位文案。"""
    bind_trace(
        trace_id=trace_id,
        session_id=body.session_id,
        user_id=body.user_id,
    )
    with span("request", question_preview=preview(body.question)):
        try:
            entry = get_agent_entry()
            yield from entry.stream_sse(
                question=body.question,
                session_id=body.session_id,
                user_id=body.user_id,
                limit=body.limit,
                access_token=body.access_token,
                trace_id=trace_id,
            )
        except Exception as exc:
            logger.exception("[ai/chat] failed session_id=%s trace_id=%s", body.session_id, trace_id)
            payload = json.dumps({"code": 50000, "message": f"服务异常：{exc}"}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"


@router.post("/ai/ops/bug-scan")
def ops_bug_scan(x_ops_token: str | None = Header(default=None, alias="X-Ops-Token")):
    """开发者手动触发 Bug Ops 巡检（不对用户开放）。"""
    expected = (os.getenv("AGENT_OPS_TOKEN") or "").strip()
    if not expected or x_ops_token != expected:
        return JSONResponse(status_code=403, content={"code": 40300, "message": "forbidden"})

    from server.bug_agent_runner import scan_and_run_pending

    ran = scan_and_run_pending()
    return {"ok": True, "handled": len(ran), "items": ran}


@router.post("/ai/chat")
def llm_chat(body: ChatRequest = Body(...)):
    trace_id = new_trace_id()
    if not body.account or not body.user_name or not body.user_id:
        return JSONResponse(
            status_code=400,
            content={"code": 40000, "message": "用户不存在！"},
        )

    return StreamingResponse(
        _safe_chat_stream(body, trace_id),
        media_type="text/event-stream; charset=utf-8",
        headers={**SSE_HEADERS, "X-Trace-Id": trace_id},
    )

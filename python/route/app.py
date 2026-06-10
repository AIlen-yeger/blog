import json
import logging
import os
from typing import Any, Iterator

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from config.config import AgentConfig
from server.agent_entry import get_agent_entry
from utils.log.trace_log import bind_trace, new_trace_id, preview, span

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
    user_role: str = Field(default="", validation_alias=AliasChoices("user_role", "userRole"))
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    execution_mode: str = Field(default="auto", validation_alias=AliasChoices("execution_mode", "executionMode"))


def _parse_attachments(raw: dict[str, Any]) -> list[dict[str, Any]]:
    rows = raw.get("attachments")
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = {
            "id": _pick_str(row, "id"),
            "name": _pick_str(row, "name"),
            "mime": _pick_str(row, "mime"),
            "url": _pick_str(row, "url"),
            "kind": _pick_str(row, "kind") or "document",
        }
        text_inline = _pick_str(row, "text", "content")
        if text_inline:
            item["text"] = text_inline
        if item["id"] or item["name"] or item["url"] or text_inline:
            out.append(item)
    return out


def _parse_execution_mode(raw: dict[str, Any]) -> str:
    mode = _pick_str(raw, "execution_mode", "executionMode").lower() or "auto"
    return mode if mode in ("auto", "plan", "fast") else "auto"


def _pick_str(raw: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = raw.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _pick_int(raw: dict[str, Any], *keys: str, default: int = 0) -> int:
    for key in keys:
        value = raw.get(key)
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return default


def _parse_chat_request(raw: object) -> ChatRequest | JSONResponse:
    if not isinstance(raw, dict):
        logger.warning("[ai/chat] body is not object: %r", raw)
        return JSONResponse(
            status_code=422,
            content={"code": 42200, "message": "请求体必须是 JSON 对象"},
        )

    limit = _pick_int(raw, "limit", default=_DEFAULT_HISTORY_LIMIT)
    limit = max(1, min(50, limit))
    question = _pick_str(raw, "question")
    session_id = _pick_str(raw, "session_id", "sessionId")

    if not question:
        return JSONResponse(
            status_code=422,
            content={"code": 42200, "message": "question 不能为空"},
        )
    if not session_id:
        return JSONResponse(
            status_code=422,
            content={"code": 42200, "message": "session_id 不能为空"},
        )

    return ChatRequest(
        question=question,
        session_id=session_id,
        user_id=_pick_int(raw, "user_id", "userId"),
        account=_pick_str(raw, "account"),
        user_name=_pick_str(raw, "user_name", "userName"),
        limit=limit,
        access_token=_pick_str(raw, "access_token", "accessToken"),
        user_role=_pick_str(raw, "user_role", "userRole"),
        attachments=_parse_attachments(raw),
        execution_mode=_parse_execution_mode(raw),
    )


def _require_ops_token(x_ops_token: str | None) -> JSONResponse | None:
    expected = (os.getenv("AGENT_OPS_TOKEN") or "").strip()
    if not expected or x_ops_token != expected:
        return JSONResponse(status_code=403, content={"code": 40300, "message": "forbidden"})
    return None


@router.post("/ai/ops/bug-scan")
def ops_bug_scan(x_ops_token: str | None = Header(default=None, alias="X-Ops-Token")):
    """开发者手动触发 Bug Ops 巡检（不对用户开放）。"""
    denied = _require_ops_token(x_ops_token)
    if denied:
        return denied

    from server.bug_agent_runner import scan_and_run_pending

    ran = scan_and_run_pending()
    return {"ok": True, "handled": len(ran), "items": ran}


@router.post("/ai/ops/btc-daily-test")
def ops_btc_daily_test(x_ops_token: str | None = Header(default=None, alias="X-Ops-Token")):
    """立即发送一条 BTC 定投日报到 NAPCAT_ALERT_QQ（测定时推送与持仓盈亏）。"""
    denied = _require_ops_token(x_ops_token)
    if denied:
        return denied

    from service.btc_daily_brief import send_daily_brief_to_developer

    result = send_daily_brief_to_developer(force=True)
    status = 200 if result.get("ok") else 502
    return JSONResponse(status_code=status, content=result)


@router.post("/ai/ops/napcat-test")
def ops_napcat_test(x_ops_token: str | None = Header(default=None, alias="X-Ops-Token")):
    """向 NAPCAT_ALERT_QQ 发送一条测试私聊（验证 NapCat HTTP 与登录状态）。"""
    denied = _require_ops_token(x_ops_token)
    if denied:
        return denied

    from utils.qq.napcat_notify import napcat_configured, send_developer_alert

    if not napcat_configured():
        return JSONResponse(
            status_code=503,
            content={
                "code": 50300,
                "message": "NapCat 未配置：请设置 NAPCAT_HTTP_URL、NAPCAT_ALERT_QQ，并确认 NAPCAT_NOTIFY_ENABLED=true",
            },
        )
    result = send_developer_alert(
        title="NapCat 连通测试",
        message="来自博客 Agent 的测试消息；若收到说明 QQ 告警通道正常。",
        severity="high",
        trace_id=new_trace_id(),
        event="ops.napcat_test",
    )
    status = 200 if result.get("ok") else 502
    return JSONResponse(status_code=status, content={"ok": bool(result.get("ok")), **result})


@router.post("/ai/chat")
async def llm_chat(request: Request):
    try:
        raw = await request.json()
    except Exception as exc:
        logger.warning("[ai/chat] invalid json: %s", exc)
        return JSONResponse(
            status_code=422,
            content={"code": 42200, "message": "JSON 格式错误"},
        )

    parsed = _parse_chat_request(raw)
    if isinstance(parsed, JSONResponse):
        return parsed
    body = parsed

    trace_id = new_trace_id()
    logger.info(
        "[ai/chat] ok session_id=%s user_id=%s limit=%s",
        body.session_id,
        body.user_id,
        body.limit,
    )
    if not body.account or not body.user_name or not body.user_id:
        return JSONResponse(
            status_code=400,
            content={"code": 40000, "message": "用户不存在！"},
        )

    def sse_stream() -> Iterator[str]:
        with span(
            "request",
            trace_id=trace_id,
            session_id=body.session_id,
            user_id=body.user_id,
            question_preview=preview(body.question),
        ):
            bind_trace(
                trace_id=trace_id,
                session_id=body.session_id,
                user_id=body.user_id,
            )
            try:
                result = get_agent_entry().run(
                    question=body.question,
                    session_id=body.session_id,
                    user_id=body.user_id,
                    limit=body.limit,
                    access_token=body.access_token,
                    trace_id=trace_id,
                    channel="web",
                    user_name=body.user_name,
                    account=body.account,
                    user_role=body.user_role,
                    attachments=body.attachments,
                    execution_mode=body.execution_mode,
                )
                yield from result.iter_sse()
            except Exception as exc:
                logger.exception(
                    "[ai/chat] failed session_id=%s trace_id=%s",
                    body.session_id,
                    trace_id,
                )
                payload = json.dumps(
                    {"code": 50000, "message": "服务暂时不可用，请稍后重试"},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={**SSE_HEADERS, "X-Trace-Id": trace_id},
    )


class NoteCommentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    note_id: str = Field(validation_alias=AliasChoices("note_id", "noteId"))
    job_id: str = Field(default="", validation_alias=AliasChoices("job_id", "jobId"))
    question: str
    note_title: str = Field(default="", validation_alias=AliasChoices("note_title", "noteTitle"))
    session_id: str = Field(default="", validation_alias=AliasChoices("session_id", "sessionId"))
    user_id: int = Field(default=0, validation_alias=AliasChoices("user_id", "userId"))
    limit: int = Field(default=_DEFAULT_HISTORY_LIMIT, ge=1, le=50)


@router.post("/ai/internal/note-comment")
async def internal_note_comment(
    request: Request,
    x_ops_token: str | None = Header(default=None, alias="X-Ops-Token"),
):
    """
    笔记发布后由 Java 内网调用：强制 commit_user，生成回复并写入 notes.agent_reply。
    """
    denied = _require_ops_token(x_ops_token)
    if denied:
        return denied

    try:
        raw = await request.json()
    except Exception as exc:
        logger.warning("[ai/internal/note-comment] invalid json: %s", exc)
        return JSONResponse(
            status_code=422,
            content={"code": 42200, "message": "JSON 格式错误"},
        )

    if not isinstance(raw, dict):
        return JSONResponse(status_code=422, content={"code": 42200, "message": "请求体必须是 JSON 对象"})

    note_id = _pick_str(raw, "note_id", "noteId")
    job_id = _pick_str(raw, "job_id", "jobId")
    question = _pick_str(raw, "question")
    if not note_id or not question:
        return JSONResponse(
            status_code=422,
            content={"code": 42200, "message": "note_id 与 question 不能为空"},
        )
    if not job_id:
        return JSONResponse(
            status_code=422,
            content={"code": 42200, "message": "job_id 不能为空"},
        )

    body = NoteCommentRequest(
        note_id=note_id,
        job_id=job_id,
        question=question,
        note_title=_pick_str(raw, "note_title", "noteTitle"),
        session_id=_pick_str(raw, "session_id", "sessionId"),
        user_id=_pick_int(raw, "user_id", "userId"),
        limit=max(1, min(50, _pick_int(raw, "limit", default=_DEFAULT_HISTORY_LIMIT))),
    )

    trace_id = new_trace_id()
    with span("note.comment.request", note_id=body.note_id, question_preview=preview(body.question)):
        try:
            result = get_agent_entry().run_note_comment_job(
                note_id=body.note_id,
                job_id=body.job_id,
                question=body.question,
                note_title=body.note_title,
                session_id=body.session_id,
                user_id=body.user_id,
                limit=body.limit,
                trace_id=trace_id,
            )
            return {
                "ok": True,
                "trace_id": trace_id,
                "note_id": body.note_id,
                "saved": bool(result.get("saved")),
                "reply": result.get("final_answer") or "",
            }
        except Exception as exc:
            logger.exception(
                "[ai/internal/note-comment] failed note_id=%s trace_id=%s",
                body.note_id,
                trace_id,
            )
            return JSONResponse(
                status_code=500,
                content={"code": 50000, "message": f"笔记评论生成失败：{exc}"},
            )

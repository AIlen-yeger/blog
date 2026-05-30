from __future__ import annotations



import json

import logging

import logging.handlers

import time

import uuid

from contextlib import contextmanager

from contextvars import ContextVar, copy_context

from datetime import datetime, timezone

from pathlib import Path

from typing import Any, Callable



from utils.agent_log_config import DEFAULT_LOG_DIR, LOG_STREAMS, resolve_log_dir



_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")

_intent: ContextVar[str] = ContextVar("intent", default="-")

_session_id: ContextVar[str] = ContextVar("session_id", default="-")

_user_id: ContextVar[int] = ContextVar("user_id", default=0)



# 长留摘要：每请求关键结果 + 告警向事件（明细见 trace.jsonl）

_SUMMARY_EVENTS = frozenset(

    {

        "request.end",

        "intent.classified",

        "react.done",

        "react.fallback",

        "react.error",

        "react.skip",

        "history.saved",

    }

)





def new_trace_id() -> str:

    return uuid.uuid4().hex[:16]





def bind_trace(

    *,

    trace_id: str | None = None,

    intent: str | None = None,

    session_id: str | None = None,

    user_id: int | None = None,

) -> None:

    if trace_id is not None:

        _trace_id.set(trace_id)

    if intent is not None:

        _intent.set(intent)

    if session_id is not None:

        _session_id.set(session_id or "-")

    if user_id is not None:

        _user_id.set(int(user_id))





def current_trace() -> dict[str, Any]:

    return {

        "trace_id": _trace_id.get(),

        "intent": _intent.get(),

        "session_id": _session_id.get(),

        "user_id": _user_id.get(),

    }





def preview(text: str, max_len: int = 200) -> str:

    s = (text or "").replace("\n", " ").strip()

    return s if len(s) <= max_len else s[: max_len - 1] + "…"





def redact_args(args: dict[str, Any]) -> dict[str, Any]:

    skip = {"access_token", "token", "password", "authorization"}

    out: dict[str, Any] = {}

    for k, v in (args or {}).items():

        if k.lower() in skip:

            out[k] = "<redacted>"

        else:

            out[k] = preview(str(v), 120)

    return out





def _payload_from_record(record: logging.LogRecord) -> dict[str, Any]:

    extra = getattr(record, "extra", None)

    if isinstance(extra, dict):

        return extra

    return {"event": record.getMessage(), **current_trace()}





class _IntentLogFilter(logging.Filter):

    """按日志记录时的 intent 字段分流（不依赖写文件时的 contextvars）。"""



    def __init__(self, intent: str) -> None:

        super().__init__()

        self.intent = intent



    def filter(self, record: logging.LogRecord) -> bool:

        payload = _payload_from_record(record)

        return payload.get("intent") == self.intent





class _SummaryLogFilter(logging.Filter):

    """仅保留请求摘要、业务结果与 WARN/ERROR 级事件。"""



    def filter(self, record: logging.LogRecord) -> bool:

        if record.levelno >= logging.WARNING:

            return True

        payload = _payload_from_record(record)

        event = str(payload.get("event") or record.getMessage() or "")

        if event in _SUMMARY_EVENTS:

            return True

        if event.endswith(".error"):

            return True

        if event == "tool.end" and payload.get("ok") is False:

            return True

        return False





class JsonLineFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:

        payload: dict[str, Any] = {

            "ts": datetime.now(timezone.utc).isoformat(),

            "level": record.levelname,

            "logger": record.name,

            "msg": record.getMessage(),

        }

        extra = getattr(record, "extra", None)

        if isinstance(extra, dict):

            payload.update(extra)

        else:

            payload.update(current_trace())

        if record.exc_info:

            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)





def _daily_jsonl_handler(log_dir: Path, name: str) -> logging.Handler:

    """按 UTC 午夜轮转；backupCount=0，旧文件由 prune 脚本按策略删除。"""

    path = log_dir / f"{name}.jsonl"

    handler = logging.handlers.TimedRotatingFileHandler(

        path,

        when="midnight",

        interval=1,

        backupCount=0,

        encoding="utf-8",

        utc=True,

    )

    handler.suffix = "%Y-%m-%d"

    return handler





def setup_agent_logging(log_dir: str = DEFAULT_LOG_DIR) -> None:

    """初始化 agent.trace：summary（长留）+ trace（短留明细）+ error（长留）+ intent 分流。"""

    directory = resolve_log_dir(log_dir)

    directory.mkdir(parents=True, exist_ok=True)



    root = logging.getLogger("agent.trace")

    root.setLevel(logging.INFO)

    root.propagate = False

    if root.handlers:

        return



    fmt = JsonLineFormatter()



    trace = _daily_jsonl_handler(directory, "trace")

    trace.setFormatter(fmt)

    root.addHandler(trace)



    summary = _daily_jsonl_handler(directory, "summary")

    summary.addFilter(_SummaryLogFilter())

    summary.setFormatter(fmt)

    root.addHandler(summary)



    err = _daily_jsonl_handler(directory, "error")

    err.setLevel(logging.ERROR)

    err.setFormatter(fmt)

    root.addHandler(err)



    for intent in ("music", "chat", "commit_user", "bug"):

        if intent not in LOG_STREAMS:

            continue

        handler = _daily_jsonl_handler(directory, intent)

        handler.addFilter(_IntentLogFilter(intent))

        handler.setFormatter(fmt)

        root.addHandler(handler)





trace_log = logging.getLogger("agent.trace")





def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:

    """写入结构化事件；在写入时快照 trace，避免 SSE/线程丢失 contextvars。"""

    payload = {
        "event": event,
        "level": logging.getLevelName(level),
        **current_trace(),
        **fields,
    }

    trace_log.log(level, event, extra={"extra": payload})

    if level >= logging.ERROR:
        try:
            from utils.bug_agent_scheduler import queue_bug_agent_from_log

            queue_bug_agent_from_log(payload)
        except Exception:
            pass





@contextmanager

def span(event: str, **fields: Any):

    t0 = time.perf_counter()

    log_event(f"{event}.start", **fields)

    try:

        yield

        log_event(

            f"{event}.end",

            latency_ms=int((time.perf_counter() - t0) * 1000),

            **fields,

        )

    except Exception as exc:

        log_event(

            f"{event}.error",

            level=logging.ERROR,

            latency_ms=int((time.perf_counter() - t0) * 1000),

            error=str(exc),

            **fields,

        )

        raise





def run_in_trace_context(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:

    """在线程池等子线程中保留当前 trace 上下文。"""

    ctx = copy_context()

    return ctx.run(fn, *args, **kwargs)





def tool_result_status(content: str) -> tuple[bool, int]:

    """判断工具返回是否业务失败，以及建议日志级别。"""

    text = (content or "").strip()

    if not text:

        return False, logging.WARNING



    if text.startswith("{"):

        try:

            data = json.loads(text)

        except json.JSONDecodeError:

            data = None

        if isinstance(data, dict):

            msg = str(data.get("message") or data.get("error") or "")

            lower = msg.lower()

            if "搜索失败" in msg or "mcp" in lower and "失败" in msg:

                return False, logging.ERROR

            if msg and any(k in msg for k in ("失败", "异常", "未登录", "错误")):

                return False, logging.WARNING

            return True, logging.INFO



    if any(k in text for k in ("失败", "异常", "Error", "error")):

        return False, logging.ERROR

    return True, logging.INFO



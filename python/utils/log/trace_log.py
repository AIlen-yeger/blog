from __future__ import annotations

import json
import logging
import logging.handlers
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from utils.log.agent_log_config import (
    ARCHIVE_SUBDIR,
    LOG_STREAMS,
    resolve_log_dir,
)


def _log_timestamp() -> str:
    """JSONL 行内 ts：本机本地时区（Windows 上一般为 UTC+8）。"""
    return datetime.now().astimezone().isoformat()


_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")
_intent: ContextVar[str] = ContextVar("intent", default="-")
_session_id: ContextVar[str] = ContextVar("session_id", default="-")
_user_id: ContextVar[int] = ContextVar("user_id", default=0)
_request_models: ContextVar[list[str] | None] = ContextVar("request_models", default=None)
_request_trace: ContextVar[dict[str, Any] | None] = ContextVar("request_trace", default=None)

# 长留摘要：每请求关键结果 + 告警向事件（明细见 trace.jsonl）
_SUMMARY_EVENTS = frozenset(
    {
        "request.end",
        "intent.classified",
        "intent.override",
        "intent.fallback",
        "react.done",
        "react.fallback",
        "react.error",
        "react.skip",
        "history.saved",
        "chat.done",
        "llm.usage",
        "prompt.assembled",
        "react.tokens",
        "agent.log.ready",
        "request.tokens",
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
    _merge_request_trace(current_trace())


def _merge_request_trace(values: dict[str, Any]) -> None:
    """跨 SSE yield / 线程池时保留本请求 trace 字段（供 summary 使用）。"""
    acc = dict(_request_trace.get() or {})
    for key, val in values.items():
        if key == "user_id":
            uid = int(val or 0)
            if uid > 0 or "user_id" not in acc:
                acc["user_id"] = uid
            continue
        text = str(val or "").strip()
        if text and text != "-":
            acc[key] = text
    _request_trace.set(acc)


def request_trace_fields() -> dict[str, Any]:
    """当前请求累积的 trace（优先于可能已丢失的 contextvars）。"""
    return dict(_request_trace.get() or {})


def reset_request_trace() -> None:
    _request_trace.set({})


def trace_fields_for_log(**fields: Any) -> dict[str, Any]:
    """合并 contextvars、请求快照与显式字段；显式字段优先。"""
    merged: dict[str, Any] = {}
    merged.update(current_trace())
    merged.update(request_trace_fields())
    merged.update(fields)
    return merged


def bind_trace_from_state(state: dict[str, Any], *, intent: str | None = None) -> None:
    """从 AgentState / 请求 dict 恢复 trace（SSE 子阶段调用）。"""
    tid = (state.get("trace_id") or "").strip()
    bind_trace(
        trace_id=tid or None,
        session_id=state.get("session_id") or None,
        user_id=int(state.get("user_id") or 0),
        intent=intent,
    )


def current_trace() -> dict[str, Any]:
    return {
        "trace_id": _trace_id.get(),
        "intent": _intent.get(),
        "session_id": _session_id.get(),
        "user_id": _user_id.get(),
    }


def reset_request_models() -> None:
    """新请求开始时清空本次已调用模型列表。"""
    _request_models.set([])


def reset_request_context() -> None:
    reset_request_models()
    reset_request_trace()
    try:
        from utils.log.token_usage import reset_request_tokens

        reset_request_tokens()
    except Exception:
        pass


def record_model(model_name: str) -> None:
    """记录本次请求实际调用过的模型（去重、保序）。"""
    name = (model_name or "").strip()
    if not name:
        return
    models = _request_models.get()
    if models is None:
        models = []
    if name not in models:
        models.append(name)
    _request_models.set(models)


def request_model_fields() -> dict[str, Any]:
    """供 summary 日志输出：model=最后一次调用，models_used=本次全部。"""
    models = _request_models.get() or []
    if not models:
        return {}
    fields: dict[str, Any] = {"models_used": models, "model": models[-1]}
    if len(models) == 1:
        return fields
    return fields


def preview(text: str, max_len: int = 200) -> str:
    s = (text or "").replace("\n", " ").strip()
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def answer_log_fields(text: str, *, max_len: int | None = None) -> dict[str, Any]:
    """摘要日志里的回复预览：默认较长，并标明是否截断。"""
    if max_len is None:
        try:
            from utils.log.agent_log_config import SUMMARY_ANSWER_PREVIEW_LEN

            max_len = SUMMARY_ANSWER_PREVIEW_LEN
        except Exception:
            max_len = 800
    raw = (text or "").strip()
    limit = max(200, int(max_len))
    return {
        "answer_length": len(raw),
        "final_preview": preview(raw, limit),
        "preview_truncated": len(raw) > limit,
    }


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
            "ts": _log_timestamp(),
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


def _archive_namer(default_name: str) -> str:
    """轮转文件放入 archive/，避免与正在写入的 *.jsonl 混在同一层。"""
    p = Path(default_name)
    archive = p.parent / ARCHIVE_SUBDIR
    archive.mkdir(parents=True, exist_ok=True)
    return str(archive / p.name)


def _daily_jsonl_handler(log_dir: Path, name: str) -> logging.Handler:
    """按本地午夜轮转；旧文件进 archive/，由 prune 按保留天数删除。"""
    path = log_dir / f"{name}.jsonl"
    handler = logging.handlers.TimedRotatingFileHandler(
        path,
        when="midnight",
        interval=1,
        backupCount=0,
        encoding="utf-8",
        utc=False,
    )
    handler.suffix = "%Y-%m-%d"
    handler.namer = _archive_namer
    return handler


def setup_agent_logging(log_dir: str | None = None) -> None:
    """初始化 agent.trace：summary + trace + error + 按 intent 分流；轮转进 archive/。"""
    from utils.log.agent_log_config import migrate_wrong_log_dir, resolve_log_dir
    from utils.log.agent_log_prune import migrate_log_layout

    directory = resolve_log_dir(log_dir)
    migrate_log_layout(directory)
    merged = migrate_wrong_log_dir(directory)
    for line in merged:
        logging.getLogger(__name__).info("[agent_log] %s", line)

    root = logging.getLogger("agent.trace")
    root.setLevel(logging.INFO)
    root.propagate = False
    if root.handlers:
        logging.getLogger(__name__).warning(
            "[agent_log] handlers 已存在，未重新绑定目录；请完全重启进程后日志才写入 %s",
            directory.resolve(),
        )
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

    _write_startup_marker(directory)


def _write_startup_marker(directory: Path) -> None:
    """启动时写一行，便于确认 log/agent/*.jsonl 已创建。"""
    import json
    from datetime import datetime, timezone

    payload = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(),
        "event": "agent.log.ready",
        "log_dir": str(directory.resolve()),
        "hint": "token 见 llm.usage / request.tokens；勿在 utils/log/agent 找旧文件",
    }
    path = directory / "summary.jsonl"
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError as exc:
        logging.getLogger(__name__).warning("[agent_log] startup marker failed: %s", exc)


trace_log = logging.getLogger("agent.trace")

# 同步打到 uvicorn 控制台，便于本地调试（仍写 jsonl）
_CONSOLE_EVENTS = frozenset(
    {
        "intent.classified",
        "llm.usage",
        "prompt.assembled",
        "react.done",
        "request.tokens",
        "request.end",
    }
)


def _console_line(payload: dict[str, Any]) -> str:
    event = str(payload.get("event") or "")
    tid = payload.get("trace_id") or "-"
    if event == "llm.usage":
        return (
            f"[token] {event} trace={tid} phase={payload.get('phase')} "
            f"prompt={payload.get('prompt_tokens')} completion={payload.get('completion_tokens')} "
            f"total={payload.get('total_tokens')} est={payload.get('estimated')}"
        )
    if event == "request.tokens":
        return (
            f"[token] request trace={tid} total={payload.get('token_total')} "
            f"prompt={payload.get('token_prompt')} completion={payload.get('token_completion')} "
            f"calls={payload.get('token_calls')} phases={payload.get('token_by_phase')}"
        )
    if event == "request.end":
        return (
            f"[agent] request.end trace={tid} intent={payload.get('intent')} "
            f"ms={payload.get('latency_ms')} tokens={payload.get('token_total', 0)} "
            f"q={preview(str(payload.get('question_preview') or ''), 60)}"
        )
    if event == "react.done":
        return (
            f"[agent] react.done trace={tid} subgraph={payload.get('subgraph')} "
            f"rounds={payload.get('rounds')} tokens={payload.get('token_total', '-')}"
        )
    if event == "intent.classified":
        return (
            f"[agent] intent={payload.get('intent')} trace={tid} "
            f"q={preview(str(payload.get('question_preview') or ''), 60)}"
        )
    if event == "prompt.assembled":
        return (
            f"[prompt] trace={tid} phase={payload.get('phase')} "
            f"system_tokens={payload.get('system_tokens')}"
        )
    return f"[agent] {event} trace={tid}"


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """写入结构化事件；在写入时快照 trace，避免 SSE/线程丢失 contextvars。"""
    payload = {
        "event": event,
        "level": logging.getLevelName(level),
        **trace_fields_for_log(**fields),
        **fields,
    }
    trace_log.log(level, event, extra={"extra": payload})

    if event in _CONSOLE_EVENTS:
        logging.getLogger("uvicorn.error").info(_console_line(payload))

    if level >= logging.ERROR:
        try:
            from utils.scheduler.bug_agent_scheduler import queue_bug_agent_from_log

            queue_bug_agent_from_log(payload)
        except Exception:
            pass


@contextmanager
def span(event: str, **fields: Any):
    t0 = time.perf_counter()
    if event == "request":
        reset_request_context()

    log_event(f"{event}.start", **fields)
    try:
        yield
        end_fields = trace_fields_for_log(**fields)
        if event == "request":
            end_fields.update(request_model_fields())
            try:
                tid = str(end_fields.get("trace_id") or fields.get("trace_id") or "").strip()
                if tid:
                    from utils.log.token_usage import finish_request_tokens

                    end_fields.update(finish_request_tokens(tid))
            except Exception:
                pass

        log_event(
            f"{event}.end",
            latency_ms=int((time.perf_counter() - t0) * 1000),
            **end_fields,
        )
    except Exception as exc:
        log_event(
            f"{event}.error",
            level=logging.ERROR,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            error=str(exc),
            **trace_fields_for_log(**fields),
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

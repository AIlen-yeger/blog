"""LLM token 用量：优先读 API usage，缺失时用 tiktoken 估算。"""

from __future__ import annotations

import logging
import threading
from contextvars import ContextVar
from typing import Any

from utils.log.trace_log import current_trace, log_event

_acc_var: ContextVar[dict[str, Any] | None] = ContextVar("request_token_acc", default=None)
_trace_acc: dict[str, dict[str, Any]] = {}
_trace_lock = threading.Lock()


def _empty_acc() -> dict[str, Any]:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "calls": 0,
        "estimated_calls": 0,
        "by_phase": {},
    }


def _resolve_trace_id(trace_id: str | None = None) -> str:
    tid = (trace_id or current_trace().get("trace_id") or "").strip()
    return tid if tid and tid != "-" else ""


def reset_request_tokens() -> None:
    _acc_var.set(_empty_acc())


def begin_request_tokens(trace_id: str) -> None:
    """SSE / 流式入口：按 trace_id 初始化累计（避免 contextvars 在 generator 结束时丢失）。"""
    tid = (trace_id or "").strip()
    acc = _empty_acc()
    _acc_var.set(acc)
    if tid:
        with _trace_lock:
            _trace_acc[tid] = acc


def finish_request_tokens(trace_id: str) -> dict[str, Any]:
    """请求结束时取出累计并写 request.tokens 摘要。"""
    tid = (trace_id or "").strip()
    if not tid:
        return {}
    with _trace_lock:
        acc = _trace_acc.pop(tid, None)
    if not acc or not acc.get("calls"):
        return {}
    fields = {
        "token_prompt": acc["prompt_tokens"],
        "token_completion": acc["completion_tokens"],
        "token_total": acc["total_tokens"],
        "token_calls": acc["calls"],
        "token_estimated_calls": acc["estimated_calls"],
        "token_by_phase": acc.get("by_phase"),
    }
    log_event("request.tokens", trace_id=tid, **fields)
    return fields


def _acc(trace_id: str | None = None) -> dict[str, Any]:
    tid = _resolve_trace_id(trace_id)
    if tid:
        with _trace_lock:
            stored = _trace_acc.get(tid)
            if stored is not None:
                return stored
            acc = _empty_acc()
            _trace_acc[tid] = acc
            _acc_var.set(acc)
            return acc
    acc = _acc_var.get()
    if acc is None:
        reset_request_tokens()
        acc = _acc_var.get()
    assert acc is not None
    return acc


def _usage_from_metadata(meta: Any) -> tuple[int, int, int] | None:
    if not meta:
        return None
    if isinstance(meta, dict):
        tu = meta.get("token_usage") or meta.get("usage")
        if isinstance(tu, dict):
            p = int(tu.get("prompt_tokens") or tu.get("input_tokens") or 0)
            c = int(tu.get("completion_tokens") or tu.get("output_tokens") or 0)
            t = int(tu.get("total_tokens") or (p + c))
            if p or c or t:
                return p, c, t
    return None


def usage_from_ai_message(msg: Any) -> tuple[int, int, int] | None:
    """从 LangChain AIMessage / chunk 解析 usage。"""
    for attr in ("usage_metadata", "response_metadata"):
        raw = getattr(msg, attr, None)
        if attr == "usage_metadata" and raw is not None:
            if hasattr(raw, "get"):
                p = int(raw.get("input_tokens") or raw.get("prompt_tokens") or 0)
                c = int(raw.get("output_tokens") or raw.get("completion_tokens") or 0)
                t = int(raw.get("total_tokens") or (p + c))
            else:
                p = int(getattr(raw, "input_tokens", 0) or getattr(raw, "prompt_tokens", 0) or 0)
                c = int(
                    getattr(raw, "output_tokens", 0) or getattr(raw, "completion_tokens", 0) or 0
                )
                t = int(getattr(raw, "total_tokens", 0) or (p + c))
            if p or c or t:
                return p, c, t
        if attr == "response_metadata":
            parsed = _usage_from_metadata(raw)
            if parsed:
                return parsed
    return None


def estimate_messages_prompt_tokens(messages: list[Any]) -> int:
    from server.skills_server.prompt_trace import estimate_messages_tokens

    return int(estimate_messages_tokens(messages).get("total_tokens") or 0)


def estimate_text_tokens(text: str) -> int:
    from server.skills_server.prompt_trace import estimate_tokens

    return estimate_tokens(text or "")[0]


def record_llm_usage(
    *,
    phase: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    estimated: bool = False,
    level: int = logging.INFO,
    trace_id: str | None = None,
    **extra: Any,
) -> None:
    p = max(0, int(prompt_tokens))
    c = max(0, int(completion_tokens))
    t = p + c
    acc = _acc(trace_id)
    acc["prompt_tokens"] += p
    acc["completion_tokens"] += c
    acc["total_tokens"] += t
    acc["calls"] += 1
    if estimated:
        acc["estimated_calls"] += 1
    by_phase: dict[str, dict[str, int]] = acc["by_phase"]
    bucket = by_phase.setdefault(
        phase,
        {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0},
    )
    bucket["prompt_tokens"] += p
    bucket["completion_tokens"] += c
    bucket["total_tokens"] += t
    bucket["calls"] += 1

    log_event(
        "llm.usage",
        level,
        phase=phase,
        model=(model or "").strip() or "-",
        prompt_tokens=p,
        completion_tokens=c,
        total_tokens=t,
        estimated=estimated,
        request_prompt_tokens=acc["prompt_tokens"],
        request_completion_tokens=acc["completion_tokens"],
        request_total_tokens=acc["total_tokens"],
        **extra,
    )


def record_from_response(
    *,
    phase: str,
    model: str,
    messages: list[Any] | None = None,
    response: Any = None,
    completion_text: str = "",
    trace_id: str | None = None,
    **extra: Any,
) -> None:
    usage = usage_from_ai_message(response) if response is not None else None
    if usage:
        p, c, _ = usage
        record_llm_usage(
            phase=phase,
            model=model,
            prompt_tokens=p,
            completion_tokens=c,
            estimated=False,
            trace_id=trace_id,
            **extra,
        )
        return

    p = estimate_messages_prompt_tokens(messages or [])
    if response is not None:
        content = getattr(response, "content", None) or completion_text
        c = estimate_text_tokens(str(content or ""))
    else:
        c = estimate_text_tokens(completion_text)
    record_llm_usage(
        phase=phase,
        model=model,
        prompt_tokens=p,
        completion_tokens=c,
        estimated=True,
        trace_id=trace_id,
        **extra,
    )


def log_prompt_assembled(
    *,
    phase: str,
    system_prompt: str,
    intent: str = "",
    channel: str = "",
) -> None:
    """记录进模型前的 system 体量（本地估算，不计入 request 累计 LLM 账单）。"""
    tok = estimate_text_tokens(system_prompt)
    log_event(
        "prompt.assembled",
        phase=phase,
        intent=intent or None,
        channel=channel or None,
        system_chars=len(system_prompt or ""),
        system_tokens=tok,
        estimated=True,
    )


def record_react_conversation(
    *,
    subgraph: str,
    model: str,
    messages: list[Any],
    tool_rounds: int = 0,
) -> None:
    """ReAct 结束：按整条 message 链估算（补充各轮 llm.usage 未带 API usage 时）。"""
    stats = None
    try:
        from server.skills_server.prompt_trace import estimate_messages_tokens

        stats = estimate_messages_tokens(messages)
    except Exception:
        pass
    total = int((stats or {}).get("total_tokens") or 0)
    log_event(
        "react.tokens",
        subgraph=subgraph,
        model=model,
        message_count=len(messages),
        tool_rounds=tool_rounds,
        messages_total_tokens=total,
        messages_by_kind=(stats or {}).get("by_kind"),
        estimated=True,
    )


def request_token_summary_fields(trace_id: str | None = None) -> dict[str, Any]:
    acc = _acc(trace_id)
    if not acc or not acc.get("calls"):
        return {}
    return {
        "token_prompt": acc["prompt_tokens"],
        "token_completion": acc["completion_tokens"],
        "token_total": acc["total_tokens"],
        "token_calls": acc["calls"],
        "token_estimated_calls": acc["estimated_calls"],
        "token_by_phase": acc.get("by_phase"),
    }

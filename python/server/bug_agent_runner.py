"""Bug Ops 内部运行器：定时巡检 + 严重错误触发，不对用户暴露。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from server.route_graph.bug_route import run_bug_react
from server.state import AgentState
from utils.agent_log_config import resolve_log_dir, state_dir
from utils.agent_log_reader import list_recent_errors
from utils.trace_log import log_event, new_trace_id, preview

logger = logging.getLogger(__name__)

_SEVERE_EVENTS = frozenset(
    {
        "react.error",
        "bug.error",
        "request.error",
        "tool.error",
        "intent.classify.error",
    }
)

_STATE_FILE = "bug_agent_state.json"


def _state_path() -> Path:
    d = state_dir()
    d.mkdir(parents=True, exist_ok=True)
    legacy = resolve_log_dir() / _STATE_FILE
    path = d / _STATE_FILE
    if legacy.is_file() and not path.is_file():
        try:
            legacy.rename(path)
            logger.info("[bug_agent] migrated state -> %s", path)
        except OSError:
            return legacy
    return path


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.is_file():
        return {"processed": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("processed"), dict):
            return data
    except Exception:
        logger.warning("[bug_ops] corrupt state file, reset")
    return {"processed": {}}


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    processed = state.get("processed") or {}
    if len(processed) > 500:
        # 只保留最近 500 条指纹，避免状态文件无限涨
        items = sorted(processed.items(), key=lambda x: x[1].get("at", ""), reverse=True)[:500]
        processed = dict(items)
        state["processed"] = processed
    path.write_text(json.dumps(state, ensure_ascii=False, indent=0), encoding="utf-8")


def event_fingerprint(row: dict[str, Any]) -> str:
    tid = str(row.get("trace_id") or "-")
    event = str(row.get("event") or row.get("msg") or "")
    ts = str(row.get("ts") or "")
    return f"{tid}|{event}|{ts}"


def classify_severity(row: dict[str, Any]) -> str:
    event = str(row.get("event") or "")
    level = str(row.get("level") or "").upper()
    if level == "ERROR" and event in _SEVERE_EVENTS:
        return "critical"
    if level == "ERROR":
        return "high"
    if event in ("react.fallback", "tool.end") and row.get("ok") is False:
        return "high"
    if level == "WARNING":
        return "medium"
    return "low"


def should_auto_trigger(row: dict[str, Any], *, min_severity: str) -> bool:
    order = ("low", "medium", "high", "critical")
    sev = classify_severity(row)
    try:
        return order.index(sev) >= order.index(min_severity)
    except ValueError:
        return False


def is_already_processed(fp: str) -> bool:
    return fp in (_load_state().get("processed") or {})


def mark_processed(fp: str, *, incident_id: str, trigger: str) -> None:
    state = _load_state()
    processed = state.setdefault("processed", {})
    processed[fp] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "incident_id": incident_id,
        "trigger": trigger,
    }
    _save_state(state)


def is_napcat_sent(fp: str) -> bool:
    return fp in (_load_state().get("napcat_sent") or {})


def mark_napcat_sent(fp: str) -> None:
    state = _load_state()
    sent = state.setdefault("napcat_sent", {})
    sent[fp] = datetime.now(timezone.utc).isoformat()
    if len(sent) > 500:
        items = sorted(sent.items(), key=lambda x: x[1], reverse=True)[:500]
        state["napcat_sent"] = dict(items)
    _save_state(state)


def try_send_napcat_error_alert(payload: dict[str, Any], *, severity: str) -> dict[str, Any] | None:
    """严重错误时即时 QQ 私聊（与 Bug Ops 分析并行，同指纹只发一次）。"""
    from config.config import AgentConfig
    from utils.qq.napcat_notify import napcat_configured, send_developer_alert

    cfg = AgentConfig()
    if not cfg.napcat_alert_on_error or not napcat_configured():
        return None

    fp = event_fingerprint(payload)
    if is_napcat_sent(fp):
        return None

    event = str(payload.get("event") or "")
    msg = preview(
        str(payload.get("msg") or payload.get("error") or payload.get("exc") or ""),
        400,
    )
    title = f"Agent 错误 · {event or 'ERROR'}"
    result = send_developer_alert(
        title=title,
        message=msg,
        severity=severity,
        trace_id=str(payload.get("trace_id") or ""),
        event=event,
    )
    if result.get("ok"):
        mark_napcat_sent(fp)
    log_event(
        "napcat.alert",
        ok=bool(result.get("ok")),
        status=result.get("status"),
        severity=severity,
        event=event,
        trace_id=payload.get("trace_id"),
    )
    return result


def build_ops_task_message(
    *,
    trigger: str,
    symptoms: str,
    trace_id: str | None = None,
    severity: str = "medium",
    log_event_name: str | None = None,
) -> str:
    lines = [
        "【系统自动任务 · Bug Ops 内部排查，勿生成对用户可见的回复】",
        f"触发来源: {trigger}",
        f"严重级别: {severity}",
    ]
    if trace_id:
        lines.append(f"trace_id: {trace_id}")
    if log_event_name:
        lines.append(f"日志事件: {log_event_name}")
    lines.append(f"现象摘要: {symptoms}")
    lines.append(
        "请：读取相关日志 → 分析根因 → update_incident_record → "
        "若需人工处理则 notify_developer(severity 与现象一致)。"
    )
    return "\n".join(lines)


def run_bug_agent_internal(
    *,
    trigger: str,
    symptoms: str,
    trace_id: str | None = None,
    severity: str = "medium",
    log_event_name: str | None = None,
    source: str = "log_alert",
    user_id: int = 0,
) -> dict:
    """内部入口：不经过用户 SSE。"""
    tid = (trace_id or "").strip() or new_trace_id()
    task = build_ops_task_message(
        trigger=trigger,
        symptoms=symptoms,
        trace_id=tid,
        severity=severity,
        log_event_name=log_event_name,
    )
    state: AgentState = {
        "question": task,
        "trace_id": tid,
        "user_id": user_id,
        "trigger": trigger,
        "severity": severity,
        "source": source,
        "session_id": "",
        "limit": 4,
    }
    log_event(
        "bug.ops.start",
        trigger=trigger,
        severity=severity,
        trace_id=tid,
        source=source,
    )
    try:
        result = run_bug_react(state)
    except Exception:
        logger.exception("[bug_ops] run failed trigger=%s trace_id=%s", trigger, tid)
        log_event("bug.ops.error", trigger=trigger, trace_id=tid, level=logging.ERROR)
        return {"ok": False, "trace_id": tid, "trigger": trigger}

    log_event(
        "bug.ops.end",
        trigger=trigger,
        trace_id=tid,
        incident_id=result.get("incident_id"),
        final_preview=preview(str(result.get("final_answer") or ""), 200),
    )
    return {"ok": True, "trigger": trigger, **result}


def scan_and_run_pending(*, hours: int = 24, limit: int = 10, min_severity: str = "high") -> list[dict]:
    """定时巡检：处理未见过且达到严重度阈值的日志事件。"""
    rows = list_recent_errors(hours=max(1, hours), limit=max(1, limit * 3))
    ran: list[dict] = []
    for row in rows:
        if len(ran) >= limit:
            break
        if not should_auto_trigger(row, min_severity=min_severity):
            continue
        fp = event_fingerprint(row)
        if is_already_processed(fp):
            continue

        trace_id = str(row.get("trace_id") or "").strip() or None
        symptoms = preview(
            json.dumps(
                {
                    "event": row.get("event"),
                    "msg": row.get("msg"),
                    "error": row.get("error"),
                    "exc": row.get("exc"),
                },
                ensure_ascii=False,
            ),
            480,
        )
        sev = classify_severity(row)
        out = run_bug_agent_internal(
            trigger="scheduled_scan",
            symptoms=symptoms,
            trace_id=trace_id,
            severity=sev,
            log_event_name=str(row.get("event") or ""),
            source="scheduled_scan",
        )
        incident_id = out.get("incident_id") or f"bug_inc_{out.get('trace_id')}"
        mark_processed(fp, incident_id=str(incident_id), trigger="scheduled_scan")
        ran.append({"fingerprint": fp, "severity": sev, **out})
    return ran


def try_trigger_from_log_event(payload: dict[str, Any], *, min_severity: str = "high") -> bool:
    """由 log_event 在达到严重度阈值时调用；已处理则跳过。"""
    if not should_auto_trigger(payload, min_severity=min_severity):
        return False

    fp = event_fingerprint(payload)
    if is_already_processed(fp):
        return False

    trace_id = str(payload.get("trace_id") or "").strip() or None
    symptoms = preview(
        json.dumps(
            {k: payload.get(k) for k in ("event", "msg", "error", "exc", "subgraph")},
            ensure_ascii=False,
        ),
        480,
    )
    sev = classify_severity(payload)
    try_send_napcat_error_alert(payload, severity=sev)
    out = run_bug_agent_internal(
        trigger="error_alert",
        symptoms=symptoms,
        trace_id=trace_id,
        severity=sev,
        log_event_name=str(payload.get("event") or ""),
        source="error_alert",
    )
    incident_id = out.get("incident_id") or f"bug_inc_{out.get('trace_id')}"
    mark_processed(fp, incident_id=str(incident_id), trigger="error_alert")
    return True

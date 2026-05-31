"""Bug 运维 Agent 的 LangChain 工具。"""

from __future__ import annotations

import json

from langchain_core.tools import tool

from utils.agent_log_reader import list_recent_errors, read_log_events, read_trace_bundle
from utils.trace_log import current_trace, preview


@tool
def list_recent_agent_errors(hours: int = 72, limit: int = 20) -> str:
    """列出最近 Agent 错误事件（error.jsonl 与 summary 中的 ERROR）。
    用于用户报障或主动巡检时先看最近出了什么问题。"""
    rows = list_recent_errors(hours=max(1, min(hours, 168)), limit=max(1, min(limit, 50)))
    slim = [
        {
            "ts": r.get("ts"),
            "event": r.get("event"),
            "trace_id": r.get("trace_id"),
            "intent": r.get("intent"),
            "level": r.get("level"),
            "msg": preview(str(r.get("msg") or r.get("error") or ""), 160),
        }
        for r in rows
    ]
    return json.dumps({"count": len(slim), "items": slim}, ensure_ascii=False)


@tool
def get_agent_trace(trace_id: str, limit_per_stream: int = 40) -> str:
    """按 trace_id 从 summary / trace / error 日志提取完整排查上下文。"""
    tid = (trace_id or "").strip()
    if not tid:
        return json.dumps({"message": "trace_id 不能为空"}, ensure_ascii=False)
    bundle = read_trace_bundle(tid, limit_per_stream=max(5, min(limit_per_stream, 100)))
    total = sum(len(v) for v in bundle.values())
    if total == 0:
        return json.dumps(
            {"message": f"未找到 trace_id={tid} 的日志", "trace_id": tid},
            ensure_ascii=False,
        )
    return json.dumps({"trace_id": tid, "streams": bundle}, ensure_ascii=False)


@tool
def search_agent_logs(keyword: str, stream: str = "summary", limit: int = 30) -> str:
    """在指定日志流中按关键词搜索（stream: summary|trace|error|music|bug 等）。"""
    kw = (keyword or "").strip()
    if not kw:
        return json.dumps({"message": "keyword 不能为空"}, ensure_ascii=False)
    name = (stream or "summary").strip().lower()
    rows = read_log_events(stream=name, keyword=kw, limit=max(1, min(limit, 100)))
    slim = [
        {
            "ts": r.get("ts"),
            "event": r.get("event"),
            "trace_id": r.get("trace_id"),
            "level": r.get("level"),
            "preview": preview(json.dumps(r, ensure_ascii=False), 180),
        }
        for r in rows
    ]
    return json.dumps({"stream": name, "keyword": kw, "count": len(slim), "items": slim}, ensure_ascii=False)


@tool
def notify_developer(title: str, message: str, severity: str = "medium") -> str:
    """向开发者 QQ 发送告警（NapCat OneBot HTTP 私聊）。"""
    from utils.napcat_notify import send_developer_alert

    trace = current_trace()
    result = send_developer_alert(
        title=title,
        message=message,
        severity=(severity or "medium").strip().lower(),
        trace_id=str(trace.get("trace_id") or ""),
        event="notify_developer",
    )
    payload = {
        "title": preview(title, 120),
        "message": preview(message, 500),
        "severity": (severity or "medium").strip().lower(),
        "trace_id": trace.get("trace_id"),
        **result,
    }
    return json.dumps(payload, ensure_ascii=False)


@tool
def update_incident_record(
    incident_id: str,
    status: str = "",
    root_cause: str = "",
    resolution: str = "",
    symptoms: str = "",
) -> str:
    """更新 agent_incident 事件记录（需 MySQL 表；未建表时返回提示）。"""
    iid = (incident_id or "").strip()
    if not iid:
        return json.dumps({"message": "incident_id 不能为空"}, ensure_ascii=False)
    try:
        from database.mysql.mysql_db import MysqlRepo

        ok = MysqlRepo().update_incident(
            incident_id=iid,
            status=status or None,
            root_cause=root_cause or None,
            resolution=resolution or None,
            symptoms=symptoms or None,
        )
    except Exception as exc:
        return json.dumps(
            {"message": "更新失败，可能尚未创建 agent_incident 表", "error": str(exc)},
            ensure_ascii=False,
        )
    if not ok:
        return json.dumps({"message": "未找到 incident 或数据库不可用", "incident_id": iid}, ensure_ascii=False)
    return json.dumps({"message": "已更新", "incident_id": iid}, ensure_ascii=False)


def build_bug_tools(*, mode: str = "general") -> list:
    """Bug ReAct 工具集；mode 预留扩展（auto|manual|readonly）。"""
    _ = mode
    return [
        list_recent_agent_errors,
        get_agent_trace,
        search_agent_logs,
        notify_developer,
        update_incident_record,
    ]

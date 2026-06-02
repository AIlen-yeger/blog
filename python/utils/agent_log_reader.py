"""读取 Agent JSONL 日志（供 bug 工具使用）。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from utils.agent_log_config import ARCHIVE_SUBDIR, resolve_log_dir


def _iter_log_files(stream: str, log_dir: Path | None = None) -> list[Path]:
    directory = log_dir or resolve_log_dir()
    if not directory.is_dir():
        return []

    active = directory / f"{stream}.jsonl"
    archive = directory / ARCHIVE_SUBDIR
    rotated = sorted(directory.glob(f"{stream}.jsonl.*"), reverse=True)
    if archive.is_dir():
        rotated = sorted(archive.glob(f"{stream}.jsonl.*"), reverse=True) + rotated

    paths: list[Path] = []
    if active.is_file():
        paths.append(active)
    paths.extend(p for p in rotated if p.is_file())
    return paths


def _parse_ts(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_jsonl_lines(path: Path, *, tail: int | None = None) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if tail is not None and tail > 0:
        lines = lines[-tail:]
    rows: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def read_log_events(
    *,
    stream: str = "summary",
    trace_id: str | None = None,
    keyword: str | None = None,
    level: str | None = None,
    hours: int | None = None,
    limit: int = 50,
    log_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """从指定日志流读取并过滤事件（新文件优先）。"""
    limit = max(1, min(limit, 200))
    cutoff = None
    if hours is not None and hours > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    matched: list[dict[str, Any]] = []
    for path in _iter_log_files(stream, log_dir):
        for row in reversed(_read_jsonl_lines(path)):
            if cutoff is not None:
                ts = _parse_ts(str(row.get("ts") or ""))
                if ts is not None and ts < cutoff:
                    continue
            if trace_id and str(row.get("trace_id") or "") != trace_id:
                continue
            if level and str(row.get("level") or "").upper() != level.upper():
                continue
            if keyword:
                blob = json.dumps(row, ensure_ascii=False)
                if keyword not in blob:
                    continue
            matched.append(row)
            if len(matched) >= limit:
                return matched
    return matched


def read_trace_bundle(trace_id: str, *, limit_per_stream: int = 40) -> dict[str, list[dict[str, Any]]]:
    """按 trace_id 聚合 summary / trace / error 中的相关行。"""
    out: dict[str, list[dict[str, Any]]] = {}
    for stream in ("summary", "trace", "error"):
        out[stream] = read_log_events(
            stream=stream,
            trace_id=trace_id,
            limit=limit_per_stream,
        )
    return out


def list_recent_errors(*, hours: int = 72, limit: int = 30) -> list[dict[str, Any]]:
    rows = read_log_events(stream="error", hours=hours, limit=limit)
    if len(rows) >= limit:
        return rows
    extra = read_log_events(stream="summary", hours=hours, limit=limit * 2)
    for row in extra:
        if str(row.get("level") or "").upper() == "ERROR":
            rows.append(row)
        if len(rows) >= limit:
            break
    return rows[:limit]

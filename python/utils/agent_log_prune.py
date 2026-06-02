"""Agent 日志轮转文件清理（供 CLI 与进程内定时任务共用）。"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from utils.agent_log_config import (
    ARCHIVE_SUBDIR,
    STATE_SUBDIR,
    resolve_log_dir,
    retention_days_for_stream,
)

logger = logging.getLogger(__name__)

# TimedRotatingFileHandler：trace.jsonl.2026-05-22
_ROTATED = re.compile(r"^(?P<stream>[a-z_]+)\.jsonl\.(?P<date>\d{4}-\d{2}-\d{2})$")


def _parse_rotated_name(name: str) -> tuple[str, datetime] | None:
    m = _ROTATED.match(name)
    if not m:
        return None
    try:
        day = datetime.strptime(m.group("date"), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return m.group("stream"), day


def migrate_log_layout(log_dir: Path) -> None:
    """确保 archive/、state/ 存在，并把根目录下旧轮转文件挪进 archive/。"""
    log_dir.mkdir(parents=True, exist_ok=True)
    archive = log_dir / ARCHIVE_SUBDIR
    archive.mkdir(parents=True, exist_ok=True)
    (log_dir / STATE_SUBDIR).mkdir(parents=True, exist_ok=True)

    for path in list(log_dir.iterdir()):
        if not path.is_file():
            continue
        if not _ROTATED.match(path.name):
            continue
        dest = archive / path.name
        if dest.exists():
            continue
        try:
            path.rename(dest)
            logger.info("[agent_log] migrated %s -> archive/", path.name)
        except OSError as exc:
            logger.warning("[agent_log] migrate %s failed: %s", path.name, exc)


def prune_log_dir(log_dir: Path, *, dry_run: bool = False) -> list[str]:
    """删除超过保留期的轮转文件；正在写入的 *.jsonl 不删。"""
    actions: list[str] = []
    if not log_dir.is_dir():
        actions.append(f"skip: directory missing {log_dir}")
        return actions

    migrate_log_layout(log_dir)

    now = datetime.now(timezone.utc)
    cutoff_cache: dict[str, datetime] = {}

    scan_dirs = [log_dir / ARCHIVE_SUBDIR, log_dir]
    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        for path in sorted(scan_dir.iterdir()):
            if not path.is_file():
                continue
            if path.suffix == ".jsonl" and _ROTATED.match(path.name) is None:
                continue
            parsed = _parse_rotated_name(path.name)
            if not parsed:
                continue

            stream, file_day = parsed
            if stream not in cutoff_cache:
                days = retention_days_for_stream(stream)
                cutoff_cache[stream] = now - timedelta(days=days)

            if file_day >= cutoff_cache[stream]:
                continue

            age_days = (now - file_day).days
            retain = retention_days_for_stream(stream)
            rel = path.relative_to(log_dir)
            msg = f"delete: {rel} (age={age_days}d, retain={retain}d)"
            actions.append(msg)
            if not dry_run:
                path.unlink(missing_ok=True)

    return actions


def run_agent_log_prune(*, log_dir: str | None = None, dry_run: bool = False) -> list[str]:
    directory = resolve_log_dir(log_dir)
    return prune_log_dir(directory, dry_run=dry_run)

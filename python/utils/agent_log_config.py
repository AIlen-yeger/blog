"""Agent 结构化日志目录与保留策略（纯文件）。"""

from __future__ import annotations

import logging
import os
from pathlib import Path

# 当前写入的日志基名（不含 .jsonl）
LOG_STREAMS = ("summary", "trace", "error", "music", "chat", "commit_user", "bug")

ARCHIVE_SUBDIR = "archive"
STATE_SUBDIR = "state"

# 长留：请求摘要 + 错误（后续 bug agent / MCP 告警用）
SUMMARY_RETAIN_DAYS = int(os.getenv("AGENT_LOG_SUMMARY_RETAIN_DAYS", "90"))
ERROR_RETAIN_DAYS = int(os.getenv("AGENT_LOG_ERROR_RETAIN_DAYS", "180"))

# 短留：明细 trace 与按 intent 分流
TRACE_RETAIN_DAYS = int(os.getenv("AGENT_LOG_TRACE_RETAIN_DAYS", "14"))
INTENT_RETAIN_DAYS = int(os.getenv("AGENT_LOG_INTENT_RETAIN_DAYS", "14"))

# 兼容旧版 access.jsonl 轮转文件清理
LEGACY_ACCESS_RETAIN_DAYS = TRACE_RETAIN_DAYS

DEFAULT_LOG_DIR = os.getenv("AGENT_LOG_DIR", "log/agent")
_LEGACY_LOG_DIR = "log/agent.log"

# summary.jsonl 中 final_preview 最大字符数（完整回复见 MySQL/Redis 历史或 trace.jsonl）
SUMMARY_ANSWER_PREVIEW_LEN = int(os.getenv("AGENT_LOG_ANSWER_PREVIEW_LEN", "800"))

# 进程内定时清理（Agent 启动后自动跑，默认开启）
LOG_PRUNE_ENABLED = os.getenv("AGENT_LOG_PRUNE_ENABLED", "true").lower() != "false"
LOG_PRUNE_ON_STARTUP = os.getenv("AGENT_LOG_PRUNE_ON_STARTUP", "true").lower() != "false"
LOG_PRUNE_INTERVAL_HOURS = float(os.getenv("AGENT_LOG_PRUNE_INTERVAL_HOURS", "24"))
LOG_PRUNE_STARTUP_DELAY_SEC = float(os.getenv("AGENT_LOG_PRUNE_STARTUP_DELAY_SEC", "60"))

# Bug Ops 内部 Agent（不对用户暴露）
BUG_AGENT_ENABLED = os.getenv("BUG_AGENT_ENABLED", "true").lower() != "false"
BUG_AGENT_ON_STARTUP = os.getenv("BUG_AGENT_ON_STARTUP", "true").lower() != "false"
BUG_AGENT_INTERVAL_HOURS = float(os.getenv("BUG_AGENT_INTERVAL_HOURS", "6"))
BUG_AGENT_STARTUP_DELAY_SEC = float(os.getenv("BUG_AGENT_STARTUP_DELAY_SEC", "120"))
BUG_AGENT_ALERT_ON_ERROR = os.getenv("BUG_AGENT_ALERT_ON_ERROR", "true").lower() != "false"
BUG_AGENT_MIN_SEVERITY = (os.getenv("BUG_AGENT_MIN_SEVERITY", "high") or "high").strip().lower()

_logger = logging.getLogger(__name__)
_legacy_dir_warned = False


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_log_dir(log_dir: str | None = None) -> Path:
    """日志根目录：默认 log/agent（正在写的 *.jsonl）；历史轮转在 archive/。"""
    global _legacy_dir_warned
    root = _project_root()

    if log_dir and str(log_dir).strip():
        path = Path(str(log_dir).strip())
        if not path.is_absolute():
            path = root / path
        return path

    env = (os.getenv("AGENT_LOG_DIR") or "").strip()
    if env:
        path = Path(env)
        if not path.is_absolute():
            path = root / path
        return path

    preferred = root / DEFAULT_LOG_DIR
    legacy = root / _LEGACY_LOG_DIR
    if legacy.is_dir() and not preferred.is_dir():
        if not _legacy_dir_warned:
            _logger.warning(
                "[agent_log] 使用旧目录 %s，建议在 .env 设 AGENT_LOG_DIR=log/agent",
                legacy,
            )
            _legacy_dir_warned = True
        return legacy
    return preferred


def archive_dir(log_dir: Path | None = None) -> Path:
    return resolve_log_dir() if log_dir is None else Path(log_dir) / ARCHIVE_SUBDIR


def state_dir(log_dir: Path | None = None) -> Path:
    return resolve_log_dir() if log_dir is None else Path(log_dir) / STATE_SUBDIR


def retention_days_for_stream(name: str) -> int:
    if name == "summary":
        return SUMMARY_RETAIN_DAYS
    if name == "error":
        return ERROR_RETAIN_DAYS
    if name == "trace":
        return TRACE_RETAIN_DAYS
    if name == "access":
        return LEGACY_ACCESS_RETAIN_DAYS
    if name in ("music", "chat", "commit_user", "bug"):
        return INTENT_RETAIN_DAYS
    return TRACE_RETAIN_DAYS

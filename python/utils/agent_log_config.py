"""Agent 结构化日志目录与保留策略（纯文件）。"""

from __future__ import annotations

import os
from pathlib import Path

# 当前写入的日志基名（不含 .jsonl）
LOG_STREAMS = ("summary", "trace", "error", "music", "chat", "commit_user", "bug")

# 长留：请求摘要 + 错误（后续 bug agent / MCP 告警用）
SUMMARY_RETAIN_DAYS = int(os.getenv("AGENT_LOG_SUMMARY_RETAIN_DAYS", "90"))
ERROR_RETAIN_DAYS = int(os.getenv("AGENT_LOG_ERROR_RETAIN_DAYS", "180"))

# 短留：明细 trace 与按 intent 分流
TRACE_RETAIN_DAYS = int(os.getenv("AGENT_LOG_TRACE_RETAIN_DAYS", "14"))
INTENT_RETAIN_DAYS = int(os.getenv("AGENT_LOG_INTENT_RETAIN_DAYS", "14"))

# 兼容旧版 access.jsonl 轮转文件清理
LEGACY_ACCESS_RETAIN_DAYS = TRACE_RETAIN_DAYS

DEFAULT_LOG_DIR = os.getenv("AGENT_LOG_DIR", "log/agent.log")

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
# scheduled_scan / error_alert 触发的最低严重度：low | medium | high | critical
BUG_AGENT_MIN_SEVERITY = (os.getenv("BUG_AGENT_MIN_SEVERITY", "high") or "high").strip().lower()


def resolve_log_dir(log_dir: str | None = None) -> Path:
    raw = (log_dir or DEFAULT_LOG_DIR).strip()
    path = Path(raw)
    if not path.is_absolute():
        root = Path(__file__).resolve().parents[1]
        path = root / path
    return path


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

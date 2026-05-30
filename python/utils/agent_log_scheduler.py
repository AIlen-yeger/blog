"""Agent 进程内日志清理定时任务（daemon 线程，无需额外依赖）。"""

from __future__ import annotations

import logging
import os
import threading
import time

from utils.agent_log_config import (
    LOG_PRUNE_ENABLED,
    LOG_PRUNE_INTERVAL_HOURS,
    LOG_PRUNE_ON_STARTUP,
    LOG_PRUNE_STARTUP_DELAY_SEC,
)
from utils.agent_log_prune import run_agent_log_prune

logger = logging.getLogger(__name__)

_started = False
_lock = threading.Lock()


def _prune_once(*, dry_run: bool = False) -> None:
    try:
        actions = run_agent_log_prune(dry_run=dry_run)
    except Exception:
        logger.exception("[agent_log_prune] scheduled run failed")
        return

    deleted = [a for a in actions if a.startswith("delete:")]
    if deleted:
        logger.info("[agent_log_prune] removed %d file(s)", len(deleted))
        for line in deleted:
            logger.info("[agent_log_prune] %s", line)
    elif actions and actions[0].startswith("skip:"):
        logger.warning("[agent_log_prune] %s", actions[0])
    else:
        logger.debug("[agent_log_prune] nothing to prune")


def _worker(interval_sec: float, startup_delay_sec: float, run_on_startup: bool) -> None:
    if run_on_startup and startup_delay_sec > 0:
        time.sleep(startup_delay_sec)
    if run_on_startup:
        _prune_once()

    while True:
        time.sleep(interval_sec)
        _prune_once()


def start_agent_log_prune_scheduler() -> None:
    """在 FastAPI 启动时调用一次；重复调用会被忽略。"""
    global _started
    if not LOG_PRUNE_ENABLED:
        logger.info("[agent_log_prune] disabled (AGENT_LOG_PRUNE_ENABLED=false)")
        return

    with _lock:
        if _started:
            return
        _started = True

    interval_sec = max(3600.0, LOG_PRUNE_INTERVAL_HOURS * 3600.0)
    thread = threading.Thread(
        target=_worker,
        name="agent-log-prune",
        daemon=True,
        kwargs={
            "interval_sec": interval_sec,
            "startup_delay_sec": LOG_PRUNE_STARTUP_DELAY_SEC,
            "run_on_startup": LOG_PRUNE_ON_STARTUP,
        },
    )
    thread.start()
    logger.info(
        "[agent_log_prune] scheduler started interval_hours=%.1f on_startup=%s",
        interval_sec / 3600.0,
        LOG_PRUNE_ON_STARTUP,
    )

"""Bug Ops 定时巡检与错误告警队列（daemon 线程）。"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any

from utils.log.agent_log_config import (
    BUG_AGENT_ALERT_ON_ERROR,
    BUG_AGENT_ENABLED,
    BUG_AGENT_INTERVAL_HOURS,
    BUG_AGENT_MIN_SEVERITY,
    BUG_AGENT_ON_STARTUP,
    BUG_AGENT_STARTUP_DELAY_SEC,
)

logger = logging.getLogger(__name__)

_started = False
_lock = threading.Lock()
_task_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=32)


def queue_bug_agent_from_log(payload: dict[str, Any]) -> None:
    """log_event 严重错误时入队，避免阻塞请求线程。"""
    if not BUG_AGENT_ENABLED or not BUG_AGENT_ALERT_ON_ERROR:
        return
    try:
        _task_queue.put_nowait({"kind": "log_alert", "payload": dict(payload)})
    except queue.Full:
        logger.warning("[bug_ops] task queue full, drop log alert")


def _process_queue() -> None:
    from server.bug_agent_runner import try_trigger_from_log_event

    while True:
        try:
            item = _task_queue.get(timeout=1.0)
        except queue.Empty:
            return
        if item.get("kind") == "log_alert":
            try:
                try_trigger_from_log_event(
                    item.get("payload") or {},
                    min_severity=BUG_AGENT_MIN_SEVERITY,
                )
            except Exception:
                logger.exception("[bug_ops] log alert handler failed")


def _scheduled_scan() -> None:
    from server.bug_agent_runner import scan_and_run_pending

    try:
        ran = scan_and_run_pending(min_severity=BUG_AGENT_MIN_SEVERITY)
        if ran:
            logger.info("[bug_ops] scheduled scan handled %d incident(s)", len(ran))
        else:
            logger.debug("[bug_ops] scheduled scan: nothing to do")
    except Exception:
        logger.exception("[bug_ops] scheduled scan failed")


def _worker(interval_sec: float, startup_delay_sec: float, run_on_startup: bool) -> None:
    if run_on_startup and startup_delay_sec > 0:
        time.sleep(startup_delay_sec)
    if run_on_startup:
        _scheduled_scan()

    while True:
        _process_queue()
        time.sleep(interval_sec)
        _scheduled_scan()
        _process_queue()


def start_bug_agent_scheduler() -> None:
    global _started
    if not BUG_AGENT_ENABLED:
        logger.info("[bug_ops] disabled (BUG_AGENT_ENABLED=false)")
        return

    with _lock:
        if _started:
            return
        _started = True

    interval_sec = max(300.0, BUG_AGENT_INTERVAL_HOURS * 3600.0)
    thread = threading.Thread(
        target=_worker,
        name="bug-ops-scheduler",
        daemon=True,
        kwargs={
            "interval_sec": interval_sec,
            "startup_delay_sec": BUG_AGENT_STARTUP_DELAY_SEC,
            "run_on_startup": BUG_AGENT_ON_STARTUP,
        },
    )
    thread.start()
    logger.info(
        "[bug_ops] scheduler started interval_hours=%.2f alert_on_error=%s min_severity=%s",
        interval_sec / 3600.0,
        BUG_AGENT_ALERT_ON_ERROR,
        BUG_AGENT_MIN_SEVERITY,
    )

"""每日定时推送 BTC 定投简报（默认北京时间 09:00）。"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from config.config import AgentConfig
from utils.agent_log_config import state_dir

logger = logging.getLogger(__name__)

_started = False
_lock = threading.Lock()
_last_sent_date = ""


def _sent_marker_path():
    return state_dir() / "btc_dca_last_sent.txt"


def _already_sent_today(local_date: str) -> bool:
    global _last_sent_date
    if _last_sent_date == local_date:
        return True
    path = _sent_marker_path()
    if path.is_file():
        try:
            if path.read_text(encoding="utf-8").strip() == local_date:
                _last_sent_date = local_date
                return True
        except Exception:
            pass
    return False


def _mark_sent_today(local_date: str) -> None:
    global _last_sent_date
    _last_sent_date = local_date
    path = _sent_marker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(local_date, encoding="utf-8")


def _maybe_send_daily() -> None:
    cfg = AgentConfig()
    if not cfg.btc_dca_daily_enabled:
        return

    tz = ZoneInfo(cfg.btc_dca_daily_tz or "Asia/Shanghai")
    now = datetime.now(tz)
    if now.hour != cfg.btc_dca_daily_hour or now.minute != cfg.btc_dca_daily_minute:
        return

    today = now.strftime("%Y-%m-%d")
    if _already_sent_today(today):
        return

    from service.btc_daily_brief import send_daily_brief_to_developer

    result = send_daily_brief_to_developer(force=False)
    if result.get("ok"):
        _mark_sent_today(today)
        logger.info("[btc_dca] daily brief sent for %s", today)
    else:
        logger.warning("[btc_dca] daily brief failed: %s", result.get("status"))


def _worker(check_interval_sec: float) -> None:
    time.sleep(5.0)
    while True:
        try:
            _maybe_send_daily()
        except Exception:
            logger.exception("[btc_dca] scheduler tick failed")
        time.sleep(check_interval_sec)


def start_btc_dca_scheduler() -> None:
    global _started
    cfg = AgentConfig()
    if not cfg.btc_dca_daily_enabled:
        logger.info("[btc_dca] daily push disabled (BTC_DCA_DAILY_ENABLED=false)")
        return

    with _lock:
        if _started:
            return
        _started = True

    interval = max(30.0, float(cfg.btc_dca_check_interval_sec or 60.0))
    thread = threading.Thread(
        target=_worker,
        name="btc-dca-scheduler",
        daemon=True,
        kwargs={"check_interval_sec": interval},
    )
    thread.start()
    logger.info(
        "[btc_dca] scheduler started tz=%s at %02d:%02d check_every=%.0fs",
        cfg.btc_dca_daily_tz,
        cfg.btc_dca_daily_hour,
        cfg.btc_dca_daily_minute,
        interval,
    )

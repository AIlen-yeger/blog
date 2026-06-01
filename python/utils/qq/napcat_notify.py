"""通过 NapCat（OneBot v11 HTTP）向开发者 QQ 发送私聊告警。"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from config.config import AgentConfig

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = ("low", "medium", "high", "critical")


def severity_at_least(severity: str, minimum: str) -> bool:
    try:
        return _SEVERITY_ORDER.index((severity or "medium").strip().lower()) >= _SEVERITY_ORDER.index(
            (minimum or "high").strip().lower()
        )
    except ValueError:
        return False


def _napcat_settings() -> dict[str, Any]:
    cfg = AgentConfig()
    return {
        "enabled": cfg.napcat_notify_enabled,
        "base_url": (cfg.napcat_http_url or "").rstrip("/"),
        "user_id": cfg.napcat_alert_qq,
        "access_token": cfg.napcat_access_token,
        "min_severity": cfg.napcat_min_severity,
    }


def napcat_configured() -> bool:
    s = _napcat_settings()
    return bool(s["enabled"] and s["base_url"] and s["user_id"])


def format_alert_text(
    *,
    title: str,
    message: str,
    severity: str = "medium",
    trace_id: str | None = None,
    event: str | None = None,
) -> str:
    lines = [f"【博客 Agent · {severity.upper()}】", (title or "告警").strip()]
    if trace_id and trace_id not in ("-", ""):
        lines.append(f"trace: {trace_id}")
    if event:
        lines.append(f"event: {event}")
    body = (message or "").strip()
    if body:
        lines.append("")
        lines.append(body)
    return "\n".join(lines)[:3500]


def send_private_message(text: str) -> dict[str, Any]:
    """调用 NapCat send_private_msg；未配置时返回 skipped。"""
    s = _napcat_settings()
    if not s["enabled"]:
        return {"ok": False, "status": "disabled", "message": "NAPCAT_NOTIFY_ENABLED=false"}
    if not s["base_url"]:
        return {"ok": False, "status": "misconfigured", "message": "未配置 NAPCAT_HTTP_URL"}
    if not s["user_id"]:
        return {"ok": False, "status": "misconfigured", "message": "未配置 NAPCAT_ALERT_QQ"}

    try:
        user_id = int(str(s["user_id"]).strip())
    except ValueError:
        return {"ok": False, "status": "misconfigured", "message": "NAPCAT_ALERT_QQ 必须是数字 QQ 号"}

    url = f"{s['base_url']}/send_private_msg"
    payload = {
        "user_id": user_id,
        "message": [{"type": "text", "data": {"text": (text or "")[:4000]}}],
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    token = (s["access_token"] or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                body = {"raw": raw}
            status = body.get("status") if isinstance(body, dict) else None
            if status == "failed" or body.get("retcode") not in (None, 0):
                return {
                    "ok": False,
                    "status": "api_error",
                    "message": str(body.get("message") or body.get("wording") or body),
                    "response": body,
                }
            logger.info("[napcat] sent private msg to user_id=%s", user_id)
            return {"ok": True, "status": "sent", "response": body}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:500]
        logger.warning("[napcat] http error %s: %s", exc.code, err_body)
        return {"ok": False, "status": "http_error", "code": exc.code, "message": err_body}
    except urllib.error.URLError as exc:
        logger.warning("[napcat] unreachable %s: %s", url, exc.reason)
        return {"ok": False, "status": "unreachable", "message": str(exc.reason)}


def send_developer_alert(
    *,
    title: str,
    message: str,
    severity: str = "medium",
    trace_id: str | None = None,
    event: str | None = None,
) -> dict[str, Any]:
    """按严重度阈值决定是否发送 QQ 私聊。"""
    s = _napcat_settings()
    sev = (severity or "medium").strip().lower()
    if not severity_at_least(sev, s["min_severity"]):
        return {
            "ok": False,
            "status": "below_threshold",
            "message": f"severity={sev} < min={s['min_severity']}",
        }
    text = format_alert_text(
        title=title,
        message=message,
        severity=sev,
        trace_id=trace_id,
        event=event,
    )
    result = send_private_message(text)
    result["severity"] = sev
    return result

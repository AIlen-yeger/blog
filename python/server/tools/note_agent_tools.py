"""Agent 笔记发布：调用 Java POST /notes。"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from utils.qq.qq_music_tools import blog_api_base
from utils.log.trace_log import log_event, preview

logger = logging.getLogger(__name__)


def publish_note_impl(
    *,
    access_token: str,
    title: str,
    content: str,
    topic_title: str = "随笔",
    agent_session_id: str = "",
    status: str = "published",
) -> dict:
    token = (access_token or "").strip()
    t = (title or "").strip()
    body = (content or "").strip()
    if not token:
        return {"ok": False, "message": "未登录，无法发布笔记"}
    if not t:
        return {"ok": False, "message": "标题不能为空"}
    if not body:
        return {"ok": False, "message": "正文不能为空"}

    payload = {
        "title": t,
        "content": body,
        "topicTitle": (topic_title or "随笔").strip() or "随笔",
        "agentSessionId": (agent_session_id or "").strip(),
        "status": (status or "published").strip() or "published",
    }
    url = f"{blog_api_base()}/notes"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:500]
        logger.warning("[note] publish http %s: %s", exc.code, err)
        message = _extract_message(err) or f"发布失败 HTTP {exc.code}"
        log_event("note.publish", ok=False, http_status=exc.code, error_preview=preview(err))
        return {"ok": False, "message": message, "detail": err}
    except urllib.error.URLError as exc:
        return {"ok": False, "message": f"博客 API 不可达：{exc.reason}"}
    except Exception as exc:
        logger.exception("[note] publish failed")
        return {"ok": False, "message": str(exc)}

    ok = isinstance(raw, dict) and raw.get("code") in (0, 200, None)
    note = raw.get("data") if isinstance(raw, dict) else None
    note_id = note.get("id") if isinstance(note, dict) else ""
    log_event("note.publish", ok=ok, note_id=note_id or "", title_preview=preview(t))
    return {
        "ok": ok,
        "note_id": note_id,
        "title": t,
        "data": note,
        "message": raw.get("message") if isinstance(raw, dict) else "",
    }


def _extract_message(err_body: str) -> str:
    try:
        row = json.loads(err_body)
        if isinstance(row, dict) and row.get("message"):
            return str(row["message"])
    except json.JSONDecodeError:
        pass
    return ""

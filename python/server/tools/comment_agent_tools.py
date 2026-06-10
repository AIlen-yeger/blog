"""笔记评论：保存蕾西亚回复到 Java 博客 API。"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

from langchain_core.tools import tool

from utils.qq.qq_music_tools import blog_api_base
from utils.log.trace_log import log_event, preview

logger = logging.getLogger(__name__)


def _ops_token() -> str:
    return (os.getenv("AGENT_OPS_TOKEN") or "").strip()


def save_note_agent_reply_impl(*, note_id: str, agent_reply: str, job_id: str = "") -> dict:
    """调用 Java POST /agent/ops/notes/{id}/agent-reply（需 jobId 与 running 任务匹配）。"""
    nid = (note_id or "").strip()
    jid = (job_id or "").strip()
    text = (agent_reply or "").strip()
    if not nid:
        return {"ok": False, "message": "note_id 不能为空"}
    if not jid:
        return {"ok": False, "message": "job_id 不能为空"}
    if not text:
        return {"ok": False, "message": "回复内容为空"}
    token = _ops_token()
    if not token:
        return {"ok": False, "message": "未配置 AGENT_OPS_TOKEN"}

    url = f"{blog_api_base()}/agent/ops/notes/{nid}/agent-reply"
    payload = json.dumps({"jobId": jid, "agentReply": text}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Ops-Token": token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:400]
        logger.warning("[comment] save http %s note=%s: %s", exc.code, nid, err)
        log_event(
            "note.comment.save",
            ok=False,
            note_id=nid,
            http_status=exc.code,
            error_preview=preview(err),
        )
        return {"ok": False, "message": f"保存失败 HTTP {exc.code}", "detail": err}
    except urllib.error.URLError as exc:
        logger.warning("[comment] save unreachable %s: %s", url, exc.reason)
        return {"ok": False, "message": f"博客 API 不可达：{exc.reason}"}
    except Exception as exc:
        logger.exception("[comment] save failed note=%s", nid)
        return {"ok": False, "message": str(exc)}

    ok = isinstance(body, dict) and body.get("code") in (0, 200, None)
    data = body.get("data") if isinstance(body, dict) else None
    log_event(
        "note.comment.save",
        ok=ok,
        note_id=nid,
        job_id=jid,
        reply_length=len(text),
    )
    return {"ok": ok, "note_id": nid, "data": data}


@tool
def save_note_agent_reply(note_id: str, agent_reply: str, job_id: str = "") -> str:
    """将蕾西亚对笔记的回复写入博客数据库，关联指定 note_id 与 job_id。"""
    result = save_note_agent_reply_impl(note_id=note_id, agent_reply=agent_reply, job_id=job_id)
    return json.dumps(result, ensure_ascii=False)

"""发布笔记预览：解析附件，生成 action_preview，不写库。"""

from __future__ import annotations

import logging
import re

from server.state import AgentState
from service.document_ingest import ParsedDocument, merge_parsed_documents, parse_attachment, parse_text_content
from utils.log.trace_log import bind_trace, log_event, preview, span

logger = logging.getLogger(__name__)

_PUBLISH_SIGNALS = (
    "发布笔记",
    "发一篇笔记",
    "发笔记",
    "上传的是笔记",
    "这是笔记",
    "帮我发布",
    "发到博客",
    "发布到博客",
    "写成笔记",
)


def wants_publish_note(question: str, attachments: list[dict] | None) -> bool:
    q = (question or "").strip()
    if any(s in q for s in _PUBLISH_SIGNALS):
        return True
    if attachments and re.search(r"发布|发笔记|上传.*笔记", q):
        return True
    return False


def _parse_attachments(attachments: list[dict]) -> list[ParsedDocument]:
    docs: list[ParsedDocument] = []
    for att in attachments:
        if not isinstance(att, dict):
            continue
        kind = str(att.get("kind") or "").lower()
        name = str(att.get("name") or "document")
        mime = str(att.get("mime") or "")
        url = str(att.get("url") or "")
        text_inline = str(att.get("text") or att.get("content") or "")
        if kind == "text" or (text_inline and not url):
            docs.append(parse_text_content(text_inline, filename=name, mime=mime or "text/plain"))
            continue
        if not url:
            continue
        try:
            docs.append(parse_attachment(url=url, name=name, mime=mime, kind=kind))
        except Exception as exc:
            logger.warning("[publish_note] parse failed name=%s err=%s", name, exc)
            raise
    return docs


def build_publish_preview(state: AgentState) -> dict:
    """返回 preview dict，供 SSE action_preview 与前端确认卡使用。"""
    _bind_trace(state)
    question = (state.get("question") or "").strip()
    attachments = state.get("attachments") or []

    with span("publish_note.preview", question_preview=preview(question, 80)):
        docs = _parse_attachments(attachments) if attachments else []
        merged = merge_parsed_documents(docs) if docs else None

        if merged and merged.body:
            title = merged.title
            content = merged.body
            excerpt = merged.excerpt
            names = merged.source_filename
        else:
            title = _title_from_question(question)
            content = question
            excerpt = content[:200] + ("…" if len(content) > 200 else "")
            names = ""

        preview_data = {
            "title": title,
            "excerpt": excerpt,
            "topicTitle": "随笔",
            "contentPreview": content[:1200] + ("…" if len(content) > 1200 else ""),
            "content": content,
            "attachmentNames": names,
            "sessionId": (state.get("session_id") or "").strip(),
        }
        log_event(
            "publish_note.preview",
            title_preview=preview(title),
            chars=len(content),
            attachments=len(attachments),
        )
        return preview_data


def _bind_trace(state: AgentState) -> None:
    bind_trace(
        trace_id=state.get("trace_id") or None,
        session_id=state.get("session_id") or None,
        user_id=int(state.get("user_id") or 0),
        intent="publish_note",
    )


def _title_from_question(question: str) -> str:
    q = (question or "").strip()
    if not q:
        return "未命名笔记"
    first_line = q.split("\n", 1)[0].strip()
    for prefix in ("请", "帮我", "把", "将"):
        if first_line.startswith(prefix):
            first_line = first_line[len(prefix) :].strip()
    if len(first_line) > 24:
        return first_line[:24] + "…"
    return first_line or "未命名笔记"


def run_publish_note_preview(state: AgentState) -> dict:
    preview_data = build_publish_preview(state)
    msg = (
        f"我已整理好笔记预览《{preview_data['title']}》。\n"
        f"摘要：{preview_data['excerpt']}\n"
        "请在下方确认卡片中检查标题与专题，确认后才会发布到博客。"
    )
    return {
        "final_answer": msg,
        "preview": preview_data,
        "action": "publish_note",
    }

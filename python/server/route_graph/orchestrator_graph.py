"""LangGraph 多意图编排：规划 tasks 并按序执行。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.config import AgentConfig
from server.agent import ChatModel
from server.route_graph.music_route import run_music_react
from server.route_graph.publish_note_route import run_publish_note_preview, wants_publish_note
from server.state import AgentState
from utils.log.trace_log import log_event, preview, span

logger = logging.getLogger(__name__)

_MULTI_INTENT_WORDS = ("同时", "顺便", "并且", "还要", "另外", "再加", "一并")


class OrchestratorState(TypedDict, total=False):
    question: str
    attachments: list[dict]
    access_token: str
    session_id: str
    user_id: int
    limit: int
    channel: str
    user_name: str
    account: str
    user_role: str
    trace_id: str
    tasks: list[dict]
    task_results: list[dict]
    final_answer: str
    pending_preview: dict | None
    pending_action: str


def should_orchestrate(state: AgentState) -> bool:
    q = (state.get("question") or "").strip()
    attachments = state.get("attachments") or []
    if attachments:
        return True
    if any(w in q for w in _MULTI_INTENT_WORDS):
        return True
    if wants_publish_note(q, attachments) and re.search(r"歌|音乐|qq\.com", q, re.I):
        return True
    return False


def _planner_prompt(question: str, has_attachments: bool) -> str:
    attach_hint = "用户附带了文件。" if has_attachments else "用户未附带文件。"
    return f"""你是任务规划器。根据用户输入，输出 JSON 数组 tasks，每个元素为 {{"intent":"..."}}。
可用 intent：chat, music, publish_note
规则：
- 仅闲聊 → [{{"intent":"chat"}}] 或 []
- 发布/上传笔记 → publish_note（需用户明确发布意图或附件+发布语义）
- 加歌/音乐链接/听歌报告 → music
- 多需求按执行顺序列出，如 [{{"intent":"publish_note"}},{{"intent":"music"}}]
- commit_user 表示已有笔记回复，此处用 publish_note 表示发新笔记
{attach_hint}
用户：{question}
只输出 JSON 数组，无其它文字。"""


def plan_tasks(state: AgentState) -> list[dict]:
    q = (state.get("question") or "").strip()
    attachments = state.get("attachments") or []

    # 规则兜底
    tasks: list[dict] = []
    if wants_publish_note(q, attachments):
        tasks.append({"intent": "publish_note"})
    if re.search(r"y\.qq\.com|加歌|添加歌曲|音乐链接", q, re.I):
        if not any(t.get("intent") == "music" for t in tasks):
            tasks.append({"intent": "music"})
    if tasks:
        return tasks

    cfg = AgentConfig()
    try:
        llm = ChatOpenAI(
            model=cfg.judge_model_name,
            api_key=cfg.judge_api_key or cfg.chat_api_key,
            base_url=cfg.judge_base_url or cfg.chat_base_url,
            temperature=0,
            timeout=30,
            max_retries=1,
        )
        raw = llm.invoke(
            [
                SystemMessage(content="只输出 JSON 数组"),
                HumanMessage(content=_planner_prompt(q, bool(attachments))),
            ]
        )
        text = (raw.content or "").strip() if hasattr(raw, "content") else str(raw)
        data = json.loads(text)
        if isinstance(data, list):
            out = []
            for row in data:
                if isinstance(row, dict) and row.get("intent"):
                    intent = str(row["intent"]).strip().lower()
                    if intent in ("chat", "music", "publish_note"):
                        out.append({"intent": intent})
            if out:
                return out
    except Exception:
        logger.exception("[orchestrator] plan_tasks failed")

    return [{"intent": "chat"}]


def _agent_state_from_orch(state: OrchestratorState) -> AgentState:
    return {
        "question": state.get("question") or "",
        "session_id": state.get("session_id") or "",
        "user_id": int(state.get("user_id") or 0),
        "limit": int(state.get("limit") or AgentConfig().history_limit),
        "access_token": state.get("access_token") or "",
        "channel": state.get("channel") or "web",
        "user_name": state.get("user_name") or "",
        "account": state.get("account") or "",
        "user_role": state.get("user_role") or "",
        "trace_id": state.get("trace_id") or "",
        "attachments": state.get("attachments") or [],
    }


def run_orchestrator(state: AgentState) -> dict:
    """执行多意图编排，返回 final_answer / preview / action。"""
    with span("orchestrator.run", question_preview=preview(state.get("question"), 100)):
        orch: OrchestratorState = dict(state)
        tasks = plan_tasks(state)
        # 仅 chat 则交给外层 stream
        if not tasks or tasks == [{"intent": "chat"}]:
            return {"delegate_chat": True}

        orch["tasks"] = tasks
        orch["task_results"] = []
        orch["pending_preview"] = None
        orch["pending_action"] = ""

        agent_state = _agent_state_from_orch(orch)
        parts: list[str] = []

        for task in tasks:
            intent = str(task.get("intent") or "chat")
            if intent == "publish_note":
                result = run_publish_note_preview(agent_state)
                orch["pending_preview"] = result.get("preview")
                orch["pending_action"] = result.get("action") or "publish_note"
                parts.append(result.get("final_answer") or "")
                orch["task_results"].append({"intent": intent, "ok": True})
                continue
            if intent == "music":
                try:
                    music = run_music_react(agent_state)
                    text = (music.get("final_answer") or "").strip()
                    parts.append(text or "音乐相关已处理。")
                    orch["task_results"].append({"intent": intent, "ok": True})
                except Exception as exc:
                    logger.exception("[orchestrator] music failed")
                    parts.append(f"音乐部分处理失败：{exc}")
                    orch["task_results"].append({"intent": intent, "ok": False})
                continue
            if intent == "chat":
                try:
                    cm = ChatModel()
                    text = cm.chat_once(
                        question=agent_state["question"],
                        session_id=agent_state["session_id"],
                        user_id=agent_state["user_id"],
                        limit=int(agent_state.get("limit") or 10),
                        intent="chat",
                        channel=agent_state.get("channel") or "web",
                        developer_name=agent_state.get("user_name") or "",
                    )
                    parts.append(text)
                    orch["task_results"].append({"intent": intent, "ok": True})
                except Exception as exc:
                    parts.append(f"对话失败：{exc}")
                    orch["task_results"].append({"intent": intent, "ok": False})

        final = "\n\n".join(p for p in parts if p).strip() or "处理完成。"
        log_event("orchestrator.done", tasks=len(tasks), has_preview=bool(orch.get("pending_preview")))
        return {
            "final_answer": final,
            "preview": orch.get("pending_preview"),
            "action": orch.get("pending_action") or "",
            "tasks": tasks,
        }

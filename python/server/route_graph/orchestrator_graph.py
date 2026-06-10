"""LangGraph 多意图编排：规划 tasks 并按序执行。"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
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

_MULTI_INTENT_WORDS = ("同时", "顺便", "并且", "还要", "另外", "再加", "一并", "然后", "再", "接着")

STEP_TITLES: dict[str, str] = {
    "publish_note": "整理并预览笔记",
    "music": "添加歌曲",
    "chat": "补充说明",
}

StepCallback = Callable[[str, str, str], None]


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
    execution_mode: str
    tasks: list[dict]
    task_results: list[dict]
    final_answer: str
    pending_preview: dict | None
    pending_action: str


def resolve_execution_mode(state: AgentState) -> str:
    mode = (state.get("execution_mode") or "auto").strip().lower()
    return mode if mode in ("auto", "plan", "fast") else "auto"


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


def should_use_orchestrator(state: AgentState) -> bool:
    mode = resolve_execution_mode(state)
    if mode == "fast":
        return False
    if mode == "plan":
        return True
    return should_orchestrate(state)


def normalize_step(task: dict, index: int) -> dict:
    intent = str(task.get("intent") or "chat").strip().lower()
    title = str(task.get("title") or "").strip() or STEP_TITLES.get(intent, intent)
    return {"id": str(task.get("id") or index + 1), "intent": intent, "title": title}


def normalize_steps(tasks: list[dict]) -> list[dict]:
    return [normalize_step(t, i) for i, t in enumerate(tasks)]


def should_delegate_chat(tasks: list[dict], mode: str) -> bool:
    if mode == "plan":
        return False
    if not tasks:
        return True
    intents = [str(t.get("intent") or "chat") for t in tasks]
    return intents == ["chat"]


def should_emit_plan_ui(steps: list[dict], mode: str) -> bool:
    if mode == "plan":
        return len(steps) >= 1
    return len(steps) >= 2


def effective_orchestrator_mode(state: AgentState, *, force_orchestrate: bool = False) -> str:
    if force_orchestrate:
        return "plan"
    return resolve_execution_mode(state)


def _planner_prompt(question: str, has_attachments: bool) -> str:
    attach_hint = "用户附带了文件。" if has_attachments else "用户未附带文件。"
    return f"""你是任务规划器。根据用户输入，输出 JSON 数组 tasks，每个元素为 {{"intent":"...","title":"可选中文标题"}}。
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


def plan_tasks_rules_only(state: AgentState) -> list[dict]:
    """仅规则兜底规划，不调用 LLM（评测用）。"""
    q = (state.get("question") or "").strip()
    attachments = state.get("attachments") or []
    tasks: list[dict] = []
    if wants_publish_note(q, attachments):
        tasks.append({"intent": "publish_note"})
    if re.search(r"y\.qq\.com|加歌|添加歌曲|音乐链接", q, re.I):
        if not any(t.get("intent") == "music" for t in tasks):
            tasks.append({"intent": "music"})
    return normalize_steps(tasks) if tasks else []


def plan_tasks(state: AgentState) -> list[dict]:
    q = (state.get("question") or "").strip()
    attachments = state.get("attachments") or []

    ruled = plan_tasks_rules_only(state)
    if ruled:
        return ruled

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
            out: list[dict] = []
            for row in data:
                if isinstance(row, dict) and row.get("intent"):
                    intent = str(row["intent"]).strip().lower()
                    if intent in ("chat", "music", "publish_note"):
                        item: dict[str, Any] = {"intent": intent}
                        if row.get("title"):
                            item["title"] = str(row["title"]).strip()
                        out.append(item)
            if out:
                return normalize_steps(out)
    except Exception:
        logger.exception("[orchestrator] plan_tasks failed")

    return normalize_steps([{"intent": "chat"}])


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
        "execution_mode": state.get("execution_mode") or "auto",
    }


def run_orchestrator_step(agent_state: AgentState, task: dict) -> dict:
    """执行单步，返回 text / preview / action / summary / ok。"""
    intent = str(task.get("intent") or "chat")
    title = str(task.get("title") or STEP_TITLES.get(intent, intent))

    if intent == "publish_note":
        result = run_publish_note_preview(agent_state)
        return {
            "ok": True,
            "text": result.get("final_answer") or "",
            "preview": result.get("preview"),
            "action": result.get("action") or "publish_note",
            "summary": "预览已生成",
        }

    if intent == "music":
        music = run_music_react(agent_state)
        text = (music.get("final_answer") or "").strip() or "音乐相关已处理。"
        return {"ok": True, "text": text, "summary": "音乐处理完成"}

    if intent == "chat":
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
        return {"ok": True, "text": text, "summary": title}

    return {"ok": False, "text": f"未知步骤：{intent}", "summary": "未知任务"}


def run_orchestrator(
    state: AgentState,
    *,
    on_step: StepCallback | None = None,
    tasks: list[dict] | None = None,
) -> dict:
    """执行多意图编排，返回 final_answer / preview / action / tasks。"""
    with span("orchestrator.run", question_preview=preview(state.get("question"), 100)):
        mode = effective_orchestrator_mode(state)
        steps = tasks if tasks is not None else plan_tasks(state)

        if should_delegate_chat(steps, mode):
            return {"delegate_chat": True, "tasks": steps}

        orch: OrchestratorState = dict(state)
        orch["tasks"] = steps
        orch["task_results"] = []
        orch["pending_preview"] = None
        orch["pending_action"] = ""

        agent_state = _agent_state_from_orch(orch)
        parts: list[str] = []

        for task in steps:
            step_id = str(task.get("id") or "")
            if on_step and step_id:
                on_step(step_id, "running", "")
            try:
                result = run_orchestrator_step(agent_state, task)
                if result.get("preview"):
                    orch["pending_preview"] = result.get("preview")
                    orch["pending_action"] = result.get("action") or "publish_note"
                parts.append(result.get("text") or "")
                orch["task_results"].append(
                    {"intent": task.get("intent"), "ok": bool(result.get("ok", True))}
                )
                if on_step and step_id:
                    on_step(step_id, "done", str(result.get("summary") or ""))
            except Exception as exc:
                logger.exception("[orchestrator] step failed intent=%s", task.get("intent"))
                parts.append("该步骤处理失败，请稍后重试。")
                orch["task_results"].append({"intent": task.get("intent"), "ok": False})
                if on_step and step_id:
                    on_step(step_id, "failed", "处理失败")

        final = "\n\n".join(p for p in parts if p).strip() or "处理完成。"
        log_event("orchestrator.done", tasks=len(steps), has_preview=bool(orch.get("pending_preview")))
        return {
            "final_answer": final,
            "preview": orch.get("pending_preview"),
            "action": orch.get("pending_action") or "",
            "tasks": steps,
        }

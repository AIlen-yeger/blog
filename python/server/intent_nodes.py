"""默认 IntentNode 注册：从 manifest 读描述，绑定各 route_graph 执行器。"""

from __future__ import annotations

from config.config import AgentConfig
from server.agent import ChatModel
from server.aicoin_access import aicoin_allowed_for_state
from server.intent_registry import IntentNode, get_intent_registry
from server.intent_types import StepResult
from server.route_graph.aicoin_route import run_aicoin_react
from server.route_graph.comment_route import run_note_comment
from server.route_graph.music_route import run_music_react
from server.route_graph.publish_note_route import run_publish_note_preview
from server.skills_server.skill_registry import get_registry
from server.state import AgentState


def _cap_description(intent: str, fallback: str) -> str:
    reg = get_registry()
    cap = reg.get_for_intent(intent)
    if cap and cap.description:
        return cap.description
    return fallback


def _exec_publish_note(
    state: AgentState,
    chat_model: ChatModel | None,
    task_title: str,
) -> StepResult:
    result = run_publish_note_preview(state)
    return StepResult(
        ok=True,
        text=str(result.get("final_answer") or ""),
        summary=task_title or "预览已生成",
        preview=result.get("preview"),
        action=str(result.get("action") or "publish_note"),
    )


def _exec_music(
    state: AgentState,
    chat_model: ChatModel | None,
    task_title: str,
) -> StepResult:
    music = run_music_react(state)
    text = (music.get("final_answer") or "").strip() or "音乐相关已处理。"
    return StepResult(ok=True, text=text, summary=task_title or "音乐处理完成")


def _exec_aicoin(
    state: AgentState,
    chat_model: ChatModel | None,
    task_title: str,
) -> StepResult:
    cm = chat_model or ChatModel()
    aicoin = run_aicoin_react(state, chat_model=cm)
    text = (aicoin.get("final_answer") or "").strip() or "处理完成"
    return StepResult(ok=True, text=text, summary=task_title or "行情已分析")


def _exec_chat(
    state: AgentState,
    chat_model: ChatModel | None,
    task_title: str,
) -> StepResult:
    cm = chat_model or ChatModel()
    limit = int(state.get("limit") or AgentConfig().history_limit)
    text = cm.chat_once(
        question=state["question"],
        session_id=state.get("session_id") or "",
        user_id=int(state.get("user_id") or 0),
        limit=limit,
        intent="chat",
        trace_id=state.get("trace_id") or "",
        channel=(state.get("channel") or "web").strip().lower(),
        developer_name=(state.get("user_name") or "").strip(),
        user_logged_in=bool((state.get("access_token") or "").strip()),
    )
    return StepResult(ok=True, text=text, summary=task_title or "补充说明")


def _exec_commit_user(
    state: AgentState,
    chat_model: ChatModel | None,
    task_title: str,
) -> StepResult:
    comment = run_note_comment(state)
    text = (comment.get("final_answer") or "").strip() or "笔记回复生成失败，请稍后刷新。"
    ok = bool(text and "失败" not in text[:20])
    return StepResult(ok=ok, text=text, summary=task_title or "笔记回复已生成")


def bootstrap_intent_registry() -> None:
    """注册内置 intent 节点（幂等）。"""
    registry = get_intent_registry()
    if registry.is_bootstrapped:
        return

    registry.register(
        IntentNode(
            intent="music",
            description=_cap_description("music", "QQ 音乐链接、听歌排行/报告、加歌"),
            orchestratable=True,
            plan_title="添加歌曲",
            output_mode="stream",
        ),
        _exec_music,
    )
    registry.register(
        IntentNode(
            intent="aicoin",
            description=_cap_description("aicoin", "只读行情、定投与快讯"),
            orchestratable=True,
            plan_title="查询行情",
            output_mode="stream",
            guard=aicoin_allowed_for_state,
            denied_message="行情助手仅对管理员或开发者开放，该步骤无法执行。",
        ),
        _exec_aicoin,
    )
    registry.register(
        IntentNode(
            intent="publish_note",
            description=_cap_description("publish_note", "从对话/附件发布新笔记"),
            orchestratable=True,
            plan_title="整理并预览笔记",
            output_mode="stream",
        ),
        _exec_publish_note,
    )
    registry.register(
        IntentNode(
            intent="chat",
            description=_cap_description("chat", "闲聊陪伴，无工具"),
            orchestratable=True,
            plan_title="补充说明",
            output_mode="stream",
        ),
        _exec_chat,
    )
    registry.register(
        IntentNode(
            intent="commit_user",
            description=_cap_description("commit_user", "笔记下回复开发者"),
            orchestratable=False,
            plan_title="笔记回复",
            output_mode="once",
        ),
        _exec_commit_user,
    )
    registry.mark_bootstrapped()

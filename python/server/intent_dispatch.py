"""统一 intent 步进执行层（单路由与编排器共用）。"""

from __future__ import annotations

import logging

from server.agent import ChatModel
from server.intent_nodes import bootstrap_intent_registry
from server.intent_registry import get_intent_registry
from server.intent_types import StepResult
from server.state import AgentState

logger = logging.getLogger(__name__)

_PRIOR_TEXT_CAP = 500


def _ensure_registry():
    bootstrap_intent_registry()
    return get_intent_registry()


def orchestratable_intents() -> frozenset[str]:
    return _ensure_registry().orchestratable_intents()


def plan_step_title(intent: str) -> str:
    return _ensure_registry().plan_step_title(intent)


def build_planner_intent_list() -> str:
    return _ensure_registry().planner_intent_line()


def intent_output_mode(intent: str) -> str:
    return _ensure_registry().get_output_mode(intent)


def registered_intents() -> frozenset[str]:
    return _ensure_registry().all_intents()


def inject_step_context(
    state: AgentState,
    prior_results: list[dict] | None,
) -> AgentState:
    """将已完成步骤摘要拼入 question，供后续子图使用。"""
    if not prior_results:
        return state

    reg = _ensure_registry()
    lines = ["【已完成步骤】"]
    for row in prior_results:
        intent = str(row.get("intent") or "").strip()
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        if len(text) > _PRIOR_TEXT_CAP:
            text = text[: _PRIOR_TEXT_CAP - 1] + "…"
        label = reg.plan_step_title(intent) if intent else "步骤"
        lines.append(f"- {label}：{text}")

    if len(lines) <= 1:
        return state

    base_q = (state.get("question") or "").strip()
    merged_q = f"{base_q}\n\n" + "\n".join(lines) if base_q else "\n".join(lines)
    out: AgentState = dict(state)
    out["question"] = merged_q
    return out


def step_result_to_dict(result: StepResult) -> dict:
    return {
        "ok": result.ok,
        "text": result.text,
        "summary": result.summary,
        "preview": result.preview,
        "action": result.action,
    }


def run_intent_step(
    state: AgentState,
    intent: str,
    *,
    prior_results: list[dict] | None = None,
    chat_model: ChatModel | None = None,
    task_title: str = "",
) -> StepResult:
    """执行单 intent 子图，供 agent_entry 与 orchestrator 共用。"""
    from utils.log.trace_log import bind_trace_from_state

    key = (intent or "chat").strip().lower()
    if key == "add_son":
        key = "music"

    reg = _ensure_registry()
    step_state = inject_step_context(state, prior_results)
    bind_trace_from_state(step_state, intent=key)

    try:
        return reg.execute(
            key,
            step_state,
            chat_model=chat_model,
            task_title=task_title,
        )
    except Exception:
        logger.exception("[intent_dispatch] step failed intent=%s", key)
        return StepResult(
            ok=False,
            text="该步骤处理失败，请稍后重试。",
            summary="处理失败",
        )

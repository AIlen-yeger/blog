"""Orchestrator 规则规划与 should_orchestrate 评测。"""

from __future__ import annotations

from eval.loader import load_golden
from eval.metrics import plan_intents_match
from eval.models import EvalScore, SuiteResult
from server.route_graph.orchestrator_graph import (
    plan_tasks_rules_only,
    should_emit_plan_ui,
    should_orchestrate,
    should_use_orchestrator,
)


def _state_from_case(row: dict) -> dict:
    state = {
        "question": row.get("question", ""),
        "attachments": row.get("attachments") or [],
        "channel": row.get("channel", "web"),
    }
    if "execution_mode" in row:
        state["execution_mode"] = row["execution_mode"]
    return state


def run_orchestrator_suite() -> SuiteResult:
    cases = load_golden("orchestrator")
    scores: list[EvalScore] = []
    for row in cases:
        state = _state_from_case(row)
        kind = row.get("kind", "plan")

        if kind == "should_orchestrate":
            actual = should_orchestrate(state)
            expected = bool(row.get("expect", False))
            passed = actual == expected
            detail = f"actual={actual} expected={expected}"
            scores.append(
                EvalScore(
                    case_id=row["id"],
                    value=1.0 if passed else 0.0,
                    passed=passed,
                    detail=detail,
                )
            )
        elif kind == "should_use_orchestrator":
            actual = should_use_orchestrator(state)
            expected = bool(row.get("expect", False))
            passed = actual == expected
            detail = f"actual={actual} expected={expected}"
            scores.append(
                EvalScore(
                    case_id=row["id"],
                    value=1.0 if passed else 0.0,
                    passed=passed,
                    detail=detail,
                )
            )
        elif kind == "should_emit_plan_ui":
            steps = row.get("steps") or []
            mode = str(row.get("mode") or "auto")
            actual = should_emit_plan_ui(steps, mode)
            expected = bool(row.get("expect", False))
            passed = actual == expected
            detail = f"actual={actual} expected={expected}"
            scores.append(
                EvalScore(
                    case_id=row["id"],
                    value=1.0 if passed else 0.0,
                    passed=passed,
                    detail=detail,
                )
            )
        else:
            tasks = plan_tasks_rules_only(state)
            intents = [t.get("intent", "") for t in tasks]
            value, passed, detail = plan_intents_match(intents, row.get("expect_intents") or [])
            scores.append(EvalScore(case_id=row["id"], value=value, passed=passed, detail=detail))

    return SuiteResult(name="orchestrator", scores=scores)

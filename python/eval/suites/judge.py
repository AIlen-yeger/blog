"""Judge 关键词路由评测（intent_from_question / routes_from_question）。"""

from __future__ import annotations

from eval.loader import load_golden
from eval.metrics import intent_match, plan_intents_match
from eval.models import EvalScore, SuiteResult
from server.intent_router import intent_from_question, routes_from_question


def run_judge_suite() -> SuiteResult:
    cases = load_golden("judge")
    scores: list[EvalScore] = []
    for row in cases:
        kind = row.get("kind", "intent")
        if kind == "routes":
            actual = routes_from_question(
                row.get("question", ""),
                row.get("attachments"),
            )
            value, passed, detail = plan_intents_match(
                actual, row.get("expect_routes") or []
            )
        else:
            actual = intent_from_question(row["question"])
            value, passed, detail = intent_match(actual, row["expect_intent"])
        scores.append(EvalScore(case_id=row["id"], value=value, passed=passed, detail=detail))
    return SuiteResult(name="judge", scores=scores)

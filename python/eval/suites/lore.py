"""Lorebook 触发评测。"""

from __future__ import annotations

from eval.loader import load_golden
from eval.metrics import subset_ids
from eval.models import EvalScore, SuiteResult
from server.lore.lorebook import Lorebook


def run_lore_suite() -> SuiteResult:
    book = Lorebook.load_yaml("skills/character-skill/lacia-blog/lore/lacia_static.yaml")
    cases = load_golden("lore")
    scores: list[EvalScore] = []
    for row in cases:
        ids = book.select_matched_ids(
            row["message"],
            channel=row.get("channel", "web"),
            extra_text=row.get("extra_text", ""),
        )
        value, passed, detail = subset_ids(
            ids,
            row.get("expect_ids") or [],
            row.get("forbid_ids"),
        )
        scores.append(EvalScore(case_id=row["id"], value=value, passed=passed, detail=detail))
    return SuiteResult(name="lore", scores=scores)

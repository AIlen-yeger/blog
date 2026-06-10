"""Document ingest 解析评测。"""

from __future__ import annotations

from pathlib import Path

from eval.loader import fixture_path, load_golden
from eval.metrics import body_contains, exact_match
from eval.models import EvalScore, SuiteResult
from service.document_ingest import parse_text_content


def run_document_suite() -> SuiteResult:
    cases = load_golden("document")
    scores: list[EvalScore] = []
    for row in cases:
        path = fixture_path(row["fixture"])
        text = path.read_text(encoding="utf-8")
        filename = row.get("filename") or Path(row["fixture"]).name
        parsed = parse_text_content(text, filename=filename, mime=row.get("mime", "text/markdown"))
        title = parsed.title or ""
        body = parsed.body or ""

        value_t, passed_t, detail_t = exact_match(title, row.get("expect_title", ""))
        value_b, passed_b, detail_b = body_contains(body, row.get("expect_body_contains") or [])
        passed = passed_t and passed_b
        detail = f"title: {detail_t}; body: {detail_b}"
        scores.append(
            EvalScore(
                case_id=row["id"],
                value=1.0 if passed else 0.0,
                passed=passed,
                detail=detail,
            )
        )
    return SuiteResult(name="document", scores=scores)

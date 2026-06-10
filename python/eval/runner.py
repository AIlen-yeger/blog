"""Evaluation harness runner。"""

from __future__ import annotations

import json
from pathlib import Path

from eval.models import EvalReport, SuiteResult
from eval.suites import SUITE_RUNNERS

DEFAULT_SUITES = ("judge", "lore", "orchestrator", "document", "recall")
DEFAULT_THRESHOLD = 0.90


def run_suite(name: str) -> SuiteResult:
    runner = SUITE_RUNNERS.get(name)
    if not runner:
        raise ValueError(f"unknown suite: {name}")
    return runner()


def run_all(
    *,
    suites: list[str] | None = None,
    threshold: float = DEFAULT_THRESHOLD,
) -> EvalReport:
    names = suites or list(DEFAULT_SUITES)
    results: list[SuiteResult] = []
    for name in names:
        results.append(run_suite(name))
    return EvalReport(suites=results, threshold=threshold)


def format_table(report: EvalReport) -> str:
    lines = [
        f"{'Suite':<14} {'Cases':>6} {'Passed':>7} {'Rate':>7} {'Status':>6}",
    ]
    for suite in report.suites:
        if suite.skipped:
            lines.append(
                f"{suite.name:<14} {suite.total:>6} {'-':>7} {'SKIP':>7} {'SKIP':>6}"
            )
            if suite.skip_reason:
                lines.append(f"  -> {suite.skip_reason}")
            continue
        rate = suite.pass_rate * 100
        ok = suite.pass_rate >= report.threshold
        status = "OK" if ok else "FAIL"
        lines.append(
            f"{suite.name:<14} {suite.total:>6} {suite.passed_count:>7} {rate:>6.1f}% {status:>6}"
        )
        for score in suite.scores:
            if not score.passed:
                lines.append(f"  FAIL {score.case_id}: {score.detail}")
    lines.append("")
    lines.append(f"Threshold: {report.threshold:.0%} per suite (skipped suites excluded)")
    lines.append(f"Overall: {'PASS' if report.all_ok else 'FAIL'}")
    return "\n".join(lines)


def write_json_report(report: EvalReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

#!/usr/bin/env python3
"""多意图编排规则冒烟 — 薄包装 eval orchestrator 套件。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.runner import format_table, run_suite  # noqa: E402


if __name__ == "__main__":
    result = run_suite("orchestrator")
    report_threshold = 1.0
    from eval.models import EvalReport

    print(format_table(EvalReport(suites=[result], threshold=report_threshold)))
    if result.skipped or result.pass_rate < report_threshold:
        raise SystemExit(1)
    print("ok")

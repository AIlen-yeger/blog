#!/usr/bin/env python3
"""文档解析清洗冒烟 — 薄包装 eval document 套件。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.models import EvalReport
from eval.runner import format_table, run_suite  # noqa: E402


if __name__ == "__main__":
    result = run_suite("document")
    print(format_table(EvalReport(suites=[result], threshold=1.0)))
    if result.skipped or result.pass_rate < 1.0:
        raise SystemExit(1)
    print("ok")

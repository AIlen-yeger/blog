#!/usr/bin/env python3
"""Agent Evaluation Harness CLI。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval import DEFAULT_SUITES, DEFAULT_THRESHOLD, format_table, run_all, write_json_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run agent evaluation suites (no LLM).")
    parser.add_argument(
        "--suite",
        default="",
        help="Comma-separated suites (default: all). Choices: judge,lore,orchestrator,document,recall",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Per-suite minimum pass rate (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--json",
        default="",
        help="Write JSON report to path (default: reports/eval/latest.json)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suites = [s.strip() for s in args.suite.split(",") if s.strip()] or None
    report = run_all(suites=suites, threshold=args.threshold)
    print(format_table(report))

    json_path = Path(args.json) if args.json else ROOT / "reports" / "eval" / "latest.json"
    write_json_report(report, json_path)
    print(f"JSON: {json_path}")

    return 0 if report.all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

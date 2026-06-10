"""Evaluation harness 数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalScore:
    case_id: str
    value: float
    passed: bool
    detail: str = ""


@dataclass
class SuiteResult:
    name: str
    scores: list[EvalScore] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""

    @property
    def total(self) -> int:
        return len(self.scores)

    @property
    def passed_count(self) -> int:
        return sum(1 for s in self.scores if s.passed)

    @property
    def pass_rate(self) -> float:
        if not self.scores:
            return 1.0 if self.skipped else 0.0
        return self.passed_count / len(self.scores)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "total": self.total,
            "passed": self.passed_count,
            "pass_rate": round(self.pass_rate, 4),
            "cases": [
                {
                    "id": s.case_id,
                    "value": s.value,
                    "passed": s.passed,
                    "detail": s.detail,
                }
                for s in self.scores
            ],
        }


@dataclass
class EvalReport:
    suites: list[SuiteResult]
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self.threshold,
            "suites": [s.to_dict() for s in self.suites],
            "ok": self.all_ok,
        }

    @property
    def all_ok(self) -> bool:
        for suite in self.suites:
            if suite.skipped:
                continue
            if suite.pass_rate < self.threshold:
                return False
        return True

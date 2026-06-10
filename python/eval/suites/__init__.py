"""Evaluation suites."""

from eval.suites.document import run_document_suite
from eval.suites.judge import run_judge_suite
from eval.suites.lore import run_lore_suite
from eval.suites.orchestrator import run_orchestrator_suite
from eval.suites.recall import run_recall_suite

SUITE_RUNNERS = {
    "judge": run_judge_suite,
    "lore": run_lore_suite,
    "orchestrator": run_orchestrator_suite,
    "document": run_document_suite,
    "recall": run_recall_suite,
}

__all__ = [
    "SUITE_RUNNERS",
    "run_judge_suite",
    "run_lore_suite",
    "run_orchestrator_suite",
    "run_document_suite",
    "run_recall_suite",
]

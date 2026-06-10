"""加载 eval/golden/*.yaml。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

EVAL_ROOT = Path(__file__).resolve().parent
GOLDEN_DIR = EVAL_ROOT / "golden"
FIXTURES_DIR = EVAL_ROOT / "fixtures"


def load_yaml_file(path: Path) -> list[dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "cases" in raw:
        cases = raw["cases"]
    elif isinstance(raw, list):
        cases = raw
    else:
        raise ValueError(f"invalid golden format: {path}")
    if not isinstance(cases, list):
        raise ValueError(f"cases must be list: {path}")
    out: list[dict[str, Any]] = []
    for row in cases:
        if not isinstance(row, dict) or not row.get("id"):
            raise ValueError(f"each case needs id: {path}")
        out.append(row)
    return out


def load_golden(suite: str) -> list[dict[str, Any]]:
    mapping = {
        "judge": "judge_routing.yaml",
        "lore": "lore_trigger.yaml",
        "orchestrator": "orchestrator_plan.yaml",
        "document": "document_ingest.yaml",
        "recall": "recall_cases.yaml",
    }
    name = mapping.get(suite)
    if not name:
        raise ValueError(f"unknown suite: {suite}")
    path = GOLDEN_DIR / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return load_yaml_file(path)


def fixture_path(relative: str) -> Path:
    return FIXTURES_DIR / relative

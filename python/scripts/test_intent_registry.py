#!/usr/bin/env python3
"""Intent 注册表与 dispatch 冒烟。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.intent_dispatch import (  # noqa: E402
    build_planner_intent_list,
    orchestratable_intents,
    plan_step_title,
    registered_intents,
    run_intent_step,
)
from server.intent_router import parse_judge_routes, routes_from_question  # noqa: E402
from server.state import AgentState  # noqa: E402


def test_registry_bootstrap() -> None:
    intents = registered_intents()
    assert "music" in intents
    assert "aicoin" in intents
    assert "publish_note" in intents
    assert orchestratable_intents() >= {"music", "aicoin", "publish_note", "chat"}
    assert "aicoin" in build_planner_intent_list()
    assert plan_step_title("music") == "添加歌曲"


def test_routes_from_question() -> None:
    routes = routes_from_question(
        "发布笔记并加歌 https://y.qq.com/n/1",
        [],
    )
    assert routes == ["publish_note", "music"]


def test_parse_judge_routes_multi() -> None:
    routes = parse_judge_routes('{"routes":["publish_note","aicoin"]}')
    assert routes == ["publish_note", "aicoin"]


def test_unknown_intent_step() -> None:
    state: AgentState = {"question": "hi", "channel": "web"}
    result = run_intent_step(state, "unknown_intent_xyz")
    assert not result.ok
    assert "未知" in result.text


if __name__ == "__main__":
    test_registry_bootstrap()
    test_routes_from_question()
    test_parse_judge_routes_multi()
    test_unknown_intent_step()
    print("ok")

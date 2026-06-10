#!/usr/bin/env python3
"""多意图编排规则冒烟（不调用 LLM）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.route_graph.orchestrator_graph import plan_tasks, should_orchestrate  # noqa: E402
from server.route_graph.publish_note_route import wants_publish_note  # noqa: E402


def test_publish_and_music() -> None:
    q = "帮我把附件发布笔记，顺便加这首歌 https://y.qq.com/n/xxx"
    attachments = [{"kind": "document", "name": "draft.md", "url": "http://x/a.md"}]
    assert wants_publish_note(q, attachments)
    assert should_orchestrate({"question": q, "attachments": attachments})
    tasks = plan_tasks({"question": q, "attachments": attachments})
    intents = [t["intent"] for t in tasks]
    assert "publish_note" in intents
    assert "music" in intents
    print("multi:", intents)


def test_chat_only_delegate() -> None:
    state = {"question": "今天天气怎么样", "attachments": []}
    assert not should_orchestrate(state)
    print("chat-only: ok")


if __name__ == "__main__":
    test_publish_and_music()
    test_chat_only_delegate()
    print("ok")

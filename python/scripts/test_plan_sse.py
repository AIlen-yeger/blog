#!/usr/bin/env python3
"""编排 SSE 事件顺序冒烟测试（不调用 LLM）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.agent_entry import AgentEntry  # noqa: E402


def _parse_sse_events(lines: list[str]) -> list[dict]:
    out: list[dict] = []
    for line in lines:
        if not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if not payload or payload == "[DONE]":
            continue
        out.append(json.loads(payload))
    return out


def test_orchestrator_live_sse_order() -> None:
    state = {
        "question": "帮我把附件发布笔记，顺便加歌 https://y.qq.com/n/x",
        "session_id": "s1",
        "user_id": 1,
        "limit": 10,
        "access_token": "",
        "channel": "web",
        "user_name": "dev",
        "account": "dev@test.com",
        "user_role": "admin",
        "trace_id": "t1",
        "attachments": [],
        "execution_mode": "plan",
    }
    tasks = [
        {"id": "1", "intent": "publish_note", "title": "整理并预览笔记"},
        {"id": "2", "intent": "music", "title": "添加歌曲"},
    ]

    fake_publish = {
        "final_answer": "预览好了",
        "preview": {"title": "T", "content": "body", "excerpt": "e", "topicTitle": "随笔"},
        "action": "publish_note",
    }
    fake_music = {"final_answer": "已加歌"}

    entry = AgentEntry()
    with patch("server.agent_entry.run_orchestrator_step") as mock_step:
        mock_step.side_effect = [
            {**fake_publish, "ok": True, "text": fake_publish["final_answer"], "summary": "预览已生成"},
            {**fake_music, "ok": True, "text": fake_music["final_answer"], "summary": "完成"},
        ]
        lines = list(entry._stream_orchestrator_live(state, tasks, "plan"))

    events = _parse_sse_events(lines)
    types = [e.get("type") for e in events]
    assert types[0] == "plan", types
    assert types.count("plan_step") >= 4, types
    assert "delta" in types, types
    assert "action_preview" in types, types
    print("sse order:", types)


if __name__ == "__main__":
    test_orchestrator_live_sse_order()
    print("ok")

"""User memory recall 评测（需 EMBEDDING_*）。"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone

from config.config import embedding_configured
from eval.loader import FIXTURES_DIR, load_golden
from eval.metrics import recall_hit_at_k
from eval.models import EvalScore, SuiteResult
from server.embedding.embedding import EmbeddingClient
from server.embedding.embedding_user_memory import UserMemory
from server.embedding.memory_chroma_store import MemoryChromaStore


def _seed_store(store: MemoryChromaStore, embed: EmbeddingClient, seed: dict) -> None:
    user_id = seed.get("user_id", "eval_recall")
    channel = seed.get("channel", "web")
    now = datetime.now(timezone.utc).astimezone().isoformat()
    for item in seed.get("memories") or []:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        vector = embed.embed_query(text)
        if not vector:
            continue
        memory_id = str(item.get("id") or f"seed_{hash(text)}")
        payload = {
            "user_id": str(user_id),
            "text": text,
            "memory_tags": list(item.get("tags") or []),
            "channel": channel,
            "source": "eval",
            "created_at": now,
            "episode_turn_count": 0,
            "raw_turns": [],
        }
        store.upsert(memory_id, vector, payload)


def run_recall_suite() -> SuiteResult:
    if not embedding_configured():
        return SuiteResult(
            name="recall",
            skipped=True,
            skip_reason="no EMBEDDING_* configured",
        )

    seed_path = FIXTURES_DIR / "recall_seed.json"
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    user_id = seed.get("user_id", "eval_recall")
    cases = load_golden("recall")
    scores: list[EvalScore] = []

    with tempfile.TemporaryDirectory(prefix="eval_recall_") as tmp:
        os.environ["CHROMA_MEMORY_ENABLED"] = "true"
        os.environ["CHROMA_MEMORY_PATH"] = tmp

        store = MemoryChromaStore(persist_path=tmp)
        embed = EmbeddingClient()
        _seed_store(store, embed, seed)

        memory = UserMemory(auto_persist=False)
        memory._chroma = store

        for row in cases:
            top_k = int(row.get("top_k") or 5)
            hits = memory.recall(user_id, row["query"], top_k=top_k, channel=row.get("channel"))
            value, passed, detail = recall_hit_at_k(
                hits,
                expect_text_substr=row.get("expect_text_substr") or "",
                expect_tags=row.get("expect_tags"),
            )
            scores.append(EvalScore(case_id=row["id"], value=value, passed=passed, detail=detail))

    return SuiteResult(name="recall", scores=scores)

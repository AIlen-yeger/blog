"""用户记忆向量库：Chroma 持久化（不经过 MySQL）。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.config import AgentConfig
from utils.path_tools import get_project_tool

logger = logging.getLogger(__name__)


@dataclass
class MemoryRecallHit:
    """语义检索命中的一条记忆。"""

    id: str
    text: str
    memory_tags: list[str]
    distance: float | None
    channel: str
    source: str
    created_at: str
    episode_turn_count: int
    raw_turns: list[str]


def _json_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            return [raw]
    return []


def _normalize_user_id(user_id: int | str) -> str:
    return str(user_id if user_id not in (None, "") else "default")


class MemoryChromaStore:
    """Chroma collection 封装：upsert + 按 user_id 过滤检索。"""

    def __init__(
        self,
        *,
        persist_path: str | Path | None = None,
        collection_name: str | None = None,
    ) -> None:
        cfg = AgentConfig()
        root = get_project_tool()
        path = persist_path or cfg.chroma_memory_path
        self._persist_dir = Path(path) if Path(path).is_absolute() else root / path
        self._collection_name = collection_name or cfg.chroma_memory_collection
        self._persist_dir.mkdir(parents=True, exist_ok=True)

        import chromadb

        self._client = chromadb.PersistentClient(path=str(self._persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "[chroma_memory] path=%s collection=%s count=%s",
            self._persist_dir,
            self._collection_name,
            self._collection.count(),
        )

    @staticmethod
    def _metadata_from_payload(payload: dict[str, Any]) -> dict[str, str | int | float | bool]:
        """Chroma metadata 仅支持标量；列表字段 JSON 序列化。"""
        tags = payload.get("memory_tags") or []
        turns = payload.get("raw_turns") or []
        if not isinstance(tags, list):
            tags = [tags] if tags else []
        if not isinstance(turns, list):
            turns = [turns] if turns else []

        uid = payload.get("user_id")
        return {
            "user_id": _normalize_user_id(uid if uid is not None else "default"),
            "text": str(payload.get("text") or ""),
            "memory_tags": json.dumps([str(t) for t in tags], ensure_ascii=False),
            "channel": str(payload.get("channel") or "web"),
            "source": str(payload.get("source") or "chat"),
            "created_at": str(payload.get("created_at") or ""),
            "episode_turn_count": int(payload.get("episode_turn_count") or 0),
            "raw_turns": json.dumps([str(t) for t in turns], ensure_ascii=False),
        }

    @staticmethod
    def _hit_from_row(
        row_id: str,
        document: str | None,
        metadata: dict[str, Any] | None,
        distance: float | None,
    ) -> MemoryRecallHit:
        meta = metadata or {}
        return MemoryRecallHit(
            id=row_id,
            text=(document or meta.get("text") or "").strip(),
            memory_tags=_json_list(meta.get("memory_tags")),
            distance=distance,
            channel=str(meta.get("channel") or "web"),
            source=str(meta.get("source") or "chat"),
            created_at=str(meta.get("created_at") or ""),
            episode_turn_count=int(meta.get("episode_turn_count") or 0),
            raw_turns=_json_list(meta.get("raw_turns")),
        )

    def upsert(
        self,
        memory_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        text = str(payload.get("text") or "").strip()
        if not text:
            return
        meta = self._metadata_from_payload(payload)
        # 同 id 重复写入时覆盖（commit 重试等）
        self._collection.upsert(
            ids=[memory_id],
            embeddings=[vector],
            documents=[text],
            metadatas=[meta],
        )

    def query(
        self,
        user_id: int | str,
        query_vector: list[float],
        *,
        top_k: int = 5,
        channel: str | None = None,
    ) -> list[MemoryRecallHit]:
        n = max(1, min(top_k, 20))
        uid = _normalize_user_id(user_id)
        where: dict[str, Any]
        if channel:
            where = {
                "$and": [
                    {"user_id": {"$eq": uid}},
                    {"channel": {"$eq": channel}},
                ]
            }
        else:
            where = {"user_id": {"$eq": uid}}

        result = self._collection.query(
            query_embeddings=[query_vector],
            n_results=n,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]

        hits: list[MemoryRecallHit] = []
        for i, row_id in enumerate(ids):
            dist = dists[i] if i < len(dists) else None
            doc = docs[i] if i < len(docs) else None
            meta = metas[i] if i < len(metas) else None
            hits.append(self._hit_from_row(row_id, doc, meta, dist))
        return hits

    def count(self, user_id: int | str | None = None) -> int:
        if user_id is None:
            return self._collection.count()
        uid = _normalize_user_id(user_id)
        # Chroma 无高效 count-by-filter，小数据量 get 即可
        got = self._collection.get(where={"user_id": {"$eq": uid}})
        return len(got.get("ids") or [])

    def delete_user_memories(self, user_id: int | str) -> int:
        uid = _normalize_user_id(user_id)
        got = self._collection.get(where={"user_id": {"$eq": uid}})
        ids = got.get("ids") or []
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

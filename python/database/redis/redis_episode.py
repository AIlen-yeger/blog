"""用户记忆 episode（滚动摘要 + turns 缓冲）Redis 缓存。"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Any

import redis
from redis import ConnectionPool

from config.config import AgentConfig

logger = logging.getLogger(__name__)


@dataclass
class EpisodeState:
    """当前进行中的话题缓冲（按 user_id 分桶）。"""

    running_summary: str = ""
    turns: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EpisodeState:
        turns_raw = data.get("turns") or []
        turns = [str(t).strip() for t in turns_raw if str(t).strip()] if isinstance(turns_raw, list) else []
        return cls(
            running_summary=str(data.get("running_summary") or "").strip(),
            turns=turns,
        )


class RedisEpisodeStore:
    """memory:episode:{user_id} → JSON {running_summary, turns}"""

    def __init__(self, config: AgentConfig | None = None) -> None:
        cfg = config or AgentConfig()
        self._key_template = cfg.memory_episode_key
        self._ttl_sec = max(60, cfg.memory_episode_ttl)
        self.enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"
        self._client: redis.Redis | None = None
        self._local: dict[str, EpisodeState] = {}

        if not self.enabled:
            return
        try:
            pool = ConnectionPool(
                host=cfg.redis_host,
                port=cfg.redis_port,
                db=cfg.redis_db,
                password=cfg.redis_password or None,
                decode_responses=True,
            )
            client = redis.Redis(connection_pool=pool)
            client.ping()
            self._client = client
        except Exception as exc:
            logger.warning("[redis] episode store unavailable, use process memory: %s", exc)
            self.enabled = False
            self._client = None

    def _key(self, user_id: int | str) -> str:
        return self._key_template.format(user_id=str(user_id or "default"))

    def get(self, user_id: int | str) -> EpisodeState:
        key = self._key(user_id)
        if self._client:
            try:
                raw = self._client.get(key)
                if raw:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        return EpisodeState.from_dict(data)
            except Exception as exc:
                logger.warning("[redis] episode get failed user_id=%s err=%s", user_id, exc)
        return self._local.get(key, EpisodeState())

    def set(self, user_id: int | str, episode: EpisodeState) -> None:
        key = self._key(user_id)
        payload = json.dumps(asdict(episode), ensure_ascii=False)
        if self._client:
            try:
                self._client.setex(key, self._ttl_sec, payload)
                self._local.pop(key, None)
                return
            except Exception as exc:
                logger.warning("[redis] episode set failed user_id=%s err=%s", user_id, exc)
        self._local[key] = episode

    def delete(self, user_id: int | str) -> None:
        key = self._key(user_id)
        if self._client:
            try:
                self._client.delete(key)
            except Exception as exc:
                logger.warning("[redis] episode delete failed user_id=%s err=%s", user_id, exc)
        self._local.pop(key, None)

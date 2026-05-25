import json
import logging
import os
from typing import Any

import redis
from redis import ConnectionPool

logger = logging.getLogger(__name__)


def pack_message(role: str, content: str) -> str:
    return json.dumps({"role": role, "content": content}, ensure_ascii=False)


def parse_message(raw: str) -> dict[str, str] | None:
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        role = str(data.get("role") or "user").strip()
        content = str(data.get("content") or "").strip()
        if not content:
            return None
        return {"role": role, "content": content}
    except (json.JSONDecodeError, TypeError):
        return None


class RedisChatCache:
    """短期记忆：List 入队新消息、LTRIM 裁旧消息、EXPIRE 滑动续期。"""

    def __init__(
        self,
        list_key_template: str,
        ttl_sec: int,
        max_cache_msgs: int,
        host: str | None = None,
        port: int | None = None,
        db: int | None = None,
        password: str | None = None,
    ):
        self.list_key_template = list_key_template
        self.ttl_sec = ttl_sec
        self.max_cache_msgs = max(2, max_cache_msgs)
        self.enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"
        self._client: redis.Redis | None = None

        if not self.enabled:
            return

        try:
            pool = ConnectionPool(
                host=host or os.getenv("REDIS_HOST"),
                port=int(port or os.getenv("REDIS_PORT")),
                db=int(db if db is not None else os.getenv("REDIS_DB")),
                password=password or os.getenv("REDIS_PASSWORD") or None,
                decode_responses=True,
            )
            client = redis.Redis(connection_pool=pool)
            client.ping()
            self._client = client
        except Exception as exc:
            logger.warning("[redis] unavailable, fallback to mysql only: %s", exc)
            self.enabled = False
            self._client = None

    def _key(self, session_id: str) -> str:
        return self.list_key_template.format(session_id=session_id)

    def get_recent(self, session_id: str, need: int) -> list[dict[str, str]]:
        if not self.enabled or not self._client or need <= 0:
            return []
        try:
            raw_list = self._client.lrange(self._key(session_id), -need, -1)
            messages: list[dict[str, str]] = []
            for raw in raw_list:
                msg = parse_message(raw)
                if msg:
                    messages.append(msg)
            return messages
        except Exception as exc:
            logger.warning("[redis] lrange failed session_id=%s err=%s", session_id, exc)
            return []

    def append_turn(
        self,
        session_id: str,
        user_question: str,
        assistant_answer: str,
    ) -> None:
        if not self.enabled or not self._client:
            return
        key = self._key(session_id)
        try:
            pipe = self._client.pipeline()
            pipe.rpush(
                key,
                pack_message("user", user_question),
                pack_message("assistant", assistant_answer),
            )
            pipe.ltrim(key, -self.max_cache_msgs, -1)
            pipe.expire(key, self.ttl_sec)
            pipe.execute()
        except Exception as exc:
            logger.warning("[redis] append failed session_id=%s err=%s", session_id, exc)

    def replace_recent(self, session_id: str, rows: list[dict[str, str]]) -> None:
        if not self.enabled or not self._client or not rows:
            return
        key = self._key(session_id)
        try:
            payload = [
                pack_message(r.get("role", "user"), r.get("content", ""))
                for r in rows
                if (r.get("content") or "").strip()
            ]
            if not payload:
                return
            pipe = self._client.pipeline()
            pipe.delete(key)
            pipe.rpush(key, *payload)
            pipe.ltrim(key, -self.max_cache_msgs, -1)
            pipe.expire(key, self.ttl_sec)
            pipe.execute()
        except Exception as exc:
            logger.warning("[redis] replace failed session_id=%s err=%s", session_id, exc)

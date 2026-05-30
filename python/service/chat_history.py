import logging

from config.config import AgentConfig
from database.mysql.mysql_db import MysqlRepo
from database.redis.redis_client import RedisChatCache

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """
    短期记忆：Redis List（先读，不够再回填）
    长期归档：MySQL（登录用户每轮双写）
    """

    def __init__(self, config: AgentConfig | None = None):
        cfg = config or AgentConfig()
        self.mysql = MysqlRepo(cfg)
        self.redis = RedisChatCache(
            list_key_template=cfg.chat_list_key,
            ttl_sec=cfg.chat_ttl,
            max_cache_msgs=cfg.max_cache_msgs,
            config=cfg,
        )

    def get_recent_history(
        self,
        session_id: str,
        user_id: int,
        limit: int | None = None,
    ) -> list[dict[str, str]]:
        if not session_id:
            return []

        if limit is None:
            limit = AgentConfig().history_limit
        need = max(1, limit) * 2
        cached = self.redis.get_recent(session_id, need)
        if len(cached) >= need:
            return cached

        # 游客：只用 Redis，没有则返回已有片段
        if user_id <= 0:
            return cached

        # 已登录：Redis 不足时从 MySQL 拉最近记录并回填 List
        rows = self.mysql.get_recent_history(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
        )
        if rows:
            self.redis.replace_recent(session_id, rows)
        return rows if rows else cached

    def get_bug_history(
        self,
        session_id: str,
        limit: int | None = None,
        user_id: int = None,
    ) -> list[dict[str, str]]:
        if not session_id:
            return []

        if limit is None:
            limit = AgentConfig().history_limit

        rows = self.mysql.get_bug_history(session_id, limit)
        return rows if rows else []

    def save_bug_turn(
        self,
        session_id: str,
        user_id: int,
        incident_id: str,
        user_question: str,
        assistant_answer: str,
    ) -> None:
        if not session_id:
            return
        question = (user_question or "").strip()
        answer = (assistant_answer or "").strip()
        if not question and not answer:
            return
        if question:
            self.mysql.save_bug_message(
                session_id=session_id,
                user_id=user_id,
                incident_id=incident_id,
                role="user",
                content=question,
            )
        if answer:
            self.mysql.save_bug_message(
                session_id=session_id,
                user_id=user_id,
                incident_id=incident_id,
                role="assistant",
                content=answer,
            )

    def save_turn(
        self,
        session_id: str,
        user_id: int,
        user_question: str,
        assistant_answer: str,
    ) -> None:
        if not session_id:
            return

        question = (user_question or "").strip()
        answer = (assistant_answer or "").strip()
        if not question and not answer:
            return

        if user_id > 0:
            self.mysql.save_turn(
                session_id=session_id,
                user_question=question,
                assistant_answer=answer,
                user_id=user_id,
            )

        self.redis.append_turn(session_id, question, answer)



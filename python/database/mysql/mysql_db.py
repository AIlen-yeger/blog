import logging
import os

try:
    import pymysql
except Exception:  # pragma: no cover - optional dependency
    pymysql = None

logger = logging.getLogger(__name__)


class MysqlRepo:
    def __init__(self):
        self.host = os.getenv("MYSQL_HOST")
        self.port = int(os.getenv("MYSQL_PORT"))
        self.user = os.getenv("MYSQL_USER")
        self.password = os.getenv("MYSQL_PASSWORD")
        self.database = os.getenv("MYSQL_DB")
        self.enabled = os.getenv("CHAT_HISTORY_ENABLED", "true").lower() == "true"

    def connect(self):
        if not self.enabled:
            return None

        if pymysql is None:
            return None

        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def get_recent_history(
        self,
        session_id: str,
        user_id: int,
        limit: int = 5,
    ) -> list[dict[str, str]]:
        if not session_id:
            return []
        conn = self.connect()
        if conn is None:
            return []

        try:
            with conn.cursor() as cur:
                sql = """
                    SELECT role, content
                    FROM ai_chat_message
                    WHERE session_id = %s
                      AND user_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                """
                cur.execute(sql, (session_id, user_id, limit * 2))
                rows = cur.fetchall() or []
            rows.reverse()
            return [
                self._to_chat_message(r.get("content", ""), r.get("role"))
                for r in rows
                if r.get("content")
            ]
        except Exception as e:
            logger.warning(
                "[history] get recent failed session_id=%s err=%s",
                session_id,
                e,
            )
            return []
        finally:
            conn.close()

    @staticmethod
    def _to_chat_message(content: str, role: str | None) -> dict[str, str]:
        return {"role": (role or "user").strip(), "content": (content or "").strip()}

    def save_turn(
        self,
        session_id: str,
        user_question: str,
        assistant_answer: str,
        user_id: int = 0,
    ) -> bool:
        if not session_id:
            return False
        conn = self.connect()
        if conn is None:
            return False

        sql = """
            INSERT INTO ai_chat_message (session_id, user_id, role, content, create_time)
            VALUES (%s, %s, %s, %s, NOW())
        """
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (session_id, user_id, "user", user_question))
                cur.execute(sql, (session_id, user_id, "assistant", assistant_answer))
            return True
        except Exception as e:
            logger.warning("[history] save turn failed session_id=%s err=%s", session_id, e)
            return False
        finally:
            conn.close()

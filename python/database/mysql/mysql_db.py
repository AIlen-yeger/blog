import logging

try:
    import pymysql
except Exception:  # pragma: no cover - optional dependency
    pymysql = None

from config.config import AgentConfig

logger = logging.getLogger(__name__)

class MysqlRepo:
    def __init__(self, config: AgentConfig | None = None):
        cfg = config or AgentConfig()
        self.host = cfg.mysql_host
        self.port = cfg.mysql_port
        self.user = cfg.mysql_user
        self.password = cfg.mysql_password
        self.database = cfg.mysql_database
        self.enabled = __import__("os").getenv("CHAT_HISTORY_ENABLED", "true").lower() == "true"

    def connect(self):
        if not self.enabled:
            return None

        if pymysql is None:
            logger.warning("[mysql] pymysql not installed, chat history disabled")
            return None

        if not self.host or not self.user or not self.database:
            logger.warning("[mysql] incomplete config, chat history disabled")
            return None

        try:
            return pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password or "",
                database=self.database,
                charset="utf8mb4",
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor,
            )
        except Exception as exc:
            logger.warning(
                "[mysql] connect failed host=%s db=%s err=%s",
                self.host,
                self.database,
                exc,
            )
            return None

    def get_recent_history(
        self,
        session_id: str,
        user_id: int,
        limit: int = 10,
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
                # session_id 已区分 qq:private:{qq} 与 web；channel 列供统计/筛选
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
            if conn is not None:
                conn.close()

    def get_bug_history(
        self,
        session_id: str,
        limit: int = 10,
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
                    FROM agent_bug_message
                    WHERE session_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                """
                cur.execute(sql, (session_id, limit * 2))
                rows = cur.fetchall() or []
            rows.reverse()
            return [
                self._to_chat_message(r.get("content", ""), r.get("role"))
                for r in rows
                if r.get("content")
            ]
        except Exception as e:
            logger.warning(
                "[history] get bug history failed session_id=%s err=%s",
                session_id,
                e,
            )
            return []
        finally:
            if conn is not None:
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
        *,
        channel: str = "web",
    ) -> bool:
        if not session_id:
            return False
        conn = self.connect()
        if conn is None:
            return False

        ch = (channel or "web").strip().lower()[:16] or "web"
        sql = """
            INSERT INTO ai_chat_message (session_id, user_id, channel, role, content, create_time)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (session_id, user_id, ch, "user", user_question))
                cur.execute(sql, (session_id, user_id, ch, "assistant", assistant_answer))
            return True
        except Exception as e:
            logger.warning("[history] save turn failed session_id=%s err=%s", session_id, e)
            return False
        finally:
            if conn is not None:
                conn.close()


    def save_bug_message(
        self,
        session_id: str,
        user_id: int,
        incident_id: str,
        role: str,
        content: str,
    ) -> bool:
        if not session_id:
            return False
        conn = self.connect()
        if conn is None:
            return False

        sql = """
            INSERT INTO agent_bug_message (session_id, user_id, incident_id, role, content, create_time)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """
        try:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (session_id, user_id, incident_id, (role or "assistant").strip(), content),
                )
            return True
        except Exception as e:
            logger.warning("[history] save bug message failed session_id=%s err=%s", session_id, e)
            return False
        finally:
            if conn is not None:
                conn.close()

    def ensure_incident(
        self,
        *,
        incident_id: str,
        session_id: str,
        trace_id: str | None,
        user_id: int,
        symptoms: str,
        source: str = "user_report",
    ) -> bool:
        conn = self.connect()
        if conn is None:
            return False
        sql = """
            INSERT INTO agent_incident (
                incident_id, trace_id, session_id, user_id, source, status, symptoms
            ) VALUES (%s, %s, %s, %s, %s, 'open', %s)
            ON DUPLICATE KEY UPDATE
                updated_at = CURRENT_TIMESTAMP,
                symptoms = IF(
                    CHAR_LENGTH(TRIM(symptoms)) = 0,
                    VALUES(symptoms),
                    symptoms
                )
        """
        try:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (incident_id, trace_id, session_id, user_id, source, symptoms),
                )
            return True
        except Exception as e:
            logger.warning("[incident] ensure failed incident_id=%s err=%s", incident_id, e)
            return False
        finally:
            if conn is not None:
                conn.close()

    def update_incident(
        self,
        *,
        incident_id: str,
        status: str | None = None,
        root_cause: str | None = None,
        resolution: str | None = None,
        symptoms: str | None = None,
    ) -> bool:
        conn = self.connect()
        if conn is None:
            return False

        fields: list[str] = []
        values: list[object] = []
        for col, val in (
            ("status", status),
            ("root_cause", root_cause),
            ("resolution", resolution),
            ("symptoms", symptoms),
        ):
            if val is not None and str(val).strip():
                fields.append(f"{col} = %s")
                values.append(val.strip())
        if not fields:
            return False

        if status and status.strip().lower() == "resolved":
            fields.append("resolved_at = NOW()")

        sql = f"UPDATE agent_incident SET {', '.join(fields)}, updated_at = NOW() WHERE incident_id = %s"
        values.append(incident_id)
        try:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(values))
                return cur.rowcount > 0
        except Exception as e:
            logger.warning("[incident] update failed incident_id=%s err=%s", incident_id, e)
            return False
        finally:
            if conn is not None:
                conn.close()



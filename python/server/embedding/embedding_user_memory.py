"""用户记忆：多轮滚动摘要 + Chroma 向量持久化（不写 MySQL）。"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.config import AgentConfig, embedding_configured, normalize_openai_base_url
from database.redis.redis_episode import EpisodeState, RedisEpisodeStore
from server.embedding.embedding import EmbeddingClient
from server.embedding.memory_chroma_store import MemoryChromaStore, MemoryRecallHit
from utils.log.token_usage import record_from_response
from utils.log.trace_log import log_event, record_model
from utils.path_tools import get_abs_path

logger = logging.getLogger(__name__)


def _summary_llm_recoverable(exc: BaseException) -> bool:
    """余额不足、限流等：记忆子图降级，不阻断主对话。"""
    name = type(exc).__name__
    if name in ("APIStatusError", "RateLimitError", "AuthenticationError"):
        return True
    msg = str(exc).lower()
    return any(
        k in msg
        for k in (
            "insufficient balance",
            "402",
            "429",
            "rate limit",
            "quota",
            "余额",
        )
    )


MemoryAction = Literal["continue", "commit", "split"]

_user_memory_singleton: UserMemory | None = None


@dataclass
class MemoryProcessResult:
    """单次 process_user_message 的处理结果。"""

    action: MemoryAction
    running_summary: str
    committed_memory: str | None = None
    memory_tags: list[str] = field(default_factory=list)
    episode_complete: bool = False
    topic_shift: bool = False
    extra_summary: str = ""
    memory_id: str = ""  # persist 成功后由 _maybe_persist 回填


@dataclass
class MemoryVectorRecord:
    """一条待写入 / 已写入向量库的记录。"""

    id: str
    vector: list[float]
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "vector": self.vector, "payload": self.payload}


@dataclass
class SummaryLLMOutput:
    action: MemoryAction
    running_summary: str
    memory_tags: list[str]
    episode_complete: bool
    topic_shift: bool
    extra_summary: str


def _parse_summary_llm_output(raw: str) -> SummaryLLMOutput:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("summary response must be a JSON object")

    raw_action = str(data.get("action") or "continue").strip().lower()
    if raw_action in ("commit", "split", "continue"):
        action: MemoryAction = raw_action  # type: ignore[assignment]
    elif raw_action in ("1", "true", "yes"):
        action = "commit"
    else:
        action = "continue"

    tags_raw = data.get("memory_tags") or []
    if isinstance(tags_raw, list):
        tags = [str(t).strip() for t in tags_raw if str(t).strip()]
    else:
        tags = [str(tags_raw).strip()] if str(tags_raw).strip() else []

    return SummaryLLMOutput(
        action=action,
        running_summary=str(data.get("running_summary") or "").strip(),
        memory_tags=tags,
        episode_complete=bool(data.get("episode_complete")),
        topic_shift=bool(data.get("topic_shift")),
        extra_summary=str(data.get("extra_summary") or "").strip(),
    )


class UserMemory:
    """
    滚动摘要 + 话题边界。

    - commit/split 且 committed_memory 非空时，经 _maybe_persist 写入 Chroma
    - recall：对当前用户消息做语义检索，拼进 chat system 等
    """

    def __init__(self, *, max_turns: int = 8, auto_persist: bool = True) -> None:
        config = AgentConfig()
        self.embedding = EmbeddingClient()
        model_name = (config.chat_model_name or "deepseek-chat").strip()
        self.summary_model = ChatOpenAI(
            model=model_name,
            api_key=config.chat_api_key,
            base_url=normalize_openai_base_url(config.chat_base_url),
            temperature=0,
            timeout=90,
            max_retries=1,
        )
        self._max_turns = max(2, max_turns)
        self._auto_persist = auto_persist
        self._system_prompt = self._load_summary_prompt()
        self._episode_store = RedisEpisodeStore(config)
        self._chroma: MemoryChromaStore | None = None
        if config.chroma_memory_enabled:
            self._chroma = MemoryChromaStore()

    def _load_summary_prompt(self) -> str:
        return get_abs_path("skills/summary.md").read_text(encoding="utf-8")

    def _episode_key(self, user_id: int | str) -> str:
        return str(user_id or "default")

    def get_episode(self, user_id: int | str = 0) -> EpisodeState:
        return self._episode_store.get(user_id)

    def _save_episode(self, user_id: int | str, episode: EpisodeState) -> None:
        self._episode_store.set(user_id, episode)

    def reset_episode(self, user_id: int | str = 0) -> None:
        self._episode_store.delete(user_id)

    def memory_count(self, user_id: int | str | None = None) -> int:
        if not self._chroma:
            return 0
        return self._chroma.count(user_id)

    def _build_user_payload(self, episode: EpisodeState, message: str) -> str:
        lines = [
            "【已有滚动摘要】",
            episode.running_summary.strip() if episode.running_summary else "（无）",
            "",
            "【本轮已收集的用户原话（按时间序）】",
        ]
        if episode.turns:
            for i, t in enumerate(episode.turns, 1):
                lines.append(f"{i}. {t.strip()}")
        else:
            lines.append("（无）")
        lines.extend(["", "【本条用户新消息】", message.strip()])
        return "\n".join(lines)

    def _invoke_summary(self, episode: EpisodeState, message: str) -> SummaryLLMOutput:
        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=self._build_user_payload(episode, message)),
        ]
        cfg = AgentConfig()
        record_model(cfg.summary_model_name or cfg.chat_model_name)
        resp = self.summary_model.invoke(messages)
        record_from_response(
            phase="memory.summary",
            model=cfg.summary_model_name or cfg.chat_model_name,
            messages=messages,
            response=resp,
        )
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        return _parse_summary_llm_output(content)

    def _persist_memory(
        self,
        user_id: int | str,
        result: MemoryProcessResult,
        *,
        channel: str = "web",
        raw_turns: list[str] | None = None,
    ) -> MemoryVectorRecord | None:
        text = (result.committed_memory or "").strip()
        if not text:
            return None

        vector = self.embedding.embed_query(text)
        now = datetime.now(timezone.utc).astimezone()
        memory_id = f"mem_{now.strftime('%Y%m%d')}_{user_id}_{uuid.uuid4().hex[:8]}"
        turns = [t.strip() for t in (raw_turns or []) if t.strip()]

        payload = {
            "user_id": self._episode_key(user_id),
            "text": text,
            "memory_tags": list(result.memory_tags),
            "channel": channel,
            "source": "chat",
            "created_at": now.isoformat(),
            "episode_turn_count": len(turns),
            "raw_turns": turns,
        }
        record = MemoryVectorRecord(id=memory_id, vector=vector, payload=payload)

        if self._chroma:
            self._chroma.upsert(memory_id, vector, payload)
            logger.info(
                "[user_memory] chroma upsert id=%s user_id=%s tags=%s",
                memory_id,
                user_id,
                result.memory_tags,
            )
        else:
            logger.warning(
                "[user_memory] CHROMA_MEMORY_ENABLED=false，跳过持久化 id=%s",
                memory_id,
            )
        return record

    def _maybe_persist(
        self,
        user_id: int | str,
        result: MemoryProcessResult,
        *,
        channel: str,
        raw_turns: list[str],
    ) -> None:
        """
        条件写入 Chroma 的薄封装（在 process_user_message 里调用）。

        - auto_persist=False：测试或只跑摘要、不入库
        - committed_memory 为空（continue）：无内容可存，直接 return
        - 否则 _persist_memory，并把 record.id 写回 result.memory_id 供上层日志/追踪
        """
        if not self._auto_persist or not result.committed_memory:
            return
        record = self._persist_memory(
            user_id,
            result,
            channel=channel,
            raw_turns=raw_turns,
        )
        if record:
            result.memory_id = record.id

    def recall(
        self,
        user_id: int | str,
        query: str,
        *,
        top_k: int = 5,
        channel: str | None = None,
    ) -> list[MemoryRecallHit]:
        """按 user_id 过滤的语义检索（用于拼 system skills）。"""
        q = (query or "").strip()
        if not q or not self._chroma or not embedding_configured():
            return []
        vector = self.embedding.embed_query(q)
        if not vector:
            return []
        return self._chroma.query(user_id, vector, top_k=top_k, channel=channel)

    def format_recall_for_prompt(
        self,
        user_id: int | str,
        query: str,
        *,
        top_k: int = 5,
        channel: str | None = None,
    ) -> str:
        """将 recall 结果格式化为可插入 system 的文本块。"""
        hits = self.recall(user_id, query, top_k=top_k, channel=channel)
        if not hits:
            return ""
        lines = ["【与用户相关的长期记忆（语义检索）】"]
        for i, h in enumerate(hits, 1):
            tags = "、".join(h.memory_tags) if h.memory_tags else "无标签"
            lines.append(f"{i}. [{tags}] {h.text}")
        return "\n".join(lines)

    def process_user_message(
        self,
        message: str,
        *,
        user_id: int | str = 0,
        channel: str = "web",
    ) -> MemoryProcessResult:
        text = (message or "").strip()
        if not text:
            return MemoryProcessResult(
                action="continue",
                running_summary="",
                committed_memory=None,
            )

        episode = self.get_episode(user_id)
        episode.turns.append(text)
        if len(episode.turns) > self._max_turns:
            episode.turns = episode.turns[-self._max_turns :]

        force_commit = len(episode.turns) >= self._max_turns
        turns_snapshot = list(episode.turns)

        try:
            out = self._invoke_summary(episode, text)
        except Exception as exc:
            if _summary_llm_recoverable(exc):
                if episode.turns and episode.turns[-1] == text:
                    episode.turns.pop()
                logger.warning(
                    "[user_memory] summary skipped (recoverable) user_id=%s err=%s",
                    user_id,
                    str(exc)[:200],
                )
                return MemoryProcessResult(
                    action="continue",
                    running_summary=episode.running_summary,
                    committed_memory=None,
                )
            logger.exception("[user_memory] summary llm failed user_id=%s", user_id)
            if episode.turns and episode.turns[-1] == text:
                episode.turns.pop()
            raise

        action = out.action
        running = out.running_summary
        tags = out.memory_tags
        episode_complete = out.episode_complete
        topic_shift = out.topic_shift
        extra = out.extra_summary

        if force_commit and action == "continue":
            action = "commit"
            episode_complete = True

        if action == "split":
            committed = running or episode.running_summary
            episode.running_summary = extra or text
            episode.turns = [text]
            result = MemoryProcessResult(
                action="split",
                running_summary=episode.running_summary,
                committed_memory=committed,
                memory_tags=tags,
                episode_complete=True,
                topic_shift=True,
                extra_summary=extra,
            )
            self._maybe_persist(user_id, result, channel=channel, raw_turns=turns_snapshot)
            self._save_episode(user_id, episode)
            return result

        if action == "commit":
            committed = running or episode.running_summary
            if topic_shift and not episode_complete:
                episode.running_summary = ""
                episode.turns = [text]
                self._save_episode(user_id, episode)
            else:
                self.reset_episode(user_id)
            result = MemoryProcessResult(
                action="commit",
                running_summary=running,
                committed_memory=committed,
                memory_tags=tags,
                episode_complete=episode_complete or topic_shift,
                topic_shift=topic_shift,
                extra_summary=extra,
            )
            self._maybe_persist(user_id, result, channel=channel, raw_turns=turns_snapshot)
            return result

        if running:
            episode.running_summary = running
        self._save_episode(user_id, episode)
        return MemoryProcessResult(
            action="continue",
            running_summary=episode.running_summary,
            committed_memory=None,
            memory_tags=tags,
            episode_complete=episode_complete,
            topic_shift=topic_shift,
            extra_summary=extra,
        )


def get_user_memory() -> UserMemory:
    """进程内单例，供 AgentEntry / chat 共用同一套 episode 与 Chroma。"""
    global _user_memory_singleton
    if _user_memory_singleton is None:
        _user_memory_singleton = UserMemory()
    return _user_memory_singleton

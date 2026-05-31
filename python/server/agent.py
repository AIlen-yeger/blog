import logging
import os
from typing import Any

from config.config import AgentConfig
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from server.prompt_skills import build_system_prompt
from service.chat_history import ChatHistoryService
from utils.trace_log import answer_log_fields, bind_trace_from_state, log_event, record_model

logger = logging.getLogger(__name__)


def _read_env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return default


def _normalize_base_url(url: str) -> str:
    base = (url or "https://api.deepseek.com").strip().rstrip("/")
    if base.endswith("/v1"):
        return base
    return base + "/v1"


class ChatModel:
    def __init__(self):
        config = AgentConfig()
        self.model = config.chat_model_name
        self.api_key = config.chat_api_key
        self.base_url = _normalize_base_url(config.chat_base_url)
        self.temperature = config.temperature

        if not self.model:
            raise RuntimeError("未配置 DP_MODEL（或 dp-model）")
        if not self.api_key:
            raise RuntimeError(
                "未配置 DP_CHAT_API_KEY / DP_AGENT_API_KEY，请在 python/.env 中填写 DeepSeek 密钥"
            )

        logger.info(
            "[agent] llm ready model=%s base_url=%s key=***%s",
            self.model,
            self.base_url,
            self.api_key[-4:] if len(self.api_key) >= 4 else "****",
        )

        self.chat_llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            timeout=90,
            max_retries=1,
        )
        self.history = ChatHistoryService(config)

    def chat(self, question: str, session_id: str, user_id: int, limit: int | None = None, *, trace_id: str = ""):
        """流式对话：逐 token 产出 SSE delta，结束后写入历史。"""
        bind_trace_from_state(
            {"trace_id": trace_id, "session_id": session_id, "user_id": user_id},
            intent="chat",
        )
        record_model(self.model)
        if limit is None:
            limit = AgentConfig().history_limit
        system_prompt = build_system_prompt()

        history_message = self.history.get_recent_history(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
        )

        messages = [
            SystemMessage(content=system_prompt),
            *self._to_lc_messages(history_message),
            HumanMessage(content=question),
        ]

        full_answer = []
        try:
            for chunk in self.chat_llm.stream(messages):
                content = chunk.content
                if isinstance(content, str):
                    delta = content
                elif isinstance(content, list):
                    delta = "".join(
                        str(item.get("text", "")) for item in content if isinstance(item, dict)
                    )
                else:
                    delta = ""

                if delta:
                    full_answer.append(delta)
                    yield {"type": "delta", "content": delta}
        except Exception as exc:
            logger.exception("[agent] llm stream failed session_id=%s", session_id)
            yield {
                "code": 50000,
                "message": f"模型调用失败：{exc}。请检查 DP_AGENT_API_KEY 与网络。",
            }
            return

        answer = "".join(full_answer).strip()
        if not answer:
            yield {
                "code": 50000,
                "message": "模型未返回内容，请检查 DP_MODEL 是否为 deepseek-chat 且 API 额度正常",
            }
            return

        self.history.save_turn(
            session_id=session_id,
            user_id=user_id,
            user_question=question,
            assistant_answer=answer,
        )
        log_event(
            "chat.done",
            model=self.model,
            session_id=session_id,
            user_id=user_id,
            **answer_log_fields(answer),
        )

    def rewrite_music_stream(
        self,
        *,
        question: str,
        draft: str,
        session_id: str,
        user_id: int,
        limit: int | None = None,
        trace_id: str = "",
    ):
        """千问 ReAct 草稿 → DeepSeek 流式润色（保留事实、Kohaku 语气）。"""
        bind_trace_from_state(
            {"trace_id": trace_id, "session_id": session_id, "user_id": user_id},
            intent="music",
        )
        record_model(self.model)
        if limit is None:
            limit = AgentConfig().history_limit

        system_prompt = build_system_prompt(intent="music", user_logged_in=True)
        user_content = (
            f"用户问题：{question.strip()}\n\n"
            "以下是音乐助手根据工具查询得到的事实摘要（草稿）。"
            "请用 Kohaku 的语气重新写给用户。\n"
            "硬性要求：\n"
            "- 保留草稿中的全部事实、数字、歌名、艺人、次数等，不得编造或删改\n"
            "- 不要提到草稿、工具、模型等内部流程\n"
            "- 风格自然、有温度\n\n"
            f"【事实草稿】\n{draft.strip()}"
        )

        history_message = self.history.get_recent_history(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
        )
        messages = [
            SystemMessage(content=system_prompt),
            *self._to_lc_messages(history_message),
            HumanMessage(content=user_content),
        ]

        full_answer: list[str] = []
        try:
            for chunk in self.chat_llm.stream(messages):
                content = chunk.content
                if isinstance(content, str):
                    delta = content
                elif isinstance(content, list):
                    delta = "".join(
                        str(item.get("text", "")) for item in content if isinstance(item, dict)
                    )
                else:
                    delta = ""
                if delta:
                    full_answer.append(delta)
                    yield {"type": "delta", "content": delta}
        except Exception as exc:
            logger.exception("[agent] music polish stream failed session_id=%s", session_id)
            yield {"code": 50000, "message": f"回复润色失败：{exc}"}
            return

        answer = "".join(full_answer).strip() or draft.strip()
        self.history.save_turn(
            session_id=session_id,
            user_id=user_id,
            user_question=question,
            assistant_answer=answer,
        )
        log_event(
            "music.polish.done",
            model=self.model,
            session_id=session_id,
            user_id=user_id,
            draft_length=len(draft),
            **answer_log_fields(answer),
        )

    @staticmethod
    def _to_lc_messages(history_messages: list[dict[str, str]]) -> list[Any]:
        lc_messages: list[Any] = []
        for m in history_messages:
            role = (m.get("role") or "").strip().lower()
            content = (m.get("content") or "").strip()
            if not content:
                continue
            if role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        return lc_messages

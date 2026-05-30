import logging
import os
from typing import Any

from config.config import AgentConfig
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from server.prompt_skills import build_system_prompt
from service.chat_history import ChatHistoryService
from utils.trace_log import record_model

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
        self.model = _read_env("DP_MODEL", "dp-model", "deepseek-chat")
        self.api_key = _read_env("DP_AGENT_API_KEY", "dp-agent-api-key")
        self.base_url = "https://api.deepseek.com"
        self.temperature = config.temperature

        if not self.model:
            raise RuntimeError("未配置 DP_MODEL（或 dp-model）")
        if not self.api_key:
            raise RuntimeError("未配置 DP_AGENT_API_KEY（或 dp-agent-api-key），请在 python/.env 中填写")

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

    def chat(self, question: str, session_id: str, user_id: int, limit: int | None = None):
        """流式对话：逐 token 产出 SSE delta，结束后写入历史。"""
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

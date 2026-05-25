import os
from typing import Any

from config.config import AgentConfig
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from service.chat_history import ChatHistoryService
from utils.path_tools import get_abs_path


class ChatModel:
    def __init__(self):
        config = AgentConfig()
        self.model = os.getenv("dp-model")
        self.api_key = os.getenv("dp-agent-api-key")
        self.base_url = os.getenv("dp-agent-api-url", "https://api.deepseek.com")
        self.temperature = config.temperature
        self.chat_llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
        )
        self.history = ChatHistoryService(config)

    def chat(self, question: str, session_id: str, user_id: int, limit: int = 5):
        """流式对话：逐 token 产出 SSE delta，结束后写入历史。"""
        prompt_path = get_abs_path("prompt/system_prompt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()

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

        answer = "".join(full_answer).strip()
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

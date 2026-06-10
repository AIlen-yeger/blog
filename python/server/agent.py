import logging
from typing import Any

from config.config import AgentConfig
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from server.skills_server.prompt_assembler import PromptContext, assemble_chat_system
from service.chat_history import ChatHistoryService
from utils.llm_errors import format_llm_user_message
from utils.log.token_usage import (
    log_prompt_assembled,
    record_from_response,
    record_llm_usage,
    request_token_summary_fields,
    usage_from_ai_message,
)
from utils.log.trace_log import answer_log_fields, bind_trace_from_state, log_event, record_model

logger = logging.getLogger(__name__)


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
            stream_usage=True,
        )
        self.history = ChatHistoryService(config)

    def _build_chat_system(
        self,
        *,
        question: str,
        user_id: int,
        channel: str,
        developer_name: str,
        intent: str = "chat",
        user_logged_in: bool = False,
    ) -> str:
        return assemble_chat_system(
            PromptContext(
                intent=intent or "chat",
                channel=channel,
                user_message=question,
                user_id=user_id,
                user_logged_in=user_logged_in,
                developer_name=developer_name or None,
            )
        )

    def chat(
        self,
        question: str,
        session_id: str,
        user_id: int,
        limit: int | None = None,
        *,
        trace_id: str = "",
        channel: str = "web",
        developer_name: str = "",
        intent: str = "chat",
        user_logged_in: bool = False,
    ):
        """流式对话：逐 token 产出 SSE delta，结束后写入历史。"""
        bind_trace_from_state(
            {"trace_id": trace_id, "session_id": session_id, "user_id": user_id},
            intent=intent or "chat",
        )
        record_model(self.model)
        if limit is None:
            limit = AgentConfig().history_limit
        system_prompt = self._build_chat_system(
            question=question,
            user_id=user_id,
            channel=channel,
            developer_name=developer_name,
            intent=intent,
            user_logged_in=user_logged_in,
        )

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
        log_prompt_assembled(
            phase="chat",
            system_prompt=system_prompt,
            intent=intent or "chat",
            channel=channel,
        )

        full_answer = []
        stream_usage: tuple[int, int, int] | None = None
        try:
            for chunk in self.chat_llm.stream(messages):
                u = usage_from_ai_message(chunk)
                if u:
                    stream_usage = u
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
            yield {"code": 50000, "message": format_llm_user_message(exc)}
            return

        answer = "".join(full_answer).strip()
        if not answer:
            yield {
                "code": 50000,
                "message": "模型未返回内容，请检查 DP_MODEL 是否为 deepseek-chat 且 API 额度正常",
            }
            return

        if stream_usage:
            p, c, _ = stream_usage
            record_llm_usage(
                phase="chat",
                model=self.model,
                prompt_tokens=p,
                completion_tokens=c,
                estimated=False,
                channel=channel,
                trace_id=trace_id or None,
            )
        else:
            record_from_response(
                phase="chat",
                model=self.model,
                messages=messages,
                completion_text=answer,
                channel=channel,
                trace_id=trace_id or None,
            )

        self.history.save_turn(
            session_id=session_id,
            user_id=user_id,
            user_question=question,
            assistant_answer=answer,
            channel=(channel or "web").strip().lower() or "web",
        )
        log_event(
            "chat.done",
            model=self.model,
            session_id=session_id,
            user_id=user_id,
            **answer_log_fields(answer),
            **request_token_summary_fields(trace_id or None),
        )

    def chat_once(
        self,
        question: str,
        session_id: str,
        user_id: int,
        limit: int | None = None,
        *,
        intent: str = "chat",
        trace_id: str = "",
        channel: str = "qq",
        developer_name: str = "",
        user_logged_in: bool = False,
    ) -> str:
        """非流式对话：QQ 等渠道一次性拿全文。"""
        bind_trace_from_state(
            {"trace_id": trace_id, "session_id": session_id, "user_id": user_id},
            intent=intent or "chat",
        )
        record_model(self.model)

        system_prompt = self._build_chat_system(
            question=question,
            user_id=user_id,
            channel=channel,
            developer_name=developer_name,
            intent=intent,
            user_logged_in=user_logged_in,
        )

        if limit is None:
            limit = AgentConfig().history_limit
        messages = [
            SystemMessage(content=system_prompt),
            *self._to_lc_messages(
                self.history.get_recent_history(
                    session_id=session_id,
                    user_id=user_id,
                    limit=limit,
                )
            ),
            HumanMessage(content=question),
        ]
        log_prompt_assembled(
            phase="chat",
            system_prompt=system_prompt,
            intent=intent or "chat",
            channel=channel,
        )
        try:
            resp = self.chat_llm.invoke(messages)
            content = resp.content
            if isinstance(content, str):
                answer = content.strip()
            elif isinstance(content, list):
                answer = "".join(
                    str(item.get("text", "")) for item in content if isinstance(item, dict)
                ).strip()
            else:
                answer = str(content or "").strip()
        except Exception as exc:
            logger.exception("[agent] llm invoke failed session_id=%s", session_id)
            return format_llm_user_message(exc)

        if not answer:
            return "模型未返回内容，请检查 DP_MODEL 是否为 deepseek-chat 且 API 额度正常"

        record_from_response(
            phase="chat",
            model=self.model,
            messages=messages,
            response=resp,
            completion_text=answer,
            channel=channel,
            trace_id=trace_id or None,
        )

        self.history.save_turn(
            session_id=session_id,
            user_id=user_id,
            user_question=question,
            assistant_answer=answer,
            channel=(channel or "qq").strip().lower() or "qq",
        )
        log_event(
            "chat.done",
            model=self.model,
            session_id=session_id,
            user_id=user_id,
            **answer_log_fields(answer),
            **request_token_summary_fields(trace_id or None),
        )
        return answer

    def invoke_messages_once(self, messages: list[Any]) -> str:
        """按给定消息列表单次调用模型（不写历史，由调用方负责）。"""
        try:
            resp = self.chat_llm.invoke(messages)
            content = resp.content
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                return "".join(
                    str(item.get("text", "")) for item in content if isinstance(item, dict)
                ).strip()
            return str(content or "").strip()
        except Exception as exc:
            logger.exception("[agent] invoke_messages_once failed")
            raise RuntimeError(f"模型调用失败：{exc}") from exc

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

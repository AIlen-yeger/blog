"""将 LLM / OpenAI 兼容 API 异常转为用户可读说明。"""

from __future__ import annotations


def format_llm_user_message(exc: BaseException) -> str:
    raw = str(exc) or repr(exc)
    lower = raw.lower()

    if "402" in raw or "insufficient balance" in lower or "余额" in raw:
        return (
            "模型 API 返回 402（余额不足）：请登录 DeepSeek（或当前 base_url 对应平台）"
            "充值或更换有效密钥，并确认 python/.env 中 DP_AGENT_API_KEY / DP_CHAT_API_KEY 指向该账户。"
        )
    if "401" in raw or "invalid api key" in lower or "authentication" in lower:
        return (
            "模型 API 返回 401（密钥无效）：请检查 python/.env 的 DP_AGENT_API_KEY / DP_CHAT_API_KEY "
            "与 DP_CHAT_API_URL 是否与平台一致。"
        )
    if "429" in raw or "rate limit" in lower:
        return "模型 API 限流（429）：请稍后再试或降低并发。"
    if "connection" in lower or "timeout" in lower or "timed out" in lower:
        return f"无法连接模型服务：{raw}。请检查网络、代理与 DP_CHAT_API_URL。"

    return f"模型调用失败：{raw}。请检查 DP_AGENT_API_KEY、DP_MODEL 与网络。"

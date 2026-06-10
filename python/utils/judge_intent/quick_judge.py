import re


_SMALL_TALK_RE = re.compile(
    r"^(嗯|哦|好|好的|在吗|嗨|hello|hi|哈哈|hhh|…|\.\.\.)$",
    re.I,
)
_MEMORY_SIGNALS = ("我", "喜欢", "讨厌", "昨天", "记得", "加歌", "btc", "行情", "笔记")


def should_skip_memory_pipeline(message: str) -> bool:
    text = (message or "").strip()
    if not text:
        return True
    if len(text) <= 4 and not any(s in text for s in _MEMORY_SIGNALS):
        return True
    if _SMALL_TALK_RE.match(text):
        return True
    return False


def should_skip_recall(message: str, *, intent: str) -> bool:
    #非闲聊跳过
    if intent != "chat":
        return True
    #命中寒暄等无意义消息跳过
    if should_skip_memory_pipeline(message):
        return True
    return False
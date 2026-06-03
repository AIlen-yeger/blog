"""QQ 对用户可见文案的后处理（与 aicoin skill 里的语气规则配合）。"""

from __future__ import annotations

import re

from utils.world_lexicon import apply_world_lexicon

QQ_MARKET_REPLY_MAX_CHARS = 120
QQ_DCA_DAILY_MAX_CHARS = 120
QQ_DCA_COMMAND_MAX_CHARS = 400


def strip_qq_markdown(text: str) -> str:
    if not text:
        return text
    out = text.strip()
    out = re.sub(r"```[\s\S]*?```", "", out)
    out = re.sub(r"`([^`]+)`", r"\1", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"\1", out)
    out = re.sub(r"\*([^*]+)\*", r"\1", out)
    out = re.sub(r"^#{1,6}\s*", "", out, flags=re.M)
    out = re.sub(r"^\s*[-*+]\s+", "", out, flags=re.M)
    out = re.sub(r"^\s*\d+\.\s+", "", out, flags=re.M)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def clamp_qq_length(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    cut = text[:max_chars].rstrip()
    if cut and text[max_chars : max_chars + 1] not in ("", "\n"):
        cut = cut.rstrip("，。！？、；：,.!?;:")
    return cut + "…"


def finalize_qq_reply(text: str, *, max_chars: int = QQ_MARKET_REPLY_MAX_CHARS) -> str:
    cleaned = strip_qq_markdown((text or "").strip())
    if not cleaned:
        return cleaned
    return clamp_qq_length(apply_world_lexicon(cleaned), max_chars)

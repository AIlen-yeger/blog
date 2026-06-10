"""对用户可见文案：BTC/比特币 → 纠缠之缘，USDT/U → 原石（内部计算仍用 USDT/BTC）。"""

from __future__ import annotations

import re

COIN_BTC_DISPLAY = "纠缠之缘"
CURRENCY_USDT_DISPLAY = "原石"

# 注入 system skills 的共用说明（各 AiCoin 段落前会带 preamble）
WORLD_LEXICON_PROMPT = (
    f"对用户：BTC/比特币→{COIN_BTC_DISPLAY}，USDT/U→{CURRENCY_USDT_DISPLAY}；"
    f"工具/JSON 仍用 BTC/USDT。禁对用户写 BTC/USDT（除非用户问技术名）。ETH 不改。"
)

# 识别用户是否在说纠缠之缘 / 原石
BTC_USER_ALIASES = ("btc", "比特币", COIN_BTC_DISPLAY)
USDT_USER_ALIASES = ("usdt", "u", "刀", CURRENCY_USDT_DISPLAY)


def apply_world_lexicon(text: str) -> str:
    """后处理：把模型或模板里漏掉的 BTC/USDT 用语换成世界观名称。"""
    if not text:
        return text
    out = text
    out = re.sub(r"比特币", COIN_BTC_DISPLAY, out, flags=re.I)
    out = re.sub(r"\bUSDT\b", CURRENCY_USDT_DISPLAY, out, flags=re.I)
    out = re.sub(r"U/BTC", f"{CURRENCY_USDT_DISPLAY}/{COIN_BTC_DISPLAY}", out, flags=re.I)
    out = re.sub(r"枚\s*BTC\b", f"枚{COIN_BTC_DISPLAY}", out, flags=re.I)
    out = re.sub(r"\bBTC\b", COIN_BTC_DISPLAY, out)
    out = re.sub(r"\bbtc\b", COIN_BTC_DISPLAY, out)
    out = re.sub(
        r"(\d[\d,]*(?:\.\d+)?)\s*U(?=/|，|。|！|？|\s|$|/|，)",
        rf"\1 {CURRENCY_USDT_DISPLAY}",
        out,
    )
    out = re.sub(
        r"(\d[\d,]*(?:\.\d+)?)\s*U\b",
        rf"\1 {CURRENCY_USDT_DISPLAY}",
        out,
    )
    return out

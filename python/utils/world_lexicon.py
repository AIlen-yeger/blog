"""对用户可见文案：BTC/比特币 → 纠缠之缘，USDT/U → 原石（内部计算仍用 USDT/BTC）。"""

from __future__ import annotations

import re

COIN_BTC_DISPLAY = "纠缠之缘"
CURRENCY_USDT_DISPLAY = "原石"

# 注入 system prompt 的共用说明（各 AiCoin 段落前会带 preamble）
WORLD_LEXICON_PROMPT = f"""## 世界观用词（对用户输出，硬约束）

- **{COIN_BTC_DISPLAY}**：对外代替 BTC、比特币、btc；工具参数仍用 BTC，JSON 字段名不变。
- **{CURRENCY_USDT_DISPLAY}**：对外代替 USDT、稳定币计价单位；口语里的「U」「多少 u」也写成 {CURRENCY_USDT_DISPLAY}。
- 美元现价可继续用 $ 或「美元」；**禁止**在对用户回复里再写 BTC、比特币、USDT（除非用户明确在问技术名词）。
- ETH 等其他币种名称不改。"""

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

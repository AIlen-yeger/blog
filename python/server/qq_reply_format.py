"""QQ 渠道 AiCoin：问题分类 + system 追加说明（不硬改 LLM 原文）。"""

from __future__ import annotations

_SINGLE_COIN_HINTS = (
    "btc",
    "eth",
    "bnb",
    "sol",
    "doge",
    "xrp",
    "ada",
    "比特币",
    "以太坊",
    "狗狗币",
    "瑞波",
)

_BROAD_MARKET_HINTS = (
    "大盘",
    "热门",
    "主流",
    "行情汇总",
    "市场概况",
    "今天币圈",
    "整体",
    "全市场",
    "哪些币",
    "涨幅榜",
    "跌幅榜",
)

_TREND_HINTS = ("走势", "k线", "趋势", "定投", "适合买", "回调", "抄底", "ahr999")


def is_ahr999_question(question: str) -> bool:
    q = (question or "").strip().lower()
    return "ahr999" in q or "ahr 999" in q


def is_broad_market_question(question: str) -> bool:
    q = (question or "").strip().lower()
    return any(h in q for h in _BROAD_MARKET_HINTS)


def is_single_coin_trend_question(question: str) -> bool:
    q = (question or "").strip().lower()
    if not any(h in q for h in _SINGLE_COIN_HINTS):
        return False
    return any(h in q for h in _TREND_HINTS)


def is_single_coin_price_question(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q or is_broad_market_question(q):
        return False
    if not any(h in q for h in _SINGLE_COIN_HINTS):
        return False
    price_hints = ("多少钱", "价格", "价位", "多少刀", "多少u", "现价", "行情", "涨", "跌")
    return any(h in q for h in price_hints) or is_single_coin_trend_question(q)


def qq_aicoin_max_rounds(question: str) -> int:
    """QQ 渠道 ReAct 工具轮次上限（少查、快答）。"""
    if is_ahr999_question(question):
        return 3
    if is_single_coin_price_question(question) and not is_single_coin_trend_question(question):
        return 2
    if is_broad_market_question(question):
        return 3
    return 2


def build_qq_aicoin_system_append(question: str) -> str:
    """追加到 system 末尾；靠提示词约束风格，不做后处理硬改。"""
    lines = [
        "## QQ 行情回复（本轮）",
        "- 遵守上方 channel_qq 与 aicoin_qq：用 Kohaku 口语在 QQ 里回，自然即可，不要研报/客服腔。",
        "- **够用就好**：工具查到现价与关键涨跌后立刻组织回复，不要为「写全」再开第二轮工具。",
        "- 1～3 句、约 160 字内；直接写出价格数字与 24h 涨跌；禁止 Markdown 表格/标题/长列表。",
        "- 不要「价格如下」「小结」等空壳开头；不要罗列用户没问的多个币。",
        "- 数据以工具为准；末尾可轻带一句非投资建议。",
    ]
    if is_single_coin_price_question(question) and not is_single_coin_trend_question(question):
        lines.extend(
            [
                "- 用户只问某币现价：**调用 coin_info 一次即可**，拿到 ticker 后直接回复，不要 kline/news/flash/market_info。",
            ]
        )
    elif is_single_coin_trend_question(question):
        lines.append(
            "- 用户问走势/定投：最多 coin_info + kline(1d)，不要拉新闻快讯全市场。"
        )
    elif is_broad_market_question(question):
        lines.append("- 用户问大盘/热门：可用 market_info 一次，口头提 2～3 个代表币，仍无表格。")
    else:
        lines.append("- 默认：优先 coin_info；非必要不查 news/flash/index。")
    return "\n".join(lines)

"""QQ 渠道 AiCoin：问题分类、system 追加、回复后处理。"""

from __future__ import annotations

from server.qq.message_format import QQ_MARKET_REPLY_MAX_CHARS, finalize_qq_reply

_SINGLE_COIN_HINTS = (
    "btc",
    "eth",
    "bnb",
    "sol",
    "doge",
    "xrp",
    "ada",
    "比特币",
    "纠缠之缘",
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
    if is_ahr999_question(question):
        return 3
    if is_single_coin_price_question(question) and not is_single_coin_trend_question(question):
        return 2
    if is_broad_market_question(question):
        return 3
    return 2


def build_qq_aicoin_system_append(question: str) -> str:
    _ = question
    return "\n".join(
        [
            "## QQ 行情回复（单阶段 ReAct）",
            f"- 遵守 aicoin 的 QQ 语气段：Kohaku 口语，1～3 句、约 {QQ_MARKET_REPLY_MAX_CHARS} 字内。",
            "- 工具已由系统按问题收窄；查到现价与关键涨跌后尽快回复，勿为写全再开无关工具。",
            "- 直接写价格与 24h 涨跌；禁止 Markdown 表格/标题/长列表；勿罗列用户没问的币。",
            "- 数据以工具为准；对用户用纠缠之缘、原石；末尾可轻带非投资建议。",
        ]
    )


def format_qq_market_reply(text: str) -> str:
    return finalize_qq_reply(text, max_chars=QQ_MARKET_REPLY_MAX_CHARS)

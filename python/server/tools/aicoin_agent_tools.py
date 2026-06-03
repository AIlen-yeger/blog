"""AiCoin Agent 的 LangChain 工具（只读行情/资讯，供 aicoin ReAct 子图使用）。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.tools import tool

from utils.mcp import get_mcp_client, is_mcp_enabled
from utils.trace_log import log_event, preview

logger = logging.getLogger(__name__)

AICOIN_MCP_NAME = "aicoin"
_DISABLED_MESSAGE = "暂未开启行情查询功能，请如实告知用户当前不支持实时数据查询。"

_KLINE_PERIOD = {
    "15m": "900",
    "1h": "3600",
    "4h": "14400",
    "1d": "86400",
    "1w": "604800",
}


def build_aicoin_tools(
    *,
    include_optional: bool = False,
    channel: str = "web",
    question: str = "",
) -> list:
    """供路由绑定；QQ 渠道按问题收窄工具集，减少无效调用。"""
    ch = (channel or "web").strip().lower()
    if ch == "qq":
        return AicoinAgentTools(include_optional=include_optional).build_tools_for_qq(
            question
        )
    return AicoinAgentTools(include_optional=include_optional).build_tools()


class AicoinAgentTools:
    """封装 AiCoin MCP 只读工具；绑定前须确认 MCP 已启用。"""

    def __init__(self, *, include_optional: bool = False) -> None:
        self.enabled = is_mcp_enabled(AICOIN_MCP_NAME)
        self._include_optional = include_optional

    def build_tools(self) -> list:
        if not self.enabled:
            log_event("aicoin.tools.skip", level=logging.INFO, reason="mcp_disabled")
            return []
        tools: list = [
            self._make_coin_info_tool(),
            self._make_kline_tool(),
            self._make_news_tool(),
            self._make_flash_tool(),
            self._make_market_info_tool(),
            self._make_index_data_tool(),
        ]
        if self._include_optional:
            tools.extend(
                [
                    self._make_market_overview_tool(),
                    self._make_coin_funding_rate_tool(),
                    self._make_coin_treasury_tool(),
                    self._make_crypto_stock_tool(),
                ]
            )
        return tools

    def build_tools_for_qq(self, question: str) -> list:
        """QQ：只暴露当前问题需要的少量工具。"""
        if not self.enabled:
            log_event("aicoin.tools.skip", level=logging.INFO, reason="mcp_disabled")
            return []

        from server.qq_reply_format import (
            is_ahr999_question,
            is_broad_market_question,
            is_single_coin_price_question,
            is_single_coin_trend_question,
        )

        q = (question or "").strip()
        if is_broad_market_question(q):
            names = ("coin_info", "market_info")
        elif is_ahr999_question(q) or is_single_coin_trend_question(q):
            names = ("coin_info", "kline")
        elif is_single_coin_price_question(q):
            names = ("coin_info",)
        else:
            names = ("coin_info", "kline")

        makers = {
            "coin_info": self._make_coin_info_tool,
            "kline": self._make_kline_tool,
            "market_info": self._make_market_info_tool,
        }
        tools = [makers[n]() for n in names if n in makers]
        log_event(
            "aicoin.tools.qq_subset",
            tools=list(names),
            question_preview=preview(q, 80),
        )
        return tools

    def _call_mcp(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if not self.enabled:
            return json.dumps({"message": _DISABLED_MESSAGE}, ensure_ascii=False)

        client = get_mcp_client(AICOIN_MCP_NAME)
        result = client.call_tool_sync(arguments, tool_name=tool_name)
        if not result.ok:
            log_event(
                "aicoin.mcp.error",
                level=logging.WARNING,
                tool=tool_name,
                error=preview(result.error or "", 300),
            )
            return json.dumps(
                {
                    "message": "AiCoin 查询失败",
                    "tool": tool_name,
                    "error": (result.error or "")[:500],
                },
                ensure_ascii=False,
            )

        text = (result.text or "").strip()
        if not text:
            return json.dumps(
                {"message": "AiCoin 未返回数据", "tool": tool_name},
                ensure_ascii=False,
            )
        if len(text) > 14_000:
            return text[:14_000] + "\n…(已截断)"
        return text

    def _resolve_coin_list(self, symbol: str) -> str:
        """用 search 将 BTC/比特币 等解析为 coin_list（逗号分隔 coinKey）。"""
        sym = (symbol or "").strip()
        if not sym:
            return ""
        if "," in sym and ":" not in sym:
            return sym

        raw = self._call_mcp(
            "coin_info",
            {"action": "search", "search": sym, "page_size": 5},
        )
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return sym.lower()

        keys: list[str] = []

        def _collect(obj: Any) -> None:
            if isinstance(obj, dict):
                for k in ("coinKey", "coin_key", "key", "dbKey", "dbkey"):
                    v = obj.get(k)
                    if isinstance(v, str) and v.strip():
                        keys.append(v.strip())
                for v in obj.values():
                    _collect(v)
            elif isinstance(obj, list):
                for item in obj:
                    _collect(item)

        _collect(data)
        deduped: list[str] = []
        seen: set[str] = set()
        for k in keys:
            if k not in seen:
                seen.add(k)
                deduped.append(k)
        if deduped:
            return ",".join(deduped[:5])
        return sym.lower()

    def _normalize_kline_symbol(self, symbol: str) -> str:
        s = (symbol or "").strip()
        if not s:
            return ""
        if ":" in s:
            return s
        base = re.sub(r"[^a-zA-Z0-9]", "", s).lower() or "btc"
        return f"{base}usdt:binance"

    def _make_coin_info_tool(self):
        outer = self

        @tool
        def coin_info(
            symbol: str,
            detail: str = "ticker",
        ) -> str:
            """查询币种现价、简介或基础面（只读，不下单）。
            symbol: 如 BTC、ETH、bitcoin；detail: ticker(默认现价) | config(简介) | search(仅搜索)。
            定投前问「现在什么价」时用 ticker；需要项目背景用 config。"""
            sym = (symbol or "").strip()
            if not sym:
                return json.dumps({"message": "symbol 不能为空"}, ensure_ascii=False)

            detail = (detail or "ticker").strip().lower()
            if detail == "search":
                return outer._call_mcp(
                    "coin_info",
                    {"action": "search", "search": sym, "page_size": 10},
                )
            if detail not in ("ticker", "config"):
                return json.dumps(
                    {"message": "detail 仅支持 ticker | config | search"},
                    ensure_ascii=False,
                )

            coin_list = outer._resolve_coin_list(sym)
            if not coin_list:
                return json.dumps(
                    {"message": f"未找到币种：{sym}"},
                    ensure_ascii=False,
                )
            return outer._call_mcp(
                "coin_info",
                {"action": detail, "coin_list": coin_list},
            )

        return coin_info

    def _make_kline_tool(self):
        outer = self

        @tool
        def kline(
            symbol: str,
            period: str = "1d",
            size: int = 90,
        ) -> str:
            """K 线趋势（只读）。定投看长周期：请用 period=1d 或 1w，勿用 1m/15m。
            symbol: 交易对，如 btcusdt:binance；也可只写 BTC（会映射为现货对）。
            period: 15m | 1h | 4h | 1d(默认) | 1w。size: K 线根数，默认 90。"""
            sym = outer._normalize_kline_symbol(symbol)
            if not sym:
                return json.dumps({"message": "symbol 不能为空"}, ensure_ascii=False)

            period_key = (period or "1d").strip().lower()
            period_sec = _KLINE_PERIOD.get(period_key, period_key)
            n = max(1, min(int(size or 90), 500))
            return outer._call_mcp(
                "kline",
                {
                    "action": "data",
                    "symbol": sym,
                    "period": str(period_sec),
                    "size": str(n),
                },
            )

        return kline

    def _make_news_tool(self):
        outer = self

        @tool
        def news(
            page: int = 1,
            page_size: int = 15,
        ) -> str:
            """分页获取加密货币资讯文章列表（只读）。用户问行业新闻、深度文章时使用。"""
            return outer._call_mcp(
                "news",
                {
                    "action": "list",
                    "page": str(max(1, page)),
                    "pageSize": str(max(1, min(page_size, 20))),
                },
            )

        return news

    def _make_flash_tool(self):
        outer = self

        @tool
        def flash(
            kind: str = "newsflash",
            language: str = "cn",
        ) -> str:
            """快讯：newsflash(AiCoin 快讯，默认) | list(行业快讯) | exchange_listing(上所/下架公告)。
            用户问突发、短线新闻、上所公告时使用。"""
            action = (kind or "newsflash").strip().lower()
            if action not in ("newsflash", "list", "exchange_listing"):
                return json.dumps(
                    {"message": "kind 仅支持 newsflash | list | exchange_listing"},
                    ensure_ascii=False,
                )
            args: dict[str, Any] = {"action": action}
            lang = (language or "cn").strip()
            if lang:
                args["language"] = lang
            return outer._call_mcp("flash", args)

        return flash

    def _make_market_info_tool(self):
        outer = self

        @tool
        def market_info(
            scope: str = "hot_coins",
            category: str = "market",
        ) -> str:
            """大盘与热门币（只读）。scope: hot_coins(默认热门) | exchanges(交易所列表) | futures_interest(合约持仓排行)。
            category 用于 hot_coins：market/defi/web/gamefi 等。"""
            scope = (scope or "hot_coins").strip().lower()
            if scope == "exchanges":
                return outer._call_mcp("market_info", {"action": "exchanges"})
            if scope == "futures_interest":
                return outer._call_mcp(
                    "market_info",
                    {"action": "futures_interest", "lan": "cn"},
                )
            if scope == "hot_coins":
                return outer._call_mcp(
                    "market_info",
                    {
                        "action": "hot_coins",
                        "key": (category or "market").strip(),
                        "currency": "usd",
                    },
                )
            return json.dumps(
                {"message": "scope 仅支持 hot_coins | exchanges | futures_interest"},
                ensure_ascii=False,
            )

        return market_info

    def _make_index_data_tool(self):
        outer = self

        @tool
        def index_data(
            index_key: str = "",
            action: str = "list",
        ) -> str:
            """指数/宏观指标（只读）。action=list 列出可用指数；action=price|info 需 index_key（如 i:fgi:alternative）。
            用户问恐惧贪婪、指数行情时使用；不知道 key 时先 list。"""
            act = (action or "list").strip().lower()
            if act == "list":
                return outer._call_mcp("index_data", {"action": "list"})
            key = (index_key or "").strip()
            if not key:
                return json.dumps(
                    {"message": "price/info 需要提供 index_key，可先 action=list 查看"},
                    ensure_ascii=False,
                )
            if act == "price":
                return outer._call_mcp(
                    "index_data",
                    {"action": "price", "key": key, "currency": "usd"},
                )
            if act == "info":
                return outer._call_mcp(
                    "index_data",
                    {"action": "info", "key": key, "lan": "cn"},
                )
            return json.dumps(
                {"message": "action 仅支持 list | price | info"},
                ensure_ascii=False,
            )

        return index_data

    def _make_market_overview_tool(self):
        outer = self

        @tool
        def market_overview(
            metric: str = "nav",
        ) -> str:
            """市场整体情绪（可选工具）：nav(大盘资金) | long_short(多空比) | liquidation | grayscale | stocks。
            偶尔判断「市场热不热」时使用，非每笔定投必查。"""
            m = (metric or "nav").strip().lower()
            return outer._call_mcp("market_overview", {"action": m})

        return market_overview

    def _make_coin_funding_rate_tool(self):
        outer = self

        @tool
        def coin_funding_rate(
            symbol: str = "btcswapusdt",
            interval: str = "8h",
        ) -> str:
            """资金费率历史（可选，只读情绪参考，非开仓）。symbol 如 btcswapusdt，interval 建议 8h。
            用于判断合约市场是否过热，不代表现货定投建议。"""
            sym = (symbol or "btcswapusdt").strip()
            return outer._call_mcp(
                "coin_funding_rate",
                {
                    "symbol": sym,
                    "interval": (interval or "8h").strip(),
                    "weighted": True,
                },
            )

        return coin_funding_rate

    def _make_coin_treasury_tool(self):
        outer = self

        @tool
        def coin_treasury(
            coin: str = "BTC",
            action: str = "summary",
        ) -> str:
            """上市公司/机构持仓（可选）。coin: BTC/ETH；action: summary(默认) | entities | latest_entities。"""
            c = (coin or "BTC").strip().upper()
            act = (action or "summary").strip().lower()
            if act not in ("summary", "entities", "latest_entities"):
                return json.dumps(
                    {"message": "action 仅支持 summary | entities | latest_entities"},
                    ensure_ascii=False,
                )
            return outer._call_mcp("coin_treasury", {"action": act, "coin": c})

        return coin_treasury

    def _make_crypto_stock_tool(self):
        outer = self

        @tool
        def crypto_stock(
            action: str = "top_gainer",
            tickers: str = "",
        ) -> str:
            """美股加密概念股（可选）。action: top_gainer(涨幅榜) | quotes(行情，需 tickers 如 i:mstr:nasdaq)。"""
            act = (action or "top_gainer").strip().lower()
            if act == "top_gainer":
                return outer._call_mcp(
                    "crypto_stock",
                    {"action": "top_gainer", "us_stock": True, "limit": 20},
                )
            if act == "quotes":
                t = (tickers or "").strip()
                if not t:
                    return json.dumps(
                        {"message": "quotes 需要 tickers，如 i:mstr:nasdaq,i:coin:nasdaq"},
                        ensure_ascii=False,
                    )
                return outer._call_mcp(
                    "crypto_stock",
                    {"action": "quotes", "tickers": t},
                )
            return json.dumps(
                {"message": "action 仅支持 top_gainer | quotes"},
                ensure_ascii=False,
            )

        return crypto_stock

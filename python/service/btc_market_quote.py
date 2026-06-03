"""拉取 BTC 现价（AiCoin MCP）。"""

from __future__ import annotations

import json
import logging
from typing import Any

from utils.ahr999 import pick_cny_price, pick_usd_price

logger = logging.getLogger(__name__)


def fetch_btc_ticker() -> dict[str, Any]:
    """返回 spot_usd, spot_cny, change_24h_pct 等；失败则空字段。"""
    out: dict[str, Any] = {
        "symbol": "BTC",
        "spot_usd": None,
        "spot_cny": None,
        "change_24h_pct": None,
        "change_7d_pct": None,
        "ok": False,
    }
    try:
        from server.tools.aicoin_agent_tools import AicoinAgentTools

        tools = AicoinAgentTools()
        if not tools.enabled:
            return out
        raw = tools._call_mcp(
            "coin_info",
            {"action": "ticker", "coin_list": "bitcoin"},
        )
        if not raw or not raw.strip().startswith("{"):
            return out
        data = json.loads(raw)
        out["ok"] = bool(data.get("success", True))
        usd = pick_usd_price({}, [raw])
        cny = pick_cny_price({}, [raw])
        out["spot_usd"] = usd
        out["spot_cny"] = cny
        rows = data.get("data")
        if isinstance(rows, list) and rows:
            row = rows[0]
            if isinstance(row, dict):
                for key, target in (
                    ("degree_24h_usd", "change_24h_pct"),
                    ("degree_7day_usd", "change_7d_pct"),
                ):
                    try:
                        v = float(row.get(key))
                        out[target] = v
                    except (TypeError, ValueError):
                        pass
        out["ok"] = usd is not None and usd > 0
    except Exception:
        logger.exception("[btc_quote] fetch failed")
    return out

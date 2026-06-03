"""每日 BTC 定投简报：事实块 + QQ 口语润色 + NapCat 推送。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from config.config import AgentConfig
from server.agent import ChatModel
from server.prompt_skills import build_system_prompt, read_aicoin_skill
from server.qq.message_format import QQ_DCA_DAILY_MAX_CHARS, finalize_qq_reply
from utils.world_lexicon import COIN_BTC_DISPLAY, CURRENCY_USDT_DISPLAY
from service.btc_dca_position import load_position, position_pnl_usdt
from service.btc_market_quote import fetch_btc_ticker
from utils.ahr999 import enrich_facts_with_ahr999
from utils.qq.napcat_notify import napcat_configured, send_private_message
from utils.trace_log import log_event, preview, span

logger = logging.getLogger(__name__)


def build_daily_facts() -> dict[str, Any]:
    quote = fetch_btc_ticker()
    pos = load_position()
    spot = float(quote.get("spot_usd") or 0)
    pnl = position_pnl_usdt(pos=pos, spot_usd=spot) if spot > 0 and pos.btc_quantity > 0 else {}

    facts: dict[str, Any] = {
        "date": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d"),
        "symbol": "BTC",
        "spot_usd": quote.get("spot_usd"),
        "spot_cny": quote.get("spot_cny"),
        "change_24h_pct": quote.get("change_24h_pct"),
        "change_7d_pct": quote.get("change_7d_pct"),
        "quote_ok": quote.get("ok"),
        "btc_quantity": round(pos.btc_quantity, 8) if pos.btc_quantity else None,
        "avg_cost_usdt": round(pos.avg_cost_usdt, 2) if pos.avg_cost_usdt else None,
        "total_cost_usdt": round(pos.total_cost_usdt, 2) if pos.total_cost_usdt else None,
        **pnl,
    }
    if spot > 0:
        facts = enrich_facts_with_ahr999(
            facts,
            [],
            "btc定投日报",
            fetch_if_missing=True,
        )
    return facts


def _fallback_qq_text(facts: dict[str, Any]) -> str:
    spot = facts.get("spot_usd")
    avg = facts.get("avg_cost_usdt")
    pnl_u = facts.get("pnl_usdt")
    pnl_p = facts.get("pnl_pct")
    cost = facts.get("total_cost_usdt")
    if not spot or not avg:
        return f"早安～今天 {COIN_BTC_DISPLAY} 报价没拉到，稍后再试一次呀。"
    trend = ""
    if pnl_u is not None:
        if pnl_u >= 0:
            trend = f"按成本算浮盈约 {pnl_u:+.2f} {CURRENCY_USDT_DISPLAY}（{pnl_p:+.2f}%）"
        else:
            trend = f"按成本算浮亏约 {pnl_u:.2f} {CURRENCY_USDT_DISPLAY}（{pnl_p:.2f}%）"
    line = (
        f"早安呀～{COIN_BTC_DISPLAY} 现在约 ${spot:,.0f}，你的均价 ${avg:,.0f}，"
        f"累计投入 {cost:.2f} {CURRENCY_USDT_DISPLAY}，{trend}。"
    )
    if facts.get("ahr999_ok") and facts.get("ahr999") is not None:
        line += f" AHR999 约 {facts['ahr999']}（{facts.get('ahr999_zone_cn', '')}）。"
    return finalize_qq_reply(line, max_chars=QQ_DCA_DAILY_MAX_CHARS)


def polish_daily_qq_message(facts: dict[str, Any]) -> str:
    if not facts.get("quote_ok"):
        return _fallback_qq_text(facts)

    try:
        model = ChatModel()
        system = build_system_prompt(intent="chat", channel="qq", developer_name="开发者")
        extra = read_aicoin_skill("dca_daily")
        system = "\n\n---\n\n".join(p for p in (system, extra) if p)

        human = (
            f"请根据以下只读数据，写一条 QQ 早安定投简报（1～3 句、约 {QQ_DCA_DAILY_MAX_CHARS} 字内）。"
            "必须包含：现价(美元)、你的均价(美元)、相对成本的浮盈/浮亏(原石与%)。"
            "对用户称纠缠之缘、原石；数字不得改；无 Markdown。\n\n"
            f"[定投日报-只读]\n{json.dumps(facts, ensure_ascii=False)}"
        )
        with span("btc.dca.polish"):
            text = model.invoke_messages_once(
                [SystemMessage(content=system), HumanMessage(content=human)]
            )
        text = (text or "").strip()
        if text:
            return finalize_qq_reply(text, max_chars=QQ_DCA_DAILY_MAX_CHARS)
    except Exception:
        logger.exception("[btc_dca] polish failed")
    return _fallback_qq_text(facts)


def send_daily_brief_to_developer(
    *,
    force: bool = False,
    push: bool = True,
) -> dict[str, Any]:
    """生成并可选推送定投日报。

    push=True：经 NapCat 主动私聊（定时任务、HTTP ops 测试）。
    push=False：仅生成文案，由 QQ poller 作为回复发出（避免重复推送）。
    """
    cfg = AgentConfig()
    if not cfg.btc_dca_daily_enabled and not force:
        return {"ok": False, "status": "disabled"}

    if push and not napcat_configured():
        return {"ok": False, "status": "napcat_not_configured"}

    facts = build_daily_facts()
    message = polish_daily_qq_message(facts)
    if not message:
        return {"ok": False, "status": "empty_message", "facts": facts}

    push_result: dict[str, Any] = {"ok": True, "status": "return_only"}
    if push:
        push_result = send_private_message(message)

    log_event(
        "btc.dca.daily_sent",
        ok=push_result.get("ok"),
        push=push,
        spot_usd=facts.get("spot_usd"),
        pnl_usdt=facts.get("pnl_usdt"),
        preview=preview(message, 200),
    )
    return {
        "ok": bool(push_result.get("ok")),
        "message": message,
        "facts": facts,
        **push_result,
    }

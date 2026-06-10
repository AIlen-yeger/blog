"""BTC 定投持仓：成本、数量、均价（JSON 持久化）。"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.config import AgentConfig
from server.qq.message_format import QQ_DCA_COMMAND_MAX_CHARS, finalize_qq_reply
from utils.world_lexicon import BTC_USER_ALIASES, COIN_BTC_DISPLAY, CURRENCY_USDT_DISPLAY
from utils.log.agent_log_config import state_dir

logger = logging.getLogger(__name__)

_STATE_NAME = "btc_dca_position.json"


@dataclass
class BtcDcaPosition:
    """持仓以 BTC 数量 + 均价为主；total_cost_usdt = btc_quantity * avg_cost_usdt。"""

    btc_quantity: float = 0.0
    avg_cost_usdt: float = 0.0
    total_cost_usdt: float = 0.0
    updated_at: str = ""

    def sync_totals(self) -> None:
        if self.btc_quantity > 0 and self.avg_cost_usdt > 0:
            self.total_cost_usdt = round(self.btc_quantity * self.avg_cost_usdt, 4)
        elif self.total_cost_usdt > 0 and self.avg_cost_usdt > 0:
            self.btc_quantity = self.total_cost_usdt / self.avg_cost_usdt

    def apply_dca(self, *, spend_usdt: float, price_usdt: float) -> "BtcDcaPosition":
        if spend_usdt <= 0 or price_usdt <= 0:
            raise ValueError("定投金额与价格须大于 0")
        add_btc = spend_usdt / price_usdt
        old_cost = self.btc_quantity * self.avg_cost_usdt if self.btc_quantity > 0 else 0.0
        new_qty = self.btc_quantity + add_btc
        new_cost = old_cost + spend_usdt
        self.btc_quantity = new_qty
        self.avg_cost_usdt = new_cost / new_qty if new_qty > 0 else price_usdt
        self.total_cost_usdt = round(new_cost, 4)
        self.updated_at = _now_iso()
        return self

    def set_from_cost_and_avg(self, *, total_cost_usdt: float, avg_cost_usdt: float) -> None:
        if total_cost_usdt <= 0 or avg_cost_usdt <= 0:
            raise ValueError("成本与均价须大于 0")
        self.total_cost_usdt = round(total_cost_usdt, 4)
        self.avg_cost_usdt = float(avg_cost_usdt)
        self.btc_quantity = self.total_cost_usdt / self.avg_cost_usdt
        self.updated_at = _now_iso()

    def set_from_qty_and_avg(self, *, btc_quantity: float, avg_cost_usdt: float) -> None:
        if btc_quantity <= 0 or avg_cost_usdt <= 0:
            raise ValueError("持仓数量与均价须大于 0")
        self.btc_quantity = float(btc_quantity)
        self.avg_cost_usdt = float(avg_cost_usdt)
        self.total_cost_usdt = round(self.btc_quantity * self.avg_cost_usdt, 2)
        self.updated_at = _now_iso()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _state_path() -> Path:
    return state_dir() / _STATE_NAME


def _default_from_env() -> BtcDcaPosition | None:
    cfg = AgentConfig()
    avg = float(getattr(cfg, "btc_dca_initial_avg_usdt", 0) or 0)
    qty = float(getattr(cfg, "btc_dca_initial_btc_qty", 0) or 0)
    cost = float(getattr(cfg, "btc_dca_initial_cost_usdt", 0) or 0)
    if avg <= 0:
        return None
    pos = BtcDcaPosition()
    if qty > 0:
        pos.btc_quantity = qty
        pos.avg_cost_usdt = avg
        pos.total_cost_usdt = round(qty * avg, 2)
        pos.updated_at = _now_iso()
        return pos
    if cost > 0:
        pos.set_from_cost_and_avg(total_cost_usdt=cost, avg_cost_usdt=avg)
        return pos
    return None


def load_position() -> BtcDcaPosition:
    path = _state_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                pos = BtcDcaPosition(
                    btc_quantity=float(data.get("btc_quantity") or 0),
                    avg_cost_usdt=float(data.get("avg_cost_usdt") or 0),
                    total_cost_usdt=float(data.get("total_cost_usdt") or 0),
                    updated_at=str(data.get("updated_at") or ""),
                )
                pos.sync_totals()
                return pos
        except Exception:
            logger.exception("[btc_dca] corrupt state, reset from env")

    pos = _default_from_env()
    if pos is None:
        return BtcDcaPosition()
    save_position(pos)
    return pos


def save_position(pos: BtcDcaPosition, *, history_entry: dict[str, Any] | None = None) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    pos.sync_totals()
    payload: dict[str, Any] = {
        "version": 1,
        **asdict(pos),
        "history": [],
    }
    if path.is_file():
        try:
            old = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(old, dict) and isinstance(old.get("history"), list):
                payload["history"] = old["history"][-49:]
        except Exception:
            pass
    if history_entry:
        payload["history"] = (payload.get("history") or []) + [history_entry]
        payload["history"] = payload["history"][-50:]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def position_pnl_usdt(*, pos: BtcDcaPosition, spot_usd: float) -> dict[str, float]:
    pos.sync_totals()
    cost = pos.total_cost_usdt or (pos.btc_quantity * pos.avg_cost_usdt)
    value = pos.btc_quantity * spot_usd if spot_usd > 0 else 0.0
    pnl = value - cost
    pct = (pnl / cost * 100.0) if cost > 0 else 0.0
    return {
        "cost_usdt": round(cost, 2),
        "value_usdt": round(value, 2),
        "pnl_usdt": round(pnl, 2),
        "pnl_pct": round(pct, 2),
    }


def _finalize_dca_reply(text: str) -> str:
    return finalize_qq_reply(text, max_chars=QQ_DCA_COMMAND_MAX_CHARS)


def try_handle_qq_message(text: str) -> str | None:
    """解析 QQ 定投/改仓指令；命中则返回回复，否则 None。"""
    q = (text or "").strip()
    if not q:
        return None

    lower = q.lower()
    if not any(k in lower for k in ("定投", "加仓", "买入", "买了", "持仓", "均价", "成本", "更新仓位", "更新持仓")):
        if not any(a in lower or a in q for a in BTC_USER_ALIASES):
            return None

    pos = load_position()

    m = re.search(
        r"(?:持仓|持有|仓位)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:枚?\s*)?btc",
        lower,
    )
    if m:
        qty = float(m.group(1))
        avg = pos.avg_cost_usdt or float(AgentConfig().btc_dca_initial_avg_usdt or 0)
        if avg <= 0:
            return "还缺均价哦，可以说「设置持仓 0.00288579btc 均价92212」～"
        pos.set_from_qty_and_avg(btc_quantity=qty, avg_cost_usdt=avg)
        save_position(
            pos,
            history_entry={"type": "set_qty", "btc_quantity": qty, "avg": avg, "at": _now_iso()},
        )
        return _finalize_dca_reply(_format_updated_reply(pos))

    m = re.search(
        r"(?:设置|更新).{0,8}?(?:持仓|仓位|成本).{0,20}?"
        r"(?:成本|投入|持仓)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:u|usdt|原石|刀)?"
        r".{0,40}?(?:均价|成本价|均价)\s*([0-9]+(?:\.[0-9]+)?)",
        q,
        re.I | re.S,
    )
    if m:
        cost = float(m.group(1))
        avg = float(m.group(2))
        pos.set_from_cost_and_avg(total_cost_usdt=cost, avg_cost_usdt=avg)
        save_position(
            pos,
            history_entry={"type": "set", "cost": cost, "avg": avg, "at": _now_iso()},
        )
        return _finalize_dca_reply(_format_updated_reply(pos))

    m = re.search(
        r"(?:定投|加仓|买了?).{0,12}?"
        r"([0-9]+(?:\.[0-9]+)?)\s*(?:u|usdt|原石|刀|美元)?"
        r".{0,30}?(?:价|@|价格|价位)\s*([0-9]+(?:\.[0-9]+)?)",
        q,
        re.I | re.S,
    )
    if not m:
        m = re.search(
            r"([0-9]+(?:\.[0-9]+)?)\s*(?:u|usdt|原石).{0,20}?([0-9]{4,6}(?:\.[0-9]+)?)",
            lower,
        )
    if m:
        spend = float(m.group(1))
        price = float(m.group(2))
        if price < 1000:
            return None
        pos.apply_dca(spend_usdt=spend, price_usdt=price)
        save_position(
            pos,
            history_entry={
                "type": "dca",
                "spend_usdt": spend,
                "price_usdt": price,
                "at": _now_iso(),
            },
        )
        return _finalize_dca_reply(
            _format_dca_reply(pos, spend_usdt=spend, price_usdt=price)
        )

    if "持仓" in q or "均价" in q:
        return _finalize_dca_reply(_format_status_reply(pos))
    return None


def _format_updated_reply(pos: BtcDcaPosition) -> str:
    return (
        f"好哒，持仓记好啦～累计投入约 {pos.total_cost_usdt:.2f} {CURRENCY_USDT_DISPLAY}，"
        f"均价 {pos.avg_cost_usdt:,.2f} {CURRENCY_USDT_DISPLAY}/枚，"
        f"约合 {pos.btc_quantity:.8f} 枚 {COIN_BTC_DISPLAY}。"
        f"每天早九点我会照旧报现价和盈亏哦。"
    )


def _format_dca_reply(pos: BtcDcaPosition, *, spend_usdt: float, price_usdt: float) -> str:
    return (
        f"嗯嗯，这笔 {spend_usdt:.2f} {CURRENCY_USDT_DISPLAY} @ {price_usdt:,.2f} 记进定投啦～"
        f"现在均价 {pos.avg_cost_usdt:,.2f} {CURRENCY_USDT_DISPLAY}，"
        f"累计 {pos.total_cost_usdt:.2f} {CURRENCY_USDT_DISPLAY}，"
        f"持仓约 {pos.btc_quantity:.8f} 枚 {COIN_BTC_DISPLAY}。"
    )


def _format_status_reply(pos: BtcDcaPosition) -> str:
    if pos.btc_quantity <= 0:
        return (
            f"这边还没记到你的 {COIN_BTC_DISPLAY} 持仓呢，"
            f"可以说「设置持仓 成本266 均价92212」这样～"
        )
    return (
        f"你现在的记录：均价 {pos.avg_cost_usdt:,.2f} {CURRENCY_USDT_DISPLAY}，"
        f"累计成本 {pos.total_cost_usdt:.2f} {CURRENCY_USDT_DISPLAY}，"
        f"约 {pos.btc_quantity:.8f} 枚 {COIN_BTC_DISPLAY}。"
    )

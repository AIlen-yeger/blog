"""AHR999 囤币指标（九神原版固定参数，仅适用于 BTC）。"""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_GENESIS = date(2009, 1, 3)
_PL_A = 5.84
_PL_B = -17.01
_MIN_GM_DAYS = 200

_BTC_HINTS = ("btc", "比特币", "bitcoin", "ahr999")


def is_btc_context(question: str, facts: dict[str, Any] | None = None) -> bool:
    q = (question or "").lower()
    if any(h in q for h in _BTC_HINTS):
        return True
    sym = str((facts or {}).get("symbol") or "").upper()
    if sym in ("BTC", "BITCOIN"):
        return True
    raw = str((facts or {}).get("raw") or "")
    if any(h in raw.lower() for h in ("btc", "比特币", "bitcoin")):
        return True
    return False


def coin_age_days(on_date: date | None = None) -> int:
    d = on_date or datetime.now(timezone.utc).date()
    return max(1, (d - _GENESIS).days)


def power_law_valuation_usd(on_date: date | None = None) -> float:
    days = coin_age_days(on_date)
    return 10 ** (_PL_A * math.log10(days) - _PL_B)


def geometric_mean(prices: list[float]) -> float | None:
    vals = [float(p) for p in prices if p is not None and float(p) > 0]
    if len(vals) < _MIN_GM_DAYS:
        return None
    return math.exp(sum(math.log(v) for v in vals) / len(vals))


def compute_ahr999(price_usd: float, daily_closes: list[float]) -> float | None:
    if price_usd <= 0:
        return None
    closes = daily_closes[-_MIN_GM_DAYS:]
    gm200 = geometric_mean(closes)
    if gm200 is None or gm200 <= 0:
        return None
    pl = power_law_valuation_usd()
    if pl <= 0:
        return None
    return (price_usd / gm200) * (price_usd / pl)


def ahr999_zone(value: float) -> str:
    if value < 0.45:
        return "bottom"
    if value <= 1.2:
        return "dca"
    return "above_dca"


def ahr999_zone_cn(zone: str) -> str:
    return {
        "bottom": "偏抄底（<0.45）",
        "dca": "定投区间（0.45～1.2）",
        "above_dca": "高于定投区（>1.2）",
    }.get(zone, zone)


def pick_usd_price(facts: dict[str, Any], tool_texts: list[str]) -> float | None:
    for key in ("usd", "USD", "price_usd"):
        v = _as_float((facts or {}).get(key))
        if v is not None and v > 0:
            return v

    for text in tool_texts:
        for obj in _iter_json_objects(text):
            v = _find_btc_usd_in_coin_info(obj)
            if v is not None:
                return v
            v = _find_usd_in_obj(obj)
            if v is not None:
                return v

    combined = " ".join(tool_texts)
    for pattern in (
        r'price_usd["\']?\s*[:=]\s*"?([0-9]+(?:\.[0-9]+)?)"?',
        r'(?:usd|USDT|美元)["\']?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)',
    ):
        m = re.search(pattern, combined, re.I)
        if m:
            try:
                v = float(m.group(1))
                if v > 100:
                    return v
            except ValueError:
                pass
    return None


def _find_btc_usd_in_coin_info(obj: Any) -> float | None:
    """coin_info ticker：优先 bitcoin/btc 主币，否则取 data 里最高 price_usd。"""
    if not isinstance(obj, dict):
        return None
    rows = obj.get("data")
    if not isinstance(rows, list):
        return None

    best: float | None = None
    for item in rows:
        if not isinstance(item, dict):
            continue
        key = str(item.get("coin_key") or item.get("coinKey") or "").lower()
        v = _as_float(item.get("price_usd"))
        if v is None or v <= 5000:
            continue
        if key in ("bitcoin", "btc") or (
            key.startswith("btc") and "5s" not in key and "3l" not in key
        ):
            return v
        if best is None or v > best:
            best = v
    return best


def pick_cny_price(facts: dict[str, Any], tool_texts: list[str]) -> float | None:
    for key in ("cny", "CNY", "price_cny"):
        v = _as_float((facts or {}).get(key))
        if v is not None and v > 0:
            return v

    for text in tool_texts:
        for obj in _iter_json_objects(text):
            v = _find_btc_cny_in_coin_info(obj)
            if v is not None:
                return v

    combined = " ".join(tool_texts)
    m = re.search(r'price_cny["\']?\s*[:=]\s*"?([0-9]+(?:\.[0-9]+)?)"?', combined, re.I)
    if m:
        v = _as_float(m.group(1))
        if v is not None and v > 10000:
            return v
    return None


def _find_btc_cny_in_coin_info(obj: Any) -> float | None:
    if not isinstance(obj, dict):
        return None
    rows = obj.get("data")
    if not isinstance(rows, list):
        return None

    best: float | None = None
    for item in rows:
        if not isinstance(item, dict):
            continue
        key = str(item.get("coin_key") or item.get("coinKey") or "").lower()
        v = _as_float(item.get("price_cny"))
        if v is None or v <= 50000:
            continue
        if key in ("bitcoin", "btc") or (
            key.startswith("btc") and "5s" not in key and "3l" not in key
        ):
            return v
        if best is None or v > best:
            best = v
    return best


def parse_usd_from_prose(text: str) -> float | None:
    raw = text or ""
    m = re.search(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)", raw)
    if m:
        v = _as_float(m.group(1).replace(",", ""))
        if v is not None and v > 1000:
            return v
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*k", raw, re.I)
    if m:
        v = _as_float(m.group(1))
        if v is not None:
            return v * 1000
    return None


def parse_cny_from_prose(text: str) -> float | None:
    raw = text or ""
    m = re.search(r"¥\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)", raw)
    if m:
        v = _as_float(m.group(1).replace(",", ""))
        if v is not None and v > 10000:
            return v
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*k", raw, re.I)
    if m and ("¥" in raw or "人民币" in raw or "cny" in raw.lower()):
        v = _as_float(m.group(1))
        if v is not None:
            return v * 1000
    return None


def backfill_facts_from_tools(
    facts: dict[str, Any],
    tool_texts: list[str],
    *,
    raw_final: str = "",
    question: str = "",
) -> dict[str, Any]:
    """ReAct 未输出 JSON 时，从 ToolMessage / 最终文本回填现价字段。"""
    out = dict(facts)
    if out.get("parse_ok") and out.get("usd"):
        return out

    usd = pick_usd_price(out, tool_texts) or parse_usd_from_prose(raw_final)
    cny = pick_cny_price(out, tool_texts) or parse_cny_from_prose(raw_final)

    if usd is not None:
        out["usd"] = usd
    if cny is not None:
        out["cny"] = cny
    if is_btc_context(question, out) or usd or cny:
        out.setdefault("symbol", "BTC")
    if usd or cny:
        out["parse_ok"] = True
        out["facts_source"] = "tool_backfill"
    return out


def extract_daily_closes_from_texts(texts: list[str]) -> list[float]:
    closes: list[float] = []
    for text in texts:
        for obj in _iter_json_objects(text):
            closes.extend(_extract_closes_from_obj(obj))
    return closes


def _iter_json_objects(text: str):
    text = (text or "").strip()
    if not text:
        return
    try:
        yield json.loads(text)
        return
    except json.JSONDecodeError:
        pass
    for m in re.finditer(r"\{[\s\S]*?\}|\[[\s\S]*?\]", text):
        try:
            yield json.loads(m.group(0))
        except json.JSONDecodeError:
            continue


def _find_usd_in_obj(obj: Any) -> float | None:
    if isinstance(obj, dict):
        for key in ("usd", "USD", "price_usd", "last", "close", "c", "price"):
            if key in obj:
                v = _as_float(obj[key])
                if v is not None and v > 100:
                    return v
        for v in obj.values():
            found = _find_usd_in_obj(v)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_usd_in_obj(item)
            if found is not None:
                return found
    return None


def _extract_closes_from_obj(obj: Any) -> list[float]:
    if isinstance(obj, list):
        if not obj:
            return []
        if all(isinstance(row, list) and len(row) >= 5 for row in obj[:3]):
            out: list[float] = []
            for row in obj:
                try:
                    out.append(float(row[4]))
                except (TypeError, ValueError, IndexError):
                    continue
            return [c for c in out if c > 0]
        if all(isinstance(row, dict) for row in obj[: min(3, len(obj))]):
            out = []
            for row in obj:
                if not isinstance(row, dict):
                    continue
                for key in ("close", "c", "Close", "closing_price"):
                    if key in row:
                        v = _as_float(row[key])
                        if v is not None and v > 0:
                            out.append(v)
                            break
            return out
        merged: list[float] = []
        for item in obj:
            merged.extend(_extract_closes_from_obj(item))
        return merged

    if isinstance(obj, dict):
        for key in (
            "kline_data",
            "data",
            "list",
            "records",
            "kline",
            "klines",
            "dataRecords",
        ):
            if key in obj:
                found = _extract_closes_from_obj(obj[key])
                if len(found) >= _MIN_GM_DAYS:
                    return found
        merged: list[float] = []
        for v in obj.values():
            found = _extract_closes_from_obj(v)
            if len(found) > len(merged):
                merged = found
        return merged
    return []


def _as_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_btc_daily_closes_mcp(*, size: int = 210) -> list[float]:
    try:
        from utils.mcp.registry import get_mcp_client, is_mcp_enabled

        if not is_mcp_enabled("aicoin"):
            return []
        client = get_mcp_client("aicoin")
        result = client.call_tool_sync(
            {
                "action": "data",
                "symbol": "btcusdt:binance",
                "period": "86400",
                "size": str(max(_MIN_GM_DAYS, min(size, 500))),
            },
            tool_name="kline",
        )
        if not result.ok or not (result.text or "").strip():
            return []
        return extract_daily_closes_from_texts([result.text])
    except Exception as exc:
        logger.warning("[ahr999] fetch kline failed: %s", exc)
        return []


def build_ahr999_block(*, price_usd: float, daily_closes: list[float]) -> dict[str, Any]:
    gm200 = geometric_mean(daily_closes[-_MIN_GM_DAYS:])
    pl = power_law_valuation_usd()
    val = compute_ahr999(price_usd, daily_closes)
    if val is None:
        return {"ahr999": None, "ahr999_ok": False, "ahr999_note": "计算失败"}
    zone = ahr999_zone(val)
    return {
        "ahr999": round(val, 4),
        "ahr999_ok": True,
        "ahr999_zone": zone,
        "ahr999_zone_cn": ahr999_zone_cn(zone),
        "gm200_usd": round(gm200, 2) if gm200 else None,
        "pl_usd": round(pl, 2),
        "coin_age_days": coin_age_days(),
    }


def enrich_facts_with_ahr999(
    facts: dict[str, Any],
    tool_texts: list[str],
    question: str,
    *,
    fetch_if_missing: bool = True,
) -> dict[str, Any]:
    if not is_btc_context(question, facts):
        return facts

    price = pick_usd_price(facts, tool_texts)
    if price is None:
        facts.setdefault("ahr999", None)
        facts.setdefault("ahr999_ok", False)
        facts["ahr999_note"] = "缺少 USD 现价"
        logger.info("[ahr999] skip: no usd price in facts or tool texts")
        return facts

    closes = extract_daily_closes_from_texts(tool_texts)
    kline_source = "tool_messages" if len(closes) >= _MIN_GM_DAYS else ""
    if len(closes) < _MIN_GM_DAYS and fetch_if_missing:
        closes = fetch_btc_daily_closes_mcp()
        kline_source = "mcp_kline" if len(closes) >= _MIN_GM_DAYS else "mcp_kline_failed"

    if len(closes) < _MIN_GM_DAYS:
        facts.setdefault("ahr999", None)
        facts.setdefault("ahr999_ok", False)
        facts["ahr999_note"] = f"日K不足{_MIN_GM_DAYS}根，无法计算"
        facts["ahr999_kline_bars"] = len(closes)
        facts["ahr999_kline_source"] = kline_source or "none"
        logger.info(
            "[ahr999] skip: price=%s bars=%s source=%s",
            price,
            len(closes),
            kline_source or "none",
        )
        return facts

    block = build_ahr999_block(price_usd=price, daily_closes=closes)
    block["ahr999_kline_bars"] = len(closes)
    block["ahr999_kline_source"] = kline_source or "tool_messages"
    facts.update(block)
    logger.info(
        "[ahr999] ok value=%s zone=%s bars=%s source=%s",
        block.get("ahr999"),
        block.get("ahr999_zone"),
        len(closes),
        block.get("ahr999_kline_source"),
    )
    return facts


def tool_texts_from_messages(messages: list) -> list[str]:
    texts: list[str] = []
    for m in messages or []:
        if type(m).__name__ != "ToolMessage":
            continue
        raw = getattr(m, "content", "") or ""
        texts.append(raw if isinstance(raw, str) else str(raw))
    return texts

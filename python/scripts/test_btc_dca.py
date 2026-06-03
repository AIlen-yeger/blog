"""BTC 定投日报 / 持仓 — 本地一条命令测试（Windows CMD 可直接复制）。

用法（在 python 目录、已激活 .venv）:

  python scripts/test_btc_dca.py
  python scripts/test_btc_dca.py --send
  python scripts/test_btc_dca.py --position
  python scripts/test_btc_dca.py --parse "持仓"
  python scripts/test_btc_dca.py --parse "定投 50u 价格90000"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _import_deps() -> None:
    try:
        import langchain_openai  # noqa: F401
    except ModuleNotFoundError as exc:
        print(
            "缺少依赖，请在 python 目录、已激活 .venv 时执行:\n"
            "  pip install -r requirements.txt\n"
            f"原始错误: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


def _print_position() -> None:
    from service.btc_dca_position import load_position, position_pnl_usdt
    from utils.world_lexicon import COIN_BTC_DISPLAY, CURRENCY_USDT_DISPLAY

    pos = load_position()
    print("=== 持仓 ===")
    print(f"  {COIN_BTC_DISPLAY} 数量: {pos.btc_quantity:.8f}")
    print(f"  均价({CURRENCY_USDT_DISPLAY}): {pos.avg_cost_usdt:,.4f}")
    print(f"  累计成本:   {pos.total_cost_usdt:.2f} {CURRENCY_USDT_DISPLAY}")
    if pos.updated_at:
        print(f"  更新时间:   {pos.updated_at}")
    print()


def _print_facts_and_message(*, polish: bool = True) -> None:
    from service.btc_dca_position import load_position, position_pnl_usdt
    from service.btc_daily_brief import build_daily_facts, polish_daily_qq_message

    facts = build_daily_facts()
    pos = load_position()
    spot = facts.get("spot_usd")
    if spot and pos.btc_quantity > 0:
        facts.update(position_pnl_usdt(pos=pos, spot_usd=float(spot)))

    print("=== 行情与盈亏（只读 JSON）===")
    print(json.dumps(facts, ensure_ascii=False, indent=2))
    print()

    if not polish:
        return

    if not facts.get("quote_ok"):
        print("提示: quote_ok=false，请检查 AICOIN_MCP_ENABLED 与 MCP 是否可用")
        print()

    print("=== QQ 日报文案（润色后）===")
    msg = polish_daily_qq_message(facts)
    print(msg)
    print()


def _send_qq() -> None:
    from utils.qq.napcat_notify import napcat_configured

    if not napcat_configured():
        print("NapCat 未配置：请设置 NAPCAT_HTTP_URL、NAPCAT_ALERT_QQ，并启动 NapCat")
        raise SystemExit(1)

    from service.btc_daily_brief import send_daily_brief_to_developer

    result = send_daily_brief_to_developer(force=True)
    print("=== 推送结果 ===")
    print(json.dumps({k: v for k, v in result.items() if k != "facts"}, ensure_ascii=False, indent=2))
    if result.get("ok"):
        print("\n已发送到 NAPCAT_ALERT_QQ，请查 QQ 私聊。")
    else:
        raise SystemExit(1)


def _parse_message(text: str) -> None:
    from service.btc_dca_position import try_handle_qq_message

    print(f"=== 解析 QQ 指令: {text!r} ===")
    reply = try_handle_qq_message(text)
    if reply:
        print(reply)
    else:
        print("(未识别为定投/持仓指令)")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="BTC 定投本地测试")
    parser.add_argument(
        "--position",
        action="store_true",
        help="只打印持仓",
    )
    parser.add_argument(
        "--no-polish",
        action="store_true",
        help="只拉行情 JSON，不调 chat 润色",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="通过 NapCat 真发一条 QQ（需 NapCat 已登录）",
    )
    parser.add_argument(
        "--parse",
        metavar="TEXT",
        default="",
        help='测试持仓/定投解析，如 --parse "持仓"',
    )
    args = parser.parse_args()

    _import_deps()
    from config.config import ensure_env_loaded
    from utils.mcp.registry import reload_mcp_configs

    ensure_env_loaded()
    reload_mcp_configs()

    if args.parse:
        _parse_message(args.parse.strip())
        return

    if args.position:
        _print_position()
        return

    _print_position()
    _print_facts_and_message(polish=not args.no_polish)

    if args.send:
        _send_qq()


if __name__ == "__main__":
    main()

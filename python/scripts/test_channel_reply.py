"""本地模拟 web / QQ 渠道回复，不经过 NapCat、不收发真实 QQ 消息。

用法（在 python 目录、已激活 .venv）:

  # QQ 渠道 + 行情（需 AICOIN_MCP_ENABLED、DEVELOPER_EMAIL 或 admin）
  python scripts/test_channel_reply.py --channel qq --question "btc现在多少钱"

  # QQ 闲聊语气
  python scripts/test_channel_reply.py --channel qq --question "在干嘛呀"

  # 对比同一句在 web / qq 下的 system 提示词（不调模型）
  python scripts/test_channel_reply.py --show-prompt --intent aicoin

  # 强制意图，跳过 judge
  python scripts/test_channel_reply.py --channel qq --intent aicoin --question "eth走势"

  # 模拟非管理员（应降级 chat，无行情工具）
  python scripts/test_channel_reply.py --channel qq --question "btc多少钱" --guest
"""
from __future__ import annotations

import argparse
import os
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


_import_deps()

from config.config import AgentConfig, ensure_env_loaded
from server.agent_entry import get_agent_entry
from server.aicoin_access import is_aicoin_allowed
from server.prompt_skills import build_system_prompt


def _dev_identity() -> tuple[str, str, str, int]:
    cfg = AgentConfig()
    email = (cfg.developer_email or os.getenv("DEVELOPER_EMAIL") or "").strip()
    qq = cfg.developer_qq or "".join(c for c in os.getenv("DEVELOPER_QQ", "") if c.isdigit())
    if not qq:
        qq = "".join(c for c in (os.getenv("NAPCAT_ALERT_QQ") or "") if c.isdigit())
    return email, "admin", qq, 7


def _print_prompt(*, channel: str, intent: str) -> None:
    email, role, qq, _ = _dev_identity()
    text = build_system_prompt(
        intent=intent or "chat",
        user_logged_in=True,
        channel=channel,
        developer_name="开发者",
    )
    print(f"\n=== system prompt · channel={channel} intent={intent or 'chat'} ===\n")
    print(text)
    print(f"\n--- len={len(text)} chars ---\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="模拟渠道回复（不走真实 QQ）")
    parser.add_argument("--channel", default="qq", choices=("qq", "web"))
    parser.add_argument("--question", default="btc现在多少钱")
    parser.add_argument("--intent", default="", help="force_intent，如 aicoin / chat / music")
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="只打印 system 提示词，不调用模型",
    )
    parser.add_argument(
        "--compare-prompt",
        action="store_true",
        help="打印 web 与 qq 的 aicoin system 提示词对比",
    )
    parser.add_argument(
        "--guest",
        action="store_true",
        help="模拟普通用户（非 admin / 非开发者邮箱）",
    )
    parser.add_argument(
        "--bridge",
        action="store_true",
        help="按 QQ 桥接同样方式解析身份（token-for-qq），不用脚本内置 admin",
    )
    args = parser.parse_args()

    ensure_env_loaded()
    from utils.mcp.registry import reload_mcp_configs
    from utils.trace_log import setup_agent_logging

    setup_agent_logging()
    reload_mcp_configs()

    if args.compare_prompt:
        _print_prompt(channel="web", intent="aicoin")
        _print_prompt(channel="qq", intent="aicoin")
        return

    if args.show_prompt:
        intent = (args.intent or "aicoin").strip()
        _print_prompt(channel=args.channel, intent=intent)
        return

    email, role, qq, user_id = _dev_identity()
    if args.guest:
        email, role, qq, user_id = "guest@example.com", "user", "100000000", 999
    elif args.bridge and args.channel == "qq":
        from utils.qq.qq_blog_auth import resolve_qq_blog_identity

        qq = qq or _dev_identity()[2]
        identity = resolve_qq_blog_identity(qq)
        if identity:
            email = identity.email
            role = identity.role or "user"
            user_id = identity.user_id
            print(f"[bridge] 已绑定博客身份 email={email} role={role} user_id={user_id}")
        else:
            email, role, user_id = "", "", 0
            print(f"[bridge] 未找到 {qq}@qq.com 博客账号 → 与真实 QQ 游客一致，行情会降级 chat")

    channel = args.channel.strip().lower()
    allowed = is_aicoin_allowed(
        account=email,
        user_role=role,
        friend_qq=qq,
        channel=channel,
    )
    print(
        f"[preflight] channel={channel} account={email or '-'} role={role} "
        f"friend_qq={qq or '-'} aicoin_allowed={allowed}"
    )

    entry = get_agent_entry()
    result = entry.run(
        question=args.question.strip(),
        session_id=f"test:{channel}:local",
        user_id=user_id,
        limit=4,
        channel=channel,
        force_intent=(args.intent or "").strip(),
        user_name="开发者",
        account=email,
        user_role=role,
        friend_qq=qq,
    )

    print(f"\n[intent] {result.intent}  [mode] {result.output_mode}  [channel] {result.channel}")
    if args.channel == "qq" and result.intent == "aicoin":
        print("QQ 行情若开启 QQ_AICOIN_TWO_PHASE，实际走：数据采集 ReAct → chat 润色")
    if result.intent == "chat" and ("btc" in args.question.lower() or "币" in args.question):
        print(
            "提示: intent=chat 时不会调行情 MCP，语气像 QQ 陪聊；"
            "要测 QQ 行情请保证 aicoin_allowed=True（admin/开发者邮箱/DEVELOPER_QQ）。"
        )
    print("\n=== 回复 ===\n")
    print(result.plain_text())
    print()


if __name__ == "__main__":
    main()

"""对比 web 桌宠 vs QQ 私聊的闲聊语气（蕾西亚人设 · force chat）。

在 python 目录、已配置 .env 且激活 .venv 后运行：

  # 跑内置 5 条用例，每条分别在 web / qq 各回一次（共 10 次模型调用）
  python scripts/test_channel_tone.py

  # 只跑一条内置用例
  python scripts/test_channel_tone.py --case mood

  # 自定义一句，双渠道对比
  python scripts/test_channel_tone.py --question "今天心情怎么样"

  # 只看两渠道 system+channel 技能拼接（不调模型）
  python scripts/test_channel_tone.py --skills-only

  # 列出用例 key
  python scripts/test_channel_tone.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _import_deps() -> None:
    try:
        import langchain_openai  # noqa: F401
    except ModuleNotFoundError as exc:
        print(
            "缺少依赖:\n  pip install -r requirements.txt\n"
            f"原始错误: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


@dataclass(frozen=True)
class ToneCase:
    key: str
    title: str
    question: str
    hint: str = ""


TONE_CASES: tuple[ToneCase, ...] = (
    ToneCase("greeting", "寒暄", "嗨，在吗？", "QQ 应更短更生活化；Web 可稍带工作室感"),
    ToneCase("mood", "心情倾诉", "今天有点累，不太想动。", "测共情；两渠道都应沉静、第一人称"),
    ToneCase("bored", "无聊陪聊", "好无聊啊。", "QQ 单句陪伴；Web 可轻接博客/音乐"),
    ToneCase("studio", "工作室/创作", "我想给博客歌单加一首歌，要怎么弄？", "Web 应更偏业务助手"),
    ToneCase("name", "自我介绍", "你叫什么名字？", "必须回答蕾西亚"),
)

# 固定 5 个场景；默认全跑 = 5 用例 × 2 渠道 = 10 次模型调用


def _is_balance_error(text: str) -> bool:
    t = (text or "").lower()
    return "402" in text or "insufficient balance" in t or "余额不足" in text


def _collect_reply(result) -> str:
    if result.text is not None:
        return (result.text or "").strip()
    parts: list[str] = []
    for raw in result.iter_sse():
        line = raw.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        if data.get("type") in ("delta", "message"):
            parts.append(str(data.get("content") or ""))
        elif isinstance(data.get("message"), str):
            parts.append(data["message"])
    return "".join(parts).strip()


def _print_block(title: str, body: str, *, width: int = 72) -> None:
    print("\n" + "=" * width)
    print(title)
    print("=" * width)
    print(body or "（空回复）")
    print(f"--- 字数: {len(body)} ---")


def _run_one(
    entry,
    *,
    channel: str,
    question: str,
    session_id: str,
    user_id: int,
    email: str,
    role: str,
    qq: str,
) -> tuple[str, str]:
    result = entry.run(
        question=question,
        session_id=session_id,
        user_id=user_id,
        limit=2,
        channel=channel,
        force_intent="chat",
        user_name="开发者",
        account=email,
        user_role=role,
        friend_qq=qq,
    )
    text = _collect_reply(result)
    return result.intent, text


def _print_prompts() -> None:
    from server.prompt_skills import build_system_prompt

    for ch in ("web", "qq"):
        text = build_system_prompt(
            intent="chat",
            user_logged_in=True,
            channel=ch,
            developer_name="开发者",
        )
        _print_block(f"system + channel 技能 · {ch}", text)


def main() -> None:
    parser = argparse.ArgumentParser(description="web / qq 闲聊语气对比（蕾西亚）")
    parser.add_argument("--case", default="", help="内置用例 key，默认跑全部")
    parser.add_argument("--question", default="", help="自定义问题（双渠道对比）")
    parser.add_argument(
        "--skills-only",
        action="store_true",
        help="只打印 web/qq 的 chat system 提示词",
    )
    parser.add_argument("--list", action="store_true", help="列出内置用例")
    parser.add_argument(
        "--channel",
        default="",
        choices=("", "web", "qq"),
        help="只测单一渠道（默认 web+qq 都测）",
    )
    args = parser.parse_args()

    if args.list:
        print("内置用例:")
        for c in TONE_CASES:
            extra = f" — {c.hint}" if c.hint else ""
            print(f"  {c.key:10} {c.title:8} {c.question}{extra}")
        return

    _import_deps()

    if args.prompt_only:
        _print_prompts()
        return

    from config.config import ensure_env_loaded
    from server.agent_entry import get_agent_entry
    from utils.mcp.registry import reload_mcp_configs
    from utils.log.trace_log import setup_agent_logging

    ensure_env_loaded()
    setup_agent_logging()
    reload_mcp_configs()

    from config.config import AgentConfig

    cfg = AgentConfig()
    cfg_email = (cfg.developer_email or "").strip()
    qq = cfg.developer_qq or ""
    email, role, qq, user_id = cfg_email or "dev@test.local", "admin", qq, 1

    if args.question.strip():
        cases = [
            ToneCase("custom", "自定义", args.question.strip(), "双渠道同句对比"),
        ]
    elif args.case.strip():
        key = args.case.strip()
        cases = [c for c in TONE_CASES if c.key == key]
        if not cases:
            print(f"未知 case: {key}，用 --list 查看", file=sys.stderr)
            raise SystemExit(2)
    else:
        cases = list(TONE_CASES)

    channels = ["web", "qq"]
    if args.channel:
        channels = [args.channel]

    print("蕾西亚 · 渠道语气对比测试")
    print(f"用例数: {len(cases)}  渠道: {', '.join(channels)}  intent=chat（强制）")
    print(f"模型: {cfg.chat_model_name}  base_url: {cfg.chat_base_url}")
    print("说明: web 走流式收集；qq 走 once。每用例每渠道独立 session，避免历史串味。")

    entry = get_agent_entry()
    balance_abort = False

    for tc in cases:
        if balance_abort:
            print(f"\n[跳过] 用例 [{tc.key}]：此前已检测到 API 余额不足")
            continue
        _print_block(f"用例 [{tc.key}] {tc.title} · 用户: {tc.question}", tc.hint or "（无说明）")
        for ch in channels:
            sid = f"tone:{ch}:{tc.key}"
            try:
                intent, reply = _run_one(
                    entry,
                    channel=ch,
                    question=tc.question,
                    session_id=sid,
                    user_id=user_id,
                    email=email,
                    role=role,
                    qq=qq,
                )
                _print_block(f">>> 渠道={ch}  intent={intent}", reply)
                if _is_balance_error(reply):
                    balance_abort = True
                    print(
                        "\n[中止] API 402 余额不足，后续用例已跳过。\n"
                        "  1) 到 DeepSeek 控制台充值或换 Key\n"
                        "  2) 确认 G:\\Projects\\blog\\python\\.env 的 DP_AGENT_API_KEY\n"
                        "  3) 暂不调模型可先: python scripts/test_channel_tone.py --skills-only"
                    )
                    break
            except Exception as exc:
                print(f"\n>>> 渠道={ch} 失败: {exc}", file=sys.stderr)
                if _is_balance_error(str(exc)):
                    balance_abort = True
                    break
        if balance_abort:
            break

    print("\n" + "=" * 72)
    if balance_abort:
        print("未完成语气对比（余额不足）。修复 API 后重新运行本脚本。")
    else:
        print("完成。对照要点: QQ 更短(约60字内)、更生活；Web 可稍干练并接工作室/博客。")
    print("=" * 72)


if __name__ == "__main__":
    main()

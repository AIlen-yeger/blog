#!/usr/bin/env python3
"""对比「完整闲聊」与「完整音乐 ReAct」的提示词 / 消息 token。

默认（0 LLM）：完整闲聊 system（lore+recall）+ 音乐 OpenClaw system + 工具 schema 估算。
加 --live：再各跑一遍真实对话 / 音乐 ReAct（会消耗 API token）。

  python scripts/compare_capability_tokens.py
  python scripts/compare_capability_tokens.py --live
  python scripts/compare_capability_tokens.py --live --react-rounds 2
  python scripts/compare_capability_tokens.py --dump-dir reports/compare_tokens
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.config import AgentConfig, chat_llm_configured, ensure_env_loaded, embedding_configured
from server.agent_entry import AgentEntry
from server.route_graph.music_route import run_music_react
from server.route_graph.react_subgraph import count_tool_rounds, effective_max_react_rounds
from server.skills_server.prompt_assembler import PromptContext, assemble_chat_system
from server.skills_server.prompt_trace import (
    estimate_messages_tokens,
    estimate_tokens,
    estimate_tools_schema_tokens,
    trace_assemble,
)
from server.skills_server.skill_registry import get_registry
from server.tools.music_agent_tools import build_music_tools, detect_music_task_mode
def _chat_ctx(question: str, channel: str, user_id: int) -> PromptContext:
    return PromptContext(
        intent="chat",
        channel=channel,
        user_message=question,
        user_id=user_id,
        user_logged_in=False,
        include_lore=True,
        include_recall=True,
    )


def _music_ctx(question: str, channel: str, user_id: int, *, logged_in: bool) -> PromptContext:
    return PromptContext(
        intent="music",
        channel=channel,
        user_message=question,
        user_id=user_id,
        user_logged_in=logged_in,
        include_lore=False,
        include_recall=False,
    )


def _dump(path: Path, name: str, text: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    out = path / name
    out.write_text(text, encoding="utf-8")
    print(f"  已写入 {out} ({len(text)} 字)")


def _run_live_chat(question: str, channel: str, user_id: int) -> dict:
    """与 agent_entry 闲聊分支一致（web=流式 / qq=once）。"""
    entry = AgentEntry()
    t0 = time.perf_counter()
    reply = entry.run(
        question=question,
        session_id=f"compare-chat-{int(time.time())}",
        user_id=user_id,
        limit=0,
        channel=channel,
        force_intent="chat",
        trace_id=f"compare-chat-{int(time.time())}",
    )
    ms = round((time.perf_counter() - t0) * 1000, 2)
    text = ""
    if reply.output_mode == "once":
        text = reply.plain_text()
    else:
        chunks: list[str] = []
        for line in reply.iter_sse():
            if not line.startswith("data: ") or "[DONE]" in line:
                continue
            try:
                payload = json.loads(line[6:].strip())
            except json.JSONDecodeError:
                continue
            if payload.get("type") == "delta":
                chunks.append(payload.get("content") or "")
        text = "".join(chunks).strip()
    ans_tok, _ = estimate_tokens(text)
    return {
        "channel": channel,
        "output_mode": reply.output_mode,
        "answer": text,
        "answer_tokens": ans_tok,
        "ms": ms,
    }


def _run_live_music(
    question: str,
    channel: str,
    user_id: int,
    access_token: str,
) -> dict:
    state = {
        "question": question,
        "session_id": f"compare-music-{int(time.time())}",
        "user_id": user_id,
        "limit": 0,
        "access_token": access_token,
        "trace_id": f"compare-music-{int(time.time())}",
        "channel": channel,
        "intent": "music",
    }
    t0 = time.perf_counter()
    result = run_music_react(state)
    ms = round((time.perf_counter() - t0) * 1000, 2)
    messages = result.get("messages") or []
    msg_stats = estimate_messages_tokens(messages)
    final = (result.get("final_answer") or "").strip()
    return {
        "final_answer": final,
        "tool_rounds": count_tool_rounds(messages),
        "message_stats": msg_stats,
        "ms": ms,
    }


def main() -> None:
    ensure_env_loaded()
    parser = argparse.ArgumentParser(
        description="完整闲聊 vs 音乐 ReAct：拼装 token + 可选真实跑一遍",
    )
    parser.add_argument("--channel", default="web", choices=("web", "qq"))
    parser.add_argument(
        "--question",
        default="你好蕾西亚；帮我看看最近听了什么歌，一句话总结。",
    )
    parser.add_argument("--user-id", type=int, default=9001)
    parser.add_argument(
        "--access-token",
        default=os.getenv("TEST_ACCESS_TOKEN", "test-token"),
        help="音乐 ReAct 调 Java/QQ 工具用（--live 时）",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="真实调 LLM：闲聊一轮 + 音乐 ReAct（会耗 token）",
    )
    parser.add_argument(
        "--react-rounds",
        type=int,
        default=2,
        help="--live 时音乐 ReAct 最大轮次（默认 2，防百万 token）",
    )
    parser.add_argument(
        "--dump-dir",
        default="",
        help="写出 chat_full_system.txt / music_system.txt",
    )
    args = parser.parse_args()

    if args.live:
        cfg = AgentConfig()
        if not chat_llm_configured(cfg):
            print("错误: 未配置 DP_MODEL / DP_CHAT_API_KEY，无法 --live", file=sys.stderr)
            raise SystemExit(1)
        if not embedding_configured(cfg):
            print("提示: 未配置 EMBEDDING_*，recall 可能为空。")
        os.environ["TEST_REACT_MAX_ROUNDS"] = str(max(1, min(12, args.react_rounds)))

    ch = args.channel
    q = args.question.strip()
    uid = args.user_id
    reg = get_registry()
    dump = Path(args.dump_dir) if args.dump_dir else None

    # ── 1. 完整闲聊（线上 chat system = lore + recall + optional）──
    chat_trace = trace_assemble(_chat_ctx(q, ch, uid))
    chat_system_via_api = assemble_chat_system(_chat_ctx(q, ch, uid))
    if chat_system_via_api != chat_trace.system_prompt:
        print("警告: trace 与 assemble_chat_system 正文不一致，以 trace 为准")

    # ── 2. 音乐 OpenClaw system（ReAct 首条，无 lore/recall）──
    music_trace = trace_assemble(
        _music_ctx(q, ch, uid, logged_in=bool(args.access_token)),
    )
    mode = detect_music_task_mode(q)
    tools = build_music_tools(args.access_token, mode=mode)
    tools_tok, tools_chars = estimate_tools_schema_tokens(tools)
    max_rounds = effective_max_react_rounds()
    music_react_est = music_trace.system_tokens + tools_tok * (1 + max_rounds)

    print("=" * 72)
    print("路由对比 · 完整闲聊 system vs 音乐 ReAct（默认 0 LLM）")
    print("=" * 72)
    print(f"角色包: {reg.character_root}")
    print(f"channel={ch}  user_id={uid}")
    print(f"示例句: {q[:72]}{'…' if len(q) > 72 else ''}")
    print(f"token 估算: {chat_trace.token_method}\n")

    print("【一、完整闲聊 · 仅拼装（= 线上 chat 进 LLM 前的 system）】")
    print(f"  system 字符: {chat_trace.system_chars}")
    print(f"  system tokens: {chat_trace.system_tokens}")
    print(f"  optional_core: {chat_trace.tavern_optional_core or '(无)'}")
    print(f"  lore 命中: {chat_trace.tavern_lore_hit}  recall 命中: {chat_trace.tavern_recall_hit}")
    for layer in chat_trace.layers:
        if layer.tokens:
            print(f"    · {layer.name}: {layer.tokens} tok")

    print("\n【二、音乐路由 · OpenClaw system（ReAct 无酒馆层）】")
    print(f"  system 字符: {music_trace.system_chars}")
    print(f"  system tokens: {music_trace.system_tokens}")
    print(f"  相对闲聊 system 增量: +{music_trace.system_tokens - chat_trace.system_tokens} tok")
    print(f"  计划加载: {', '.join(music_trace.openclaw_capabilities)}")

    print("\n【三、音乐 ReAct · 工具 schema（未调 LLM 的粗算）】")
    print(f"  工具 mode={mode}  数量={len(tools)}  schema≈{tools_tok} tok ({tools_chars} 字)")
    print(
        f"  粗算每轮请求 ≈ system({music_trace.system_tokens}) + tools({tools_tok})"
        f"  × (1+工具轮)  按 max_rounds={max_rounds} → 约 {music_react_est} tok 输入上界"
    )
    print("  （真实账单还含多轮 observation、历史；以 --live 实测为准）")

    if dump:
        _dump(dump, "chat_full_system.txt", chat_trace.system_prompt)
        _dump(dump, "music_system.txt", music_trace.system_prompt)

    if not args.live:
        print("\n" + "-" * 72)
        print("当前未调 LLM。要看「完整出结果」（闲聊回复 + 音乐调工具）请执行：")
        print("  python scripts/compare_capability_tokens.py --live --react-rounds 2")
        print("=" * 72)
        return

    print("\n" + "-" * 72)
    print("【四、完整闲聊 · 真实 LLM 一轮】")
    live_chat = _run_live_chat(q, ch, uid)
    print(f"  output_mode={live_chat['output_mode']}  耗时 {live_chat['ms']} ms")
    print(f"  回复 tokens≈{live_chat['answer_tokens']}")
    print(f"  回复正文:\n{live_chat['answer'][:800]}{'…' if len(live_chat['answer']) > 800 else ''}")

    print("\n【五、完整音乐 · ReAct + 工具】")
    live_music = _run_live_music(q, ch, uid, args.access_token)
    ms = live_music["message_stats"]
    print(f"  工具轮次: {live_music['tool_rounds']}  耗时 {live_music['ms']} ms")
    print(f"  消息列表合计 tokens≈{ms['total_tokens']}  按类型: {ms['by_kind']}")
    print(f"  最终回复:\n{live_music['final_answer'][:800]}{'…' if len(live_music['final_answer']) > 800 else ''}")
    for row in ms.get("rows") or []:
        print(f"    [{row['index']}] {row['kind']}: {row['tokens']} tok")

    print("\n【汇总】")
    print(f"  闲聊 system: {chat_trace.system_tokens} tok")
    print(f"  闲聊 system + 单轮回复≈{chat_trace.system_tokens + live_chat['answer_tokens']} tok（未计历史/judge/记忆子图）")
    print(f"  音乐 ReAct 消息链≈{ms['total_tokens']} tok（含 system+tools 多轮重复）")
    print("=" * 72)


if __name__ == "__main__":
    main()

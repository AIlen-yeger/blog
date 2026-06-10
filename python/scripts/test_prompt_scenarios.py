#!/usr/bin/env python3
"""分场景测试：OpenClaw 能力提示词 + 酒馆角色/记忆注入。

默认只拼装 prompt 并生成 HTML 报告，不调 LLM（0 API token）。

用法:

  python scripts/test_prompt_scenarios.py
  python scripts/test_prompt_scenarios.py --live --scenario openclaw_chat_web
  python scripts/test_prompt_scenarios.py --live-all   # 危险：多场景 + ReAct，token 极高
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
import uuid
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _import_deps() -> None:
    try:
        import langchain_openai  # noqa: F401
    except ModuleNotFoundError as exc:
        print(
            "缺少依赖: pip install -r requirements.txt\n"
            f"{exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


_import_deps()

from config.config import AgentConfig, chat_llm_configured, ensure_env_loaded, embedding_configured
from langchain_core.messages import HumanMessage, SystemMessage
from server.agent import ChatModel
from server.agent_entry import get_agent_entry
from server.embedding.embedding_user_memory import get_user_memory
from server.skills_server.prompt_assembler import assemble_for_state


def _load_report_writer():
    path = ROOT / "scripts" / "prompt_scenario_report.py"
    spec = importlib.util.spec_from_file_location("prompt_scenario_report", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.write_report_bundle


from server.skills_server.prompt_trace import (
    AssembleTrace,
    estimate_tokens,
    trace_assemble,
    trace_context_for_scenario,
    trace_to_dict,
)
from utils.judge_intent.quick_judge import should_skip_memory_pipeline


def preflight_assemble() -> None:
    """启动前快速预检（不调 LLM），避免跑完 8 场景才发现配置/代码错误。"""
    from server.skills_server.skill_registry import get_registry

    reg = get_registry()
    if not reg.get_for_intent("chat"):
        raise RuntimeError("manifest 缺少 chat capability")
    ctx = trace_context_for_scenario(
        scenario_id="preflight",
        intent="chat",
        channel="web",
        question="预检",
    )
    trace = trace_assemble(ctx)
    if not trace.system_prompt or trace.system_tokens < 50:
        raise RuntimeError("assemble 结果异常偏短")
    music_ctx = trace_context_for_scenario(
        scenario_id="preflight_music",
        intent="music",
        channel="web",
        question="预检",
    )
    music_ctx.user_logged_in = True
    music_ctx.include_lore = False
    music_ctx.include_recall = False
    music_trace = trace_assemble(music_ctx)
    music_delta = music_trace.system_tokens - trace.system_tokens
    print(
        f"预检通过 · 角色包={reg.character_root} · chat ~{trace.system_tokens} tok"
        f" · music(OpenClaw) ~{music_trace.system_tokens} tok (+{music_delta} vs chat)"
    )
    print("  详表: python scripts/compare_capability_tokens.py --with-lore-recall")


@dataclass
class Scenario:
    id: str
    title: str
    force_intent: str
    channel: str
    question: str
    user_id: int = 9001
    access_token: str = ""
    note_id: str = ""
    job_id: str = ""
    use_agent_entry: bool = True
    allow_live: bool = False  # --live 时仅跑标记为 True 的场景
    tags: list[str] = field(default_factory=list)


SCENARIOS: list[Scenario] = [
    Scenario(
        id="openclaw_chat_web",
        title="OpenClaw·Web 闲聊",
        force_intent="chat",
        channel="web",
        question="你好蕾西亚，用一两句话打个招呼。",
        allow_live=True,
        tags=["openclaw", "chat", "lore", "recall"],
    ),
    Scenario(
        id="tavern_optional_profile",
        title="酒馆·optional core（身份/称呼）",
        force_intent="chat",
        channel="web",
        question="蕾西亚你是谁？开发者叫什么名字？",
        tags=["tavern", "optional_core"],
    ),
    Scenario(
        id="tavern_lore_recall",
        title="酒馆·lore + recall",
        force_intent="chat",
        channel="web",
        question="你还记得我上次跟你说过什么吗？顺便说说 hIE 人形。",
        tags=["tavern", "lore", "recall", "memory_pipeline"],
    ),
    Scenario(
        id="fast_track_skip",
        title="快车道·跳过记忆/recall",
        force_intent="chat",
        channel="qq",
        question="嗯",
        tags=["skip_memory", "skip_recall"],
    ),
    Scenario(
        id="openclaw_music",
        title="OpenClaw·音乐 ReAct",
        force_intent="music",
        channel="web",
        question="帮我看看最近听了什么歌，一句话总结。",
        access_token="test-token",
        tags=["openclaw", "react", "music"],
    ),
    Scenario(
        id="openclaw_aicoin",
        title="OpenClaw·行情 ReAct",
        force_intent="aicoin",
        channel="web",
        question="btc 现在大概多少钱？一句话回答。",
        tags=["openclaw", "react", "aicoin"],
    ),
    Scenario(
        id="tavern_commit_user",
        title="酒馆·笔记回复",
        force_intent="commit_user",
        channel="internal",
        question="【笔记标题】周末测试\n\n【笔记正文】今天调试 agent，心情还行。",
        use_agent_entry=False,
        tags=["tavern", "optional_core", "lore", "commit_user"],
    ),
    Scenario(
        id="openclaw_bug",
        title="OpenClaw·Bug Ops",
        force_intent="bug",
        channel="web",
        question="首页偶尔 502，帮我用一句话说明你会怎么排查。",
        use_agent_entry=False,
        tags=["openclaw", "bug"],
    ),
]


def _run_memory_pipeline(sc: Scenario, *, skip: bool) -> tuple[bool, float, str]:
    if skip:
        return False, 0.0, "skipped"
    if sc.force_intent != "chat" or should_skip_memory_pipeline(sc.question):
        return False, 0.0, "skipped"
    t0 = time.perf_counter()
    try:
        get_user_memory().process_user_message(
            sc.question,
            user_id=sc.user_id,
            channel=sc.channel,
        )
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return True, ms, "ok"
    except Exception as exc:
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return False, ms, str(exc)[:200]


def _invoke_llm(system: str, question: str) -> tuple[str, float, str]:
    t0 = time.perf_counter()
    try:
        model = ChatModel()
        answer = model.invoke_messages_once(
            [
                SystemMessage(content=system),
                HumanMessage(content=question),
            ],
        )
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return answer, ms, "ok"
    except Exception as exc:
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return "", ms, str(exc)[:300]


def _run_via_agent_entry(sc: Scenario) -> dict[str, Any]:
    entry = get_agent_entry()
    session_id = f"test-{sc.id}-{uuid.uuid4().hex[:8]}"
    t0 = time.perf_counter()
    result: dict[str, Any] = {
        "handler": "agent_entry.run",
        "output_mode": None,
        "intent_resolved": sc.force_intent,
        "history_limit": 0,
    }
    try:
        reply = entry.run(
            question=sc.question,
            session_id=session_id,
            user_id=sc.user_id,
            channel=sc.channel,
            force_intent=sc.force_intent,
            access_token=sc.access_token,
            user_name="开发者",
            account="test@dev.local",
            user_role="admin",
            trace_id=f"test-{sc.id}",
            note_id=sc.note_id or "",
            limit=0,
        )
        result["output_mode"] = reply.output_mode
        result["intent_resolved"] = reply.intent
        if reply.output_mode == "once":
            result["llm_answer"] = reply.plain_text()
        else:
            chunks = []
            for line in reply.iter_sse():
                if line.startswith("data: ") and "[DONE]" not in line:
                    try:
                        payload = json.loads(line[6:].strip())
                        if payload.get("type") == "delta":
                            chunks.append(payload.get("content") or "")
                    except json.JSONDecodeError:
                        pass
            result["llm_answer"] = "".join(chunks).strip()
        result["llm_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        result["llm_status"] = "ok"
    except Exception as exc:
        result["llm_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        result["llm_status"] = "error"
        result["llm_answer"] = ""
        result["error"] = str(exc)[:400]
    return result


def run_scenario(
    sc: Scenario,
    *,
    live: bool,
    skip_memory: bool,
    include_system_prompt: bool,
) -> dict[str, Any]:
    ensure_env_loaded()
    total_t0 = time.perf_counter()

    ctx = trace_context_for_scenario(
        scenario_id=sc.id,
        intent=sc.force_intent,
        channel=sc.channel,
        question=sc.question,
        user_id=sc.user_id,
        user_logged_in=bool(sc.access_token),
    )

    # agent_entry 内 chat 会再跑记忆子图，测试侧不再重复调用
    mem_skip = skip_memory or (
        live and sc.use_agent_entry and sc.force_intent == "chat"
    )
    mem_ran, mem_ms, mem_status = _run_memory_pipeline(sc, skip=mem_skip)
    trace: AssembleTrace = trace_assemble(ctx)

    report: dict[str, Any] = {
        "scenario_id": sc.id,
        "title": sc.title,
        "tags": sc.tags,
        "force_intent": sc.force_intent,
        "channel": sc.channel,
        "question": sc.question,
        "mode": "live" if live else "assemble_only",
        "memory_pipeline": {
            "ran": mem_ran,
            "ms": mem_ms,
            "status": mem_status,
        },
        "assemble": trace_to_dict(trace, include_system_prompt=include_system_prompt),
        "system_prompt_chars": trace.system_chars,
        "openclaw_vs_tavern": {
            "openclaw": "permanent + channel + capabilities/*.md（能力清单）",
            "tavern": "optional core/*.md + lore YAML + Chroma recall",
            "openclaw_loaded": trace.openclaw_capabilities,
            "tavern_optional_core": trace.tavern_optional_core,
            "tavern_lore_injected": trace.tavern_lore_hit,
            "tavern_recall_injected": trace.tavern_recall_hit,
        },
    }

    if not live:
        report["llm_answer"] = "(仅拼装，未调 LLM)"
        report["llm_ms"] = 0
        report["llm_status"] = "skipped"
        report["llm_tokens_est"] = 0
        report["estimated_api_calls"] = 0
    elif sc.use_agent_entry and sc.force_intent in ("chat", "music", "aicoin"):
        agent_part = _run_via_agent_entry(sc)
        report["agent_entry"] = agent_part
        report["llm_answer"] = agent_part.get("llm_answer", "")
        report["llm_ms"] = agent_part.get("llm_ms", 0)
        report["llm_status"] = agent_part.get("llm_status", "")
        report["llm_tokens_est"] = estimate_tokens(report.get("llm_answer") or "")[0]
        if agent_part.get("error"):
            report["error"] = agent_part["error"]
        react_rounds = 6 if sc.force_intent in ("music", "aicoin", "bug") else 0
        report["estimated_api_calls"] = (
            (2 if sc.force_intent == "chat" and not should_skip_memory_pipeline(sc.question) else 0)
            + (1 + react_rounds if sc.force_intent in ("music", "aicoin") else 1)
        )
    else:
        if sc.force_intent == "commit_user":
            state = {
                "question": sc.question,
                "channel": sc.channel,
                "user_id": sc.user_id,
                "user_name": "开发者",
                "intent": "commit_user",
            }
            system = assemble_for_state(
                state,
                intent="commit_user",
                include_lore=True,
                user_message=sc.question,
            )
        elif sc.force_intent == "bug":
            state = {
                "question": sc.question,
                "channel": sc.channel,
                "user_id": sc.user_id,
                "intent": "bug",
            }
            system = assemble_for_state(state, intent="bug")
        else:
            system = trace.system_prompt

        ans, llm_ms, status = _invoke_llm(system, sc.question)
        report["llm_answer"] = ans
        report["llm_ms"] = llm_ms
        report["llm_status"] = status
        report["llm_tokens_est"] = estimate_tokens(ans)[0]
        report["handler"] = "ChatModel.invoke_messages_once"
        report["estimated_api_calls"] = 2 if sc.force_intent == "bug" else 1

    report["total_ms"] = round((time.perf_counter() - total_t0) * 1000, 2)
    return report


def _print_report(r: dict[str, Any]) -> None:
    print("\n" + "=" * 72)
    print(f"[{r['scenario_id']}] {r['title']}")
    print("=" * 72)
    a = r.get("assemble") or {}
    print(f"mode={r.get('mode')} system ~{a.get('system_tokens', 0)} tok · llm={r.get('llm_status')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="分场景 prompt 拼装测试（默认不调 LLM）",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="调用真实 LLM（默认仅拼装 prompt，0 token）",
    )
    parser.add_argument(
        "--live-all",
        action="store_true",
        help="对所有 8 场景调 LLM（含 ReAct，极易消耗百万级 token，慎用）",
    )
    parser.add_argument("--scenario", default="", help="只跑指定 scenario id")
    parser.add_argument(
        "--report-dir",
        default=str(ROOT / "reports"),
        help="HTML/JSON 报告目录",
    )
    parser.add_argument("--no-report", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--skip-memory-pipeline",
        action="store_true",
        help="跳过记忆摘要 LLM",
    )
    parser.add_argument(
        "--full-prompt-in-json",
        action="store_true",
        help="JSON 报告内写入完整 system 正文",
    )
    args = parser.parse_args()

    live = args.live or args.live_all
    if live:
        cfg = AgentConfig()
        if not chat_llm_configured(cfg):
            print(
                "错误: 未配置 DP_MODEL / DP_CHAT_API_KEY，无法 --live。\n"
                f"  DP_MODEL={cfg.chat_model_name!r} api_key={'有' if cfg.chat_api_key else '无'}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        if not embedding_configured(cfg):
            print(
                "提示: 未配置 EMBEDDING_*，recall 将跳过（不影响拼装报告）。"
                "参考 .env.example 填写 EMBEDDING_MODEL_NAME / API_KEY / BASE_URL。",
            )
    if args.live_all:
        warnings.warn(
            "【警告】--live-all 会对 music/aicoin/bug 跑 ReAct（每轮重复携带 tool 大 JSON），"
            "极易产生数百万 input token。建议改用: python scripts/test_prompt_scenarios.py "
            "或 --live --scenario openclaw_chat_web",
            stacklevel=1,
        )
        os.environ.setdefault("TEST_REACT_MAX_ROUNDS", "2")

    selected = list(SCENARIOS)
    if args.scenario:
        selected = [s for s in SCENARIOS if s.id == args.scenario]
        if not selected:
            print(f"未知 scenario: {args.scenario}", file=sys.stderr)
            print("可选:", ", ".join(s.id for s in SCENARIOS))
            raise SystemExit(1)
    elif live and not args.live_all:
        selected = [s for s in selected if s.allow_live]
        if not selected:
            print("无 allow_live 场景；请 --live-all 或 --scenario <id>", file=sys.stderr)
            raise SystemExit(1)

    try:
        preflight_assemble()
    except Exception as exc:
        print(f"预检失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    mode_label = "live-all" if args.live_all else ("live" if live else "assemble_only")
    print(f"开始 {len(selected)} 个场景（mode={mode_label}）…")
    if not live:
        print("提示: 当前不调 LLM，不消耗 API token。要冒烟对话请加 --live --scenario openclaw_chat_web")

    reports: list[dict[str, Any]] = []
    for i, sc in enumerate(selected, 1):
        print(f"  [{i}/{len(selected)}] {sc.id} …", flush=True)
        try:
            reports.append(
                run_scenario(
                    sc,
                    live=live,
                    skip_memory=args.skip_memory_pipeline,
                    include_system_prompt=args.full_prompt_in_json,
                )
            )
        except Exception as exc:
            reports.append(
                {
                    "scenario_id": sc.id,
                    "title": sc.title,
                    "error": str(exc)[:500],
                }
            )
        r = reports[-1]
        if args.verbose:
            _print_report(r)
        elif not r.get("error"):
            a = r.get("assemble") or {}
            print(
                f"       → {r.get('llm_status')} · system ~{a.get('system_tokens', '-')} tok "
                f"· {r.get('total_ms', 0)} ms"
            )
        else:
            print(f"       → ERR: {r.get('error', '')[:80]}")

    if not args.no_report:
        html_path, json_path = _load_report_writer()(
            reports,
            Path(args.report_dir),
            dry_run=not live,
        )
        print("\n报告已生成：")
        print(f"  HTML  {html_path.resolve()}")
        print(f"  JSON  {json_path.resolve()}")

    if live:
        est_in = sum((r.get("assemble") or {}).get("system_tokens", 0) for r in reports)
        print(f"\n[粗算] 仅 system 拼装约 {est_in} tokens；ReAct/记忆/多轮对话会再乘数倍，以控制台账单为准。")

    print(f"\n完成 {len(reports)} 个场景")


if __name__ == "__main__":
    main()

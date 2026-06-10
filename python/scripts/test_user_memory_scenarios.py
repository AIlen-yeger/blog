"""用户记忆测试：内置 5 个场景（滚动摘要 + 滑动窗口 + 可选 Chroma）。

在 python 目录、已配置 .env（DP_*、EMBEDDING_*）且已安装依赖时运行：

  python scripts/test_user_memory_scenarios.py
  python scripts/test_user_memory_scenarios.py --scenario multi_turn_experience
  python scripts/test_user_memory_scenarios.py --no-persist
  python scripts/test_user_memory_scenarios.py --max-turns 4 --scenario sliding_window

每个场景使用独立 test user_id，避免污染真实用户记忆。
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _bootstrap_env() -> argparse.Namespace:
    """在 import server/config 之前解析参数并设置环境变量。"""
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--no-persist", action="store_true")
    pre_args, _ = pre.parse_known_args()
    if pre_args.no_persist:
        os.environ["CHROMA_MEMORY_ENABLED"] = "false"
    return pre_args


def _import_deps() -> None:
    try:
        import chromadb  # noqa: F401
        import langchain_openai  # noqa: F401
    except ModuleNotFoundError as exc:
        print(
            "缺少依赖:\n  pip install -r requirements.txt\n"
            f"原始错误: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


@dataclass
class Scenario:
    key: str
    title: str
    user_id: str
    messages: list[str]
    # 人工期望，便于对照输出
    expect: str
    max_turns: int = 8


# 固定 5 个场景：一句 commit、多轮经历、偏好、话题切换、滑动窗口
SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        key="one_shot_commit",
        title="一句话讲完经历 → 应 commit",
        user_id="test_one_shot",
        messages=[
            "昨天我走在路上不小心被路过的车溅了一身水，气死我了",
        ],
        expect="首条即 commit，committed_memory 非空，episode 清空",
    ),
    Scenario(
        key="multi_turn_experience",
        title="多轮补全同一经历 → continue 再 commit",
        user_id="test_multi_turn",
        messages=[
            "昨天我看天气挺不错，想出去走走",
            "刚在路上走着呢，突然来了一辆车加速驶过",
            "然后溅我一身水，我真是服了",
        ],
        expect="前两轮 continue 且 running_summary 合并；第三轮 commit",
    ),
    Scenario(
        key="preference_commit",
        title="偏好/厌恶 → commit",
        user_id="test_preference",
        messages=[
            "我跟你说啊，我超级讨厌吃香菜，闻到就想吐",
            "以后点菜记得帮我备注不要香菜",
        ],
        expect="偏好说清后 commit，tags 含用户偏好",
    ),
    Scenario(
        key="topic_shift",
        title="旧话题结束后聊无关新内容",
        user_id="test_topic_shift",
        messages=[
            "昨天散步被车溅湿了，气了一天",
            "对了，你平时听播客吗？有推荐吗，我喜欢科技类的",
        ],
        expect="第一条 commit；第二条可能 commit 旧摘要或 continue 新话题",
    ),
    Scenario(
        key="sliding_window",
        title="滑动窗口：超过 max_turns 强制 commit",
        user_id="test_sliding",
        messages=[
            "第1句：我在学 Vue",
            "第2句：组件写得还行",
            "第3句：路由有点懵",
            "第4句：Pinia 刚上手",
            "第5句：准备做个小项目",
            "第6句：打算下周部署",
        ],
        max_turns=5,
        expect="满 5 轮仍 continue 时，第 6 条应被 force_commit",
    ),
)


def _print_banner(text: str) -> None:
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


def _print_step(i: int, msg: str, result) -> None:
    ep_turns = "—"
    print(f"\n--- 第 {i} 条用户消息 ---")
    print(f"输入: {msg}")
    print(f"action: {result.action}")
    print(f"episode_complete: {result.episode_complete}  topic_shift: {result.topic_shift}")
    print(f"memory_tags: {result.memory_tags}")
    print(f"running_summary: {result.running_summary or '（空）'}")
    if result.committed_memory:
        print(f"committed_memory: {result.committed_memory}")
    if result.memory_id:
        print(f"memory_id (已入库): {result.memory_id}")
    if result.extra_summary:
        print(f"extra_summary: {result.extra_summary}")


def run_scenario(
    sc: Scenario,
    *,
    auto_persist: bool,
    recall_query: str | None,
) -> None:
    from server.embedding.embedding_user_memory import UserMemory

    mem = UserMemory(max_turns=sc.max_turns, auto_persist=auto_persist)
    _print_banner(f"场景 [{sc.key}] {sc.title}")
    print(f"user_id={sc.user_id}  max_turns={sc.max_turns}")
    print(f"期望: {sc.expect}")

    for i, msg in enumerate(sc.messages, 1):
        result = mem.process_user_message(msg, user_id=sc.user_id, channel="test")
        _print_step(i, msg, result)
        episode = mem.get_episode(sc.user_id)
        print(f"buffer turns 数: {len(episode.turns)}")
        if episode.turns:
            print(f"buffer 末条: {episode.turns[-1][:60]}...")

    if auto_persist and mem.memory_count(sc.user_id) > 0:
        print(f"\nChroma 本场景条数: {mem.memory_count(sc.user_id)}")

    q = recall_query or (sc.messages[-1] if sc.messages else "")
    if auto_persist and q.strip():
        block = mem.format_recall_for_prompt(sc.user_id, q, top_k=3, channel="test")
        if block:
            print("\n--- recall（用最后一条或指定 query）---")
            print(block)
        else:
            print("\n--- recall: 无命中 ---")


def main() -> None:
    _bootstrap_env()
    sys.path.insert(0, str(ROOT))
    _import_deps()

    parser = argparse.ArgumentParser(description="用户记忆多场景测试")
    parser.add_argument(
        "--scenario",
        default="all",
        help="场景 key 或 all（默认跑全部 5 个）",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="不写入 Chroma（只测摘要与滑动窗口）",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=0,
        help="覆盖 sliding_window 场景的 max_turns（0=用场景默认值）",
    )
    parser.add_argument("--recall-query", default="", help="覆盖 recall 用的 query")
    args = parser.parse_args()

    selected = list(SCENARIOS)
    if args.scenario != "all":
        selected = [s for s in SCENARIOS if s.key == args.scenario]
        if not selected:
            keys = ", ".join(s.key for s in SCENARIOS)
            print(f"未知场景: {args.scenario}\n可选: {keys}", file=sys.stderr)
            raise SystemExit(2)

    auto_persist = not args.no_persist
    recall_q = args.recall_query.strip() or None

    print("用户记忆测试（5 个内置场景）")
    print(f"持久化: {'开 (Chroma+embed)' if auto_persist else '关 (--no-persist)'}")
    print(f"场景数: {len(selected)}")

    for sc in selected:
        if args.max_turns > 0 and sc.key == "sliding_window":
            sc = Scenario(
                key=sc.key,
                title=sc.title,
                user_id=sc.user_id,
                messages=sc.messages,
                max_turns=args.max_turns,
                expect=sc.expect,
            )
        try:
            run_scenario(sc, auto_persist=auto_persist, recall_query=recall_q)
        except Exception as exc:
            print(f"\n[FAIL] 场景 {sc.key} 异常: {exc}", file=sys.stderr)
            raise

    print("\n" + "=" * 72)
    print("全部场景跑完")
    print("=" * 72)
    print(
        "\n说明: action=continue 表示仍在滑动窗口内合并;"
        " commit/split 会产出 committed_memory;"
        " sliding_window 在第 max_turns+1 条会 force_commit。"
    )


if __name__ == "__main__":
    main()

"""统计 chat 路径 system 提示词字符数与 token 估算。

  python scripts/count_chat_prompt_tokens.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.prompt_skills import build_system_prompt


def estimate_tokens(text: str) -> tuple[int, str]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        n = len(enc.encode(text))
        return n, "tiktoken cl100k_base"
    except Exception:
        # 中文为主：约 1.6～2 字/token；含英文 markdown 取折中
        chars = len(text)
        low = chars // 2
        high = int(chars / 1.5)
        return (low + high) // 2, f"启发式 (~{chars} 字 ÷ 1.5～2)"


def main() -> None:
    from server.skills_server.prompt_assembler import PromptAssembler, PromptContext

    asm = PromptAssembler()
    for ch in ("web", "qq"):
        lean = build_system_prompt(intent="chat", channel=ch, user_message="你好")
        full = asm.build_chat_system(
            PromptContext(intent="chat", channel=ch, user_message="你好", user_id=0)
        )
        for label, text in (
            ("skills栈(无lore/recall)", lean),
            ("chat入口(含lore/recall)", full),
        ):
            chars = len(text)
            tokens, method = estimate_tokens(text)
            print(f"\n=== channel={ch} {label} ===")
            print(f"字符数: {chars}")
            print(f"估算 tokens ({method}): ~{tokens}")

        music = build_system_prompt(intent="music", channel=ch, user_logged_in=True)
        print(f"\n=== channel={ch} music(minimal酒馆) ~{estimate_tokens(music)[0]} tokens ===")

    print("\n完整对比（含 lore/recall 分层）: python scripts/compare_capability_tokens.py --with-lore-recall")
    print("\n--- 单轮 chat 总输入（除 system 外，默认 history_limit=10）---")
    print("  + 用户本条（例 10 字）~5～15 tokens")
    print("  + Redis 历史最多 10 轮 × (用户+助手)，视会话长度 0～数千 tokens")
    print("  + 若先走 judge：另计 judge.md 一轮（通常 <500 tokens）")
    print("输出：助手回复一般 20～150 tokens（QQ 短句更少）")


if __name__ == "__main__":
    main()

"""按保留策略清理 Agent 轮转日志（CLI；进程内定时见 utils/agent_log_scheduler.py）。

用法:
  python scripts/prune_agent_logs.py
  python scripts/prune_agent_logs.py --dry-run

保留策略（可通过 .env 覆盖）:
  summary.jsonl.*     AGENT_LOG_SUMMARY_RETAIN_DAYS  默认 90
  error.jsonl.*       AGENT_LOG_ERROR_RETAIN_DAYS    默认 180（供后续 bug agent）
  trace / intent 等   AGENT_LOG_TRACE_RETAIN_DAYS    默认 14
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from config.config import ensure_env_loaded

    ensure_env_loaded()
except ImportError:
    pass

from utils.agent_log_config import (  # noqa: E402
    ERROR_RETAIN_DAYS,
    INTENT_RETAIN_DAYS,
    SUMMARY_RETAIN_DAYS,
    TRACE_RETAIN_DAYS,
    resolve_log_dir,
)
from utils.agent_log_prune import run_agent_log_prune  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune rotated agent JSONL logs")
    parser.add_argument(
        "--log-dir",
        default=None,
        help="日志目录，默认 AGENT_LOG_DIR 或 log/agent.log",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将删除的文件，不实际删除",
    )
    args = parser.parse_args()

    log_dir = resolve_log_dir(args.log_dir)
    print(f"log_dir={log_dir}")
    print(
        "retention_days: "
        f"summary={SUMMARY_RETAIN_DAYS}, error={ERROR_RETAIN_DAYS}, "
        f"trace={TRACE_RETAIN_DAYS}, intent={INTENT_RETAIN_DAYS}"
    )

    actions = run_agent_log_prune(log_dir=args.log_dir, dry_run=args.dry_run)
    if not actions:
        print("nothing to prune")
    else:
        for line in actions:
            print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

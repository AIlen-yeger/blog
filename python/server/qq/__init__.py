"""QQ 渠道包。

`bridge` 不在包加载时导入，避免 agent_entry → aicoin_route → server.qq → bridge 循环依赖。
请使用：`from server.qq.bridge import handle_qq_private_message_sync`
"""

from server.qq.market_pipeline import env_two_phase_enabled, run_aicoin_qq_two_phase
from server.qq.reply_format import (
    build_qq_aicoin_system_append,
    format_qq_market_reply,
    qq_aicoin_max_rounds,
)

__all__ = [
    "env_two_phase_enabled",
    "run_aicoin_qq_two_phase",
    "build_qq_aicoin_system_append",
    "format_qq_market_reply",
    "qq_aicoin_max_rounds",
    "handle_qq_private_message_sync",
]


def __getattr__(name: str):
    if name == "handle_qq_private_message_sync":
        from server.qq.bridge import handle_qq_private_message_sync

        return handle_qq_private_message_sync
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""提示词分层常量（避免 prompt_skills ↔ openclaw 循环导入）。"""

from __future__ import annotations

# ReAct / 能力路由：酒馆 minimal（锚点+渠道）；OpenClaw 带能力块
CAPABILITY_INTENTS = frozenset({"music", "aicoin", "bug"})

# QQ 闲聊：锚点+渠道+极简 OpenClaw；不叠酒馆常驻 / lore / recall / optional
CHAT_LEAN_CHANNELS = frozenset({"qq"})

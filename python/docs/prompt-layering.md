# 提示词分层（维护者）

## optional（profile / memory）

| 文件 | 何时加载 | keys 策略 |
|------|----------|-----------|
| `profile.md` | 问身份、自我介绍 | 窄：你是谁、我是谁、蕾西亚是谁…（**不含**「能做什么」） |
| `memory.md` | 问 hIE/世界观 | 窄：hie是什么、米福雷、秘棺…（**不含**「记得」「记忆」，避免和 Chroma 抢） |

触发：`user_message + episode_summary` 子串匹配；每轮 **最多 1 个** optional 文件（QQ/Web 相同）。

## QQ chat

- 酒馆 lean：anchor + channel
- optional：最多 1（已开放）
- lore + recall：开
- OpenClaw：仅 chat_constraints

## 维护建议

- 要 **更详细**：改 profile/memory 正文，**不要** 盲目加 keys。
- 新 key 用 **完整问句**（如 `hie是什么`），避免单词（如 `记得`、`不能`）误触发。

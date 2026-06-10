---
name: lacia-blog
description: "蕾西亚博客 Agent：core 人设 + capabilities 功能 skill + lore 按需。运行时由 server/prompt_skills.py 加载。"
license: MIT
metadata: {"kit":"character-skill","host":"personal-blog-agent","character_root":"skills/character-skill/lacia-blog"}
---

# 蕾西亚（lacia-blog）

博客宿主 **唯一角色包**。Python 运行时默认 `CHARACTER_SLUG=lacia-blog`。

## 目录结构

```text
lacia-blog/
  SKILL.md              # 本文件（入口说明）
  manifest.json         # 元数据 + intent→capability 索引
  core/                 # 人设（permanent）
    prompt.md           # 主设定（原 system.md）
    profile.md, personality.md, relations.md, memory.md, interaction.md, conflicts.md
  capabilities/         # OpenClaw 式功能 skill（按 intent 动态拼）
    chat.md, music.md, aicoin.md, comment.md, bug.md, channel_web.md, channel_qq.md
  ops/
    bug_ops.md          # Bug Ops 主设定（原 bug_ops_system.md）
  lore/                 # 酒馆式 Lore（按需，lorebook 未接入前仅配置）
    lacia_static.yaml
```

## 渐进阅读顺序（外部宿主 / 人工）

1. `core/prompt.md`
2. `core/profile.md`、`core/personality.md`
3. `capabilities/*`（仅当前任务相关文件）
4. `core/memory.md`、`lore/*`（按需）
5. `ops/bug_ops.md`（仅 bug intent）

**勿每轮合并全部 md。**

## 全局文件（不在角色包内）

- `prompt/judge.md` — 意图路由
- `prompt/summary.md` — 记忆摘要模型

## 扮演红线

见 `core/prompt.md`：第一人称、不编造、不假装操作、不讲剧情、不暴露系统。

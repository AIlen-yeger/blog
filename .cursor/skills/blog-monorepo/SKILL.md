---
name: blog-monorepo
description: >-
  个人博客全栈 monorepo（frontend + backend + python agent）架构与联调。
  在修改跨端功能、部署、环境变量、agentReply 链路、蕾西亚桌宠或不确定改哪一层时使用。
---

# 个人博客 Monorepo

## 仓库地图

```
G:\Projects\blog\
├── frontend/     Vue 3 + Vite（端口 5173）
├── backend/      Spring Boot（8080，前缀 /v1）
└── python/       FastAPI Agent（8000）
```

## 典型数据流

### 桌宠对话

```
浏览器 → POST /api/agent/chat (SSE)
       → Java AgentController
       → POST Python /ai/chat (snake_case)
       → SSE 透传回前端
```

### 笔记自动回复

```
POST /v1/notes (+ agentSessionId)
  → Java AgentNoteCommentService
  → POST Python /ai/internal/note-comment
  → Python 生成后 POST /agent/ops/notes/{id}/agent-reply
  → 前端轮询 GET /notes/{id} 读 agentReply / agentReplyStatus
```

## 环境变量速查

| 层 | 关键变量 |
|----|----------|
| 前端 | `VITE_API_BASE`, `VITE_USE_MOCK`, `VITE_AGENT_CHAT_URL` |
| 后端 | `app.agent.base-url`, `app.agent.ops-token`, JWT secret |
| Python | `BLOG_API_BASE`, `AGENT_OPS_TOKEN`, `DP_*` |

## 改功能时的检查清单

1. 字段是否三端一致（camelCase vs snake_case 边界在 Java→Python 聊天）
2. 公开 GET 是否仍在 `PublicApiPaths`
3. Agent 展示是否受 `useAgentReplySettings` / `AgentReplyProperties` 控制
4. 人设 prompt 只改 `python/skills/`，不塞进 Vue 组件

## 延伸阅读

- API 明细：`blog-api-contract` skill 与同目录 `reference.md`
- 前端文档：`frontend/docs/API.md`（以 `src/api/*.ts` 为准）

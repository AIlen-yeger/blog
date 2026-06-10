---
name: blog-api-contract
description: >-
  个人博客三端 API 契约：REST 信封、鉴权、主要端点、agentReply 字段、Java↔Python 体格式。
  在新增/修改接口、对接前后端、调试 401/SSE/agentReply 时使用。
---

# 博客 API 契约

## 统一信封（前端 ↔ Java）

```json
{ "code": 0, "message": "ok", "data": { } }
```

- 成功：`code === 0`
- 失败：`data: null`，业务码如 `40101`
- 分页 `data`：`{ list, total, page, pageSize }`

**路径**：生产 `http://host:8080/v1/...`；开发前端 `/api/...`（代理到 `/v1`）

## 鉴权

| 场景 | 方式 |
|------|------|
| 用户 API | `Authorization: Bearer <JWT>` |
| Python ↔ Java 运维 | `X-Ops-Token`（两边 token 必须相同） |
| 公开只读 | 部分 `GET` 无需 JWT（见 `PublicApiPaths`） |

## 核心 REST 分组

| 域 | 方法 | 路径（相对 /v1） |
|----|------|------------------|
| 认证 | POST | `/auth/login`, `/auth/register/*` |
| 资料 | GET/PUT | `/profile`, `/profile/public`, `/profile/avatar` |
| 笔记 | CRUD | `/notes`, `/notes/{id}`, `/notes/{id}/pin`, `/notes/{id}/views` |
| 生活 | CRUD | `/life`, `/life/{id}`, ... |
| 专题/搜索 | GET | `/topics`, `/timeline`, `/search`, `/meta/*` |
| 音乐 | GET/POST | `/music/site-owner`, `/music/me`, `/music/tracks` |
| 上传 | POST | `/uploads/images` |
| 桌宠 | POST SSE | `/agent/chat` |
| Agent 回调 | POST | `/agent/ops/notes/{noteId}/agent-reply` |

完整列表见 [reference.md](reference.md)。

## 关键字段（camelCase）

| 字段 | 说明 |
|------|------|
| `agentReply` | 蕾西亚回复正文 |
| `agentReplyStatus` | `none \| pending \| running \| done \| failed` |
| `agentSessionId` | 发布笔记时传入，关联桌宠会话 |
| `topicId`, `viewCount`, `qqSongId` | 各域 DTO 标准 camelCase |

## Java → Python 体格式

| 接口 | JSON 风格 |
|------|-----------|
| `POST /ai/chat` | **snake_case**：`session_id`, `user_id`, `user_name`, ... |
| `POST /ai/internal/note-comment` | **camelCase**：`noteId`, `jobId`, `sessionId`, ... |

## SSE（桌宠）

- 不走 `{code,message,data}` 信封
- 事件：`meta`（intent）、`delta`/`message`（content）、`[DONE]`

## 实现入口

- 前端：`frontend/src/api/http.ts`, `blog.ts`, `agentChat.ts`
- 后端：`backend/.../controller/*.java`, `ApiResponse.java`
- Python：`python/route/app.py`

详细端点表见 [reference.md](reference.md)。

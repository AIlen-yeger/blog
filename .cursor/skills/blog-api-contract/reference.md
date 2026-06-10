# API 端点参考（扫描自源码）

## 前端 API 模块

| 文件 | 职责 |
|------|------|
| `frontend/src/api/http.ts` | `request()`, `getApiBase()`, `ApiError` |
| `frontend/src/api/auth.ts` | 登录、注册验证码 |
| `frontend/src/api/blog.ts` | profile, notes, life, topics, upload |
| `frontend/src/api/music.ts` | 音乐曲库 |
| `frontend/src/api/agentChat.ts` | 桌宠 SSE |
| `frontend/src/api/checkIn.ts` | 签到 |
| `frontend/src/api/views.ts` | 浏览计数 |

## Java Controllers（前缀 /v1）

| Controller | 路径 |
|------------|------|
| AuthController | `/auth` |
| ProfileController | `/profile` |
| NoteController | `/notes` |
| LifeController | `/life` |
| TopicController | `/topics` |
| TimelineController | `/timeline` |
| SearchController | `/search` |
| MetaController | `/meta` |
| CheckInController | `/check-ins` |
| MusicTrackController | `/music` |
| UploadController | `/uploads` |
| AgentController | `/agent/chat` |
| AgentOpsController | `/agent/ops` |
| AgentMusicController | `/agent/music`（Agent 工具用） |

## Python 路由

| 方法 | 路径 |
|------|------|
| GET | `/health` |
| POST | `/ai/chat` |
| POST | `/ai/internal/note-comment` |
| POST | `/ai/ops/bug-scan`, `/ai/ops/btc-daily-test`, `/ai/ops/napcat-test` |

## 错误码示例

| code | 含义 |
|------|------|
| 0 | 成功 |
| 40101 | 未授权（`AUTH_CODE_UNAUTHORIZED`） |

## Vite 代理（开发）

```ts
// vite.config.ts
'/api' → 'http://localhost:8080/v1'（rewrite 去掉 /api）
'/v1/uploads' → 静态上传直连
```

## 笔记 Agent 回复链路

```
NoteWriteRequest.agentSessionId
  → AgentNoteCommentService
  → Python note-comment
  → save_note_agent_reply → AgentOpsController
  → NoteDto.agentReply + agentReplyStatus
  → 前端 useNoteAgentReplyPoll / GET /notes/{id}
```

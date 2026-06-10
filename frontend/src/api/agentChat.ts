import { ApiError, getApiBase } from '@/api/http'
import { toUserErrorMessage } from '@/utils/userErrorMessage'
import { getAuthToken, hasValidSession } from '@/composables/useSession'
import {
  buildAgentChatPayload,
  type AgentAttachmentPayload,
} from '@/utils/agentPayload'

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

function useMockAgent(): boolean {
  const flag = import.meta.env.VITE_AGENT_USE_MOCK
  if (flag === 'false') return false
  if (flag === 'true') return true
  return !import.meta.env.VITE_AGENT_CHAT_URL
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

async function mockStreamReply(
  userText: string,
  onChunk: (piece: string) => void,
  signal?: AbortSignal,
) {
  const isRich =
    /搜索|检索|查询|资料|笔记|总结|分析|列表|推荐/.test(userText) ||
    userText.length > 40

  const reply = isRich
    ? `我帮你整理了一下：\n\n1. 学习笔记可在左侧「N O T E S」按专题筛选浏览。\n2. 生活记录在「L I F E」区块，支持配图发布。\n3. 关于页可播放本地音乐，粒子会随响度变化。\n\n需要我继续查某一篇具体内容吗？`
    : `嗯嗯，我在呢～今天想聊聊学习笔记，还是随便闲聊呀？`

  for (const ch of reply) {
    if (signal?.aborted) return
    onChunk(ch)
    await delay(16 + Math.floor(Math.random() * 24))
  }
}

export interface PublishNotePreviewData {
  title: string
  excerpt: string
  topicTitle: string
  contentPreview: string
  content: string
  attachmentNames?: string
  sessionId?: string
}

export interface AgentChatStreamOptions {
  onMeta?: (meta: { intent?: string }) => void
  onActionPreview?: (preview: { action: string; data: PublishNotePreviewData }) => void
}

function handleSsePayload(
  payload: unknown,
  onChunk: (piece: string) => void,
  options?: AgentChatStreamOptions,
) {
  const onMeta = options?.onMeta
  const onActionPreview = options?.onActionPreview
  if (!payload || typeof payload !== 'object') return
  const row = payload as Record<string, unknown>
  if (typeof row.code === 'number' && row.code !== 0) {
    throw new Error(String(row.message ?? 'Agent 返回错误'))
  }
  const type = String(row.type ?? '')
  if (type === 'meta') {
    const intent = typeof row.intent === 'string' ? row.intent : undefined
    onMeta?.({ intent })
    return
  }
  if (type === 'action_preview') {
    const action = typeof row.action === 'string' ? row.action : ''
    const data = row.data as PublishNotePreviewData | undefined
    if (action && data && typeof data.title === 'string') {
      onActionPreview?.({ action, data })
    }
    return
  }
  const piece = extractPiece(payload)
  if (piece) onChunk(piece)
}

function parseSseChunk(
  buffer: string,
  onChunk: (piece: string) => void,
  options?: AgentChatStreamOptions,
): string {
  let rest = buffer
  const lines = rest.split('\n')
  rest = lines.pop() ?? ''
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    if (trimmed.startsWith('data:')) {
      const data = trimmed.slice(5).trim()
      if (!data || data === '[DONE]') continue
      try {
        handleSsePayload(JSON.parse(data), onChunk, options)
      } catch (e) {
        if (e instanceof Error && e.message !== 'Agent 返回错误') {
          onChunk(data)
        } else {
          throw e
        }
      }
      continue
    }
    try {
      handleSsePayload(JSON.parse(trimmed), onChunk, options)
    } catch {
      /* 忽略非 JSON 行 */
    }
  }
  return rest
}

function resolveAgentUrl(): string {
  const configured = import.meta.env.VITE_AGENT_CHAT_URL as string | undefined
  if (configured?.startsWith('http')) return configured
  if (configured?.startsWith('/')) return configured
  return `${getApiBase().replace(/\/$/, '')}/agent/chat`
}

function extractPiece(payload: unknown): string {
  if (!payload || typeof payload !== 'object') return ''
  const row = payload as Record<string, unknown>
  if (typeof row.code === 'number' && row.code !== 0) {
    throw new Error(String(row.message ?? 'Agent 返回错误'))
  }
  const type = String(row.type ?? '')
  if (type === 'meta') return ''
  const piece = row.content ?? row.delta ?? row.text ?? ''
  return typeof piece === 'string' ? piece : ''
}

export interface AgentChatStreamContext extends AgentChatStreamOptions {
  sessionId?: string
  attachments?: AgentAttachmentPayload[]
}

export async function streamAgentChat(
  messages: ChatTurn[],
  onChunk: (piece: string) => void,
  signal?: AbortSignal,
  options?: AgentChatStreamContext,
): Promise<void> {
  const lastUser = [...messages].reverse().find((m) => m.role === 'user')
  const question = lastUser?.content?.trim() ?? ''

  if (useMockAgent()) {
    await mockStreamReply(question, onChunk, signal)
    return
  }

  if (!question) {
    throw new Error('请输入内容')
  }

  if (!hasValidSession()) {
    throw new Error('请先登录后再使用助手')
  }

  const token = getAuthToken()
  if (!token) {
    throw new Error('登录状态已失效，请重新登录')
  }

  const url = resolveAgentUrl()
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(
      buildAgentChatPayload(question, options?.sessionId, options?.attachments),
    ),
    signal,
  })

  if (!res.ok) {
    let errText = await res.text().catch(() => '')
    try {
      const json = JSON.parse(errText) as { message?: string }
      if (json.message) errText = json.message
    } catch {
      /* keep raw */
    }
    throw new Error(
      toUserErrorMessage(errText || new ApiError(res.status, ''), '助手暂时不可用，请稍后再试'),
    )
  }

  const ctype = res.headers.get('content-type') ?? ''
  if (!ctype.includes('text/event-stream') || !res.body) {
    const json = (await res.json()) as Record<string, unknown>
    handleSsePayload(json, onChunk, options)
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let pending = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    pending += decoder.decode(value, { stream: true })
    pending = parseSseChunk(pending, (piece) => {
      if (piece) onChunk(piece)
    }, options)
  }
}

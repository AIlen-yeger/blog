import { genId } from '@/utils/id'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: number
  attachments?: ChatAttachmentMeta[]
}

export interface ChatAttachmentMeta {
  id: string
  name: string
  type: 'image' | 'text' | 'document'
  url?: string
  mime?: string
}

export interface AgentChatSession {
  sessionId: string
  title: string
  messages: ChatMessage[]
  createdAt: number
  updatedAt: number
}

const SESSIONS_KEY = 'kohaku-agent-sessions'
const ACTIVE_KEY = 'kohaku-agent-active-session'
const LEGACY_HISTORY_KEY = 'kohaku-agent-chat-history'
const MAX_SESSIONS = 30
const MAX_MESSAGES = 80

function normalizeSession(raw: unknown): AgentChatSession | null {
  if (!raw || typeof raw !== 'object') return null
  const row = raw as Record<string, unknown>
  const sessionId =
    typeof row.sessionId === 'string'
      ? row.sessionId
      : typeof row.id === 'string'
        ? row.id
        : typeof row.backendSessionId === 'string'
          ? row.backendSessionId
          : ''
  if (!sessionId) return null
  const messages = Array.isArray(row.messages)
    ? row.messages.filter(
        (m): m is ChatMessage =>
          !!m &&
          typeof m === 'object' &&
          (m.role === 'user' || m.role === 'assistant') &&
          typeof m.content === 'string' &&
          typeof m.id === 'string',
      )
    : []
  return {
    sessionId,
    title: typeof row.title === 'string' ? row.title : '新对话',
    messages: messages.slice(-MAX_MESSAGES),
    createdAt: typeof row.createdAt === 'number' ? row.createdAt : Date.now(),
    updatedAt: typeof row.updatedAt === 'number' ? row.updatedAt : Date.now(),
  }
}

function loadRawSessions(): AgentChatSession[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    if (!raw) return migrateLegacyHistory()
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed) || parsed.length === 0) return migrateLegacyHistory()
    return parsed
      .map(normalizeSession)
      .filter((s): s is AgentChatSession => s !== null)
      .slice(0, MAX_SESSIONS)
  } catch {
    return migrateLegacyHistory()
  }
}

function migrateLegacyHistory(): AgentChatSession[] {
  try {
    const raw = localStorage.getItem(LEGACY_HISTORY_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed) || parsed.length === 0) return []
    const messages = parsed
      .filter(
        (m): m is ChatMessage =>
          !!m &&
          typeof m === 'object' &&
          (m.role === 'user' || m.role === 'assistant') &&
          typeof m.content === 'string' &&
          typeof m.id === 'string',
      )
      .slice(-MAX_MESSAGES)
    if (messages.length === 0) return []
    const firstUser = messages.find((m) => m.role === 'user')
    const title = firstUser
      ? firstUser.content.trim().slice(0, 24) || '对话'
      : '对话'
    const session: AgentChatSession = {
      sessionId: genId('sess'),
      title,
      messages,
      createdAt: messages[0]?.createdAt ?? Date.now(),
      updatedAt: messages[messages.length - 1]?.createdAt ?? Date.now(),
    }
    saveSessions([session])
    setActiveSessionId(session.sessionId)
    localStorage.removeItem(LEGACY_HISTORY_KEY)
    return [session]
  } catch {
    return []
  }
}

function saveSessions(sessions: AgentChatSession[]) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.slice(0, MAX_SESSIONS)))
  } catch {
    /* ignore quota */
  }
}

export function loadAgentSessions(): AgentChatSession[] {
  return loadRawSessions()
}

export function getActiveSessionId(): string | null {
  try {
    const id = localStorage.getItem(ACTIVE_KEY)
    if (id) return id
  } catch {
    /* ignore */
  }
  const sessions = loadRawSessions()
  return sessions[0]?.sessionId ?? null
}

export function setActiveSessionId(id: string) {
  try {
    localStorage.setItem(ACTIVE_KEY, id)
  } catch {
    /* ignore */
  }
}

/** 登录/登出时丢弃访客本地 active session，避免与后端会话混用 */
export function clearActiveSessionId() {
  try {
    localStorage.removeItem(ACTIVE_KEY)
  } catch {
    /* ignore */
  }
}

export function getActiveSession(): AgentChatSession | null {
  const sessions = loadRawSessions()
  const activeId = getActiveSessionId()
  return sessions.find((s) => s.sessionId === activeId) ?? sessions[0] ?? null
}

export function createLocalAgentSession(title = '新对话'): AgentChatSession {
  const session: AgentChatSession = {
    sessionId: genId('sess'),
    title,
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  }
  const sessions = [session, ...loadRawSessions()].slice(0, MAX_SESSIONS)
  saveSessions(sessions)
  setActiveSessionId(session.sessionId)
  return session
}

export function upsertLocalSession(session: AgentChatSession) {
  const sessions = loadRawSessions()
  const idx = sessions.findIndex((s) => s.sessionId === session.sessionId)
  const trimmed: AgentChatSession = {
    ...session,
    messages: session.messages.slice(-MAX_MESSAGES),
    updatedAt: Date.now(),
  }
  if (idx >= 0) {
    sessions[idx] = trimmed
  } else {
    sessions.unshift(trimmed)
  }
  sessions.sort((a, b) => b.updatedAt - a.updatedAt)
  saveSessions(sessions)
}

export function deleteLocalAgentSession(sessionId: string) {
  const sessions = loadRawSessions().filter((s) => s.sessionId !== sessionId)
  saveSessions(sessions)
  if (getActiveSessionId() === sessionId) {
    setActiveSessionId(sessions[0]?.sessionId ?? '')
  }
}

export function ensureLocalDefaultSession(): AgentChatSession {
  const existing = getActiveSession()
  if (existing) return existing
  return createLocalAgentSession()
}

export function replaceLocalSessions(sessions: AgentChatSession[]) {
  saveSessions(sessions)
}

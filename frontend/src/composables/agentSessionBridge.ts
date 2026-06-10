import { ApiError } from '@/api/http'
import {
  createAgentSessionRemote,
  fetchAgentSessions,
  fetchSessionMessages,
} from '@/api/agentSessions'
import { hasValidSession } from '@/composables/useSession'
import type { ChatMessage } from '@/utils/agentSessionsStorage'
import {
  clearActiveSessionId,
  createLocalAgentSession,
  ensureLocalDefaultSession,
  getActiveSessionId,
  setActiveSessionId,
} from '@/utils/agentSessionsStorage'

async function isRemoteSessionValid(sessionId: string): Promise<boolean> {
  try {
    const rows = await fetchAgentSessions()
    return rows.some((s) => s.sessionId === sessionId)
  } catch {
    return false
  }
}

export async function ensureAgentSessionId(): Promise<string> {
  if (!hasValidSession()) {
    return ensureLocalDefaultSession().sessionId
  }
  const existing = getActiveSessionId()
  if (existing && (await isRemoteSessionValid(existing))) {
    return existing
  }
  if (existing) {
    clearActiveSessionId()
  }
  const created = await createAgentSessionRemote()
  setActiveSessionId(created.sessionId)
  return created.sessionId
}

/** 与后端 ErrorCode.AGENT_SESSION_NOT_FOUND 对齐 */
export const AGENT_SESSION_NOT_FOUND = 40405

export async function recoverStaleAgentSession(): Promise<string> {
  const created = await createAgentSessionRemote()
  setActiveSessionId(created.sessionId)
  return created.sessionId
}

export async function loadServerMessages(sessionId: string): Promise<ChatMessage[]> {
  try {
    const rows = await fetchSessionMessages(sessionId)
    return rows.map((row) => ({
      id: String(row.id),
      role: row.role,
      content: row.content,
      createdAt: row.createdAt,
    }))
  } catch (e) {
    const active = getActiveSessionId()
    if (
      e instanceof ApiError &&
      e.code === AGENT_SESSION_NOT_FOUND &&
      active === sessionId
    ) {
      await recoverStaleAgentSession()
      return []
    }
    throw e
  }
}

export function createGuestSessionId(): string {
  return createLocalAgentSession().sessionId
}

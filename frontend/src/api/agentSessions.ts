import { del, get, patch, post } from '@/api/http'

export interface AgentSessionRecord {
  sessionId: string
  title: string
  createdAt: number
  updatedAt: number
}

export interface AgentMessageRecord {
  id: number
  role: 'user' | 'assistant'
  content: string
  createdAt: number
}

export function fetchAgentSessions(): Promise<AgentSessionRecord[]> {
  return get<AgentSessionRecord[]>('/agent/sessions')
}

export function createAgentSessionRemote(): Promise<AgentSessionRecord> {
  return post<AgentSessionRecord>('/agent/sessions', {})
}

export function fetchSessionMessages(sessionId: string): Promise<AgentMessageRecord[]> {
  return get<AgentMessageRecord[]>(`/agent/sessions/${encodeURIComponent(sessionId)}/messages`)
}

export function updateSessionTitleRemote(
  sessionId: string,
  title: string,
): Promise<AgentSessionRecord> {
  return patch<AgentSessionRecord>(`/agent/sessions/${encodeURIComponent(sessionId)}`, { title })
}

export function deleteAgentSessionRemote(sessionId: string): Promise<void> {
  return del<void>(`/agent/sessions/${encodeURIComponent(sessionId)}`)
}

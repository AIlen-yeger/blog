import { genId } from '@/utils/id'

const SESSION_KEY = 'kohaku-agent-session-id'

export function getAgentSessionId(): string {
  try {
    const existing = localStorage.getItem(SESSION_KEY)
    if (existing) return existing
    const id = genId('sess')
    localStorage.setItem(SESSION_KEY, id)
    return id
  } catch {
    return genId('sess')
  }
}

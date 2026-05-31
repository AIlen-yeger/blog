import type { ChatMessage } from '@/composables/useDesktopPetChat'

const HISTORY_KEY = 'kohaku-agent-chat-history'
const MAX_STORED = 40

export function loadAgentChatHistory(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter(
        (m): m is ChatMessage =>
          !!m &&
          typeof m === 'object' &&
          (m.role === 'user' || m.role === 'assistant') &&
          typeof m.content === 'string' &&
          typeof m.id === 'string',
      )
      .slice(-MAX_STORED)
  } catch {
    return []
  }
}

export function saveAgentChatHistory(messages: ChatMessage[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(messages.slice(-MAX_STORED)))
  } catch {
    /* ignore quota */
  }
}

export function clearAgentChatHistory() {
  try {
    localStorage.removeItem(HISTORY_KEY)
  } catch {
    /* ignore */
  }
}

import { getAgentSessionId } from '@/utils/agentSession'

export function buildAgentChatPayload(question: string) {
  const limit = Number(import.meta.env.VITE_AGENT_HISTORY_LIMIT ?? 5)

  return {
    question,
    sessionId: getAgentSessionId(),
    limit: Number.isFinite(limit) ? Math.min(50, Math.max(1, limit)) : 5,
  }
}

import { getAgentSessionId } from '@/utils/agentSession'

export interface AgentAttachmentPayload {
  id: string
  name: string
  mime: string
  url?: string
  kind: 'image' | 'document' | 'text'
  text?: string
}

export function buildAgentChatPayload(
  question: string,
  sessionId?: string,
  attachments?: AgentAttachmentPayload[],
) {
  const limit = Number(import.meta.env.VITE_AGENT_HISTORY_LIMIT ?? 10)

  return {
    question,
    sessionId: (sessionId ?? getAgentSessionId()).trim(),
    limit: Number.isFinite(limit) ? Math.min(50, Math.max(1, limit)) : 10,
    attachments: attachments?.length ? attachments : undefined,
  }
}

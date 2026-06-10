import { getAgentSessionId } from '@/utils/agentSession'

export type ExecutionMode = 'auto' | 'plan' | 'fast'

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
  executionMode?: ExecutionMode,
) {
  const limit = Number(import.meta.env.VITE_AGENT_HISTORY_LIMIT ?? 10)

  return {
    question,
    sessionId: (sessionId ?? getAgentSessionId()).trim(),
    limit: Number.isFinite(limit) ? Math.min(50, Math.max(1, limit)) : 10,
    attachments: attachments?.length ? attachments : undefined,
    executionMode: executionMode ?? 'auto',
  }
}

const PLAN_PREFIX_RE = /^\/plan\s+/i

export function stripPlanPrefix(text: string): { question: string; forcePlan: boolean } {
  if (PLAN_PREFIX_RE.test(text)) {
    return { question: text.replace(PLAN_PREFIX_RE, '').trim(), forcePlan: true }
  }
  return { question: text, forcePlan: false }
}

/** Agent 全屏对话页 hash 路由 */

export type AgentRouteView = 'chat' | null

export function readAgentRouteFromUrl(): AgentRouteView {
  if (typeof window === 'undefined') return null
  const hash = window.location.hash.trim().toLowerCase()
  if (hash === '#/agent' || hash.startsWith('#/agent/')) return 'chat'
  return null
}

export function isAgentHash(): boolean {
  return readAgentRouteFromUrl() === 'chat'
}

export function buildAgentChatUrl(): string {
  if (typeof window === 'undefined') return '#/agent'
  return `${window.location.origin}${window.location.pathname}#/agent`
}

export function navigateToAgentChat() {
  if (typeof window === 'undefined') return
  window.open(buildAgentChatUrl(), '_blank', 'noopener,noreferrer')
}

export function exitAgentChat() {
  if (typeof window === 'undefined') return
  if (window.opener) {
    window.close()
    return
  }
  if (window.history.length > 1) {
    window.history.back()
    return
  }
  window.location.hash = '/blog'
}

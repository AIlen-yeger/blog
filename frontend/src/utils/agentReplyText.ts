/** 卡片预览：超出 maxChars 时截断并加省略号 */
export function truncateAgentReplyPreview(
  text: string,
  maxChars: number,
): { display: string; truncated: boolean } {
  const normalized = (text || '').trim()
  if (!normalized) return { display: '', truncated: false }
  const limit = Math.max(20, maxChars)
  if (normalized.length <= limit) {
    return { display: normalized, truncated: false }
  }
  return { display: `${normalized.slice(0, limit)}…`, truncated: true }
}

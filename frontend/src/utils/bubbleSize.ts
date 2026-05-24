/** 根据当前展示文本长度决定气泡档位 */
export type BubbleTier = 'compact' | 'normal' | 'wide'

const COMPACT_MAX = 72
const NORMAL_MAX = 240

export function bubbleTierFromText(text: string): BubbleTier {
  const len = text.trim().length
  if (len <= COMPACT_MAX) return 'compact'
  if (len <= NORMAL_MAX) return 'normal'
  return 'wide'
}

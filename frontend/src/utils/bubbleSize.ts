/** 根据当前展示文本长度决定气泡档位 */
export type BubbleTier = 'compact' | 'normal' | 'wide' | 'scroll'

/** 超过此字数：固定高度 + 内部滚动条 */
export const SCROLL_CHAR_THRESHOLD = 240

const COMPACT_MAX = 72
const NORMAL_MAX = 180
const WIDE_MAX = SCROLL_CHAR_THRESHOLD

export function bubbleTierFromText(text: string): BubbleTier {
  const len = text.trim().length
  if (len <= COMPACT_MAX) return 'compact'
  if (len <= NORMAL_MAX) return 'normal'
  if (len <= WIDE_MAX) return 'wide'
  return 'scroll'
}

export function messageNeedsScroll(text: string): boolean {
  return text.trim().length > SCROLL_CHAR_THRESHOLD
}

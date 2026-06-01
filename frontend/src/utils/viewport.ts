/** 与 CSS @media (max-width: 767px) 对齐 */
export function isMobileViewport(): boolean {
  if (typeof window === 'undefined') return false
  return window.innerWidth < 768
}

/** 着陆页是否由 .landing-wrap 承担纵向滚动 */
export function isLandingPageScrollable(): boolean {
  if (!isMobileViewport() || typeof document === 'undefined') return false
  const wrap = document.querySelector('.landing-wrap') as HTMLElement | null
  if (!wrap) return false
  return wrap.scrollHeight > wrap.clientHeight + 8
}

/** 桌宠默认位置需避开的底部区域（px，含滑动提示 / 底栏） */
export function mobileBottomReservePx(inBlog: boolean): number {
  const safe = 0
  try {
    const el = document.documentElement
    const pb = getComputedStyle(el).getPropertyValue('--mobile-pet-bottom-reserve')
    if (pb && pb.includes('rem')) {
      const rem = parseFloat(pb) || 5.25
      const root = parseFloat(getComputedStyle(el).fontSize) || 16
      return Math.round(rem * root) + safe
    }
  } catch {
    /* ignore */
  }
  return inBlog ? 76 : 92
}

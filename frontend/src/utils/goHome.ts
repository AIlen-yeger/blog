/** 回到着陆页：SPA 软切换，避免整页 reload */
export function goHome(ev?: Event) {
  ev?.preventDefault?.()
  ev?.stopPropagation?.()
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent('blog:return-landing'))
}

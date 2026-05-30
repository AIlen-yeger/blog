/** 强制回到站点根路径并刷新（绕过 SPA 同 URL 不刷新的问题） */
export function goHome() {
  const base = import.meta.env.BASE_URL || '/'
  const root = base.endsWith('/') ? base : `${base}/`
  window.location.href = `${root}?home=${Date.now()}`
}

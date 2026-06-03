/** URL hash 标记博客内 / 着陆页，F5 可恢复 */

export type BlogRouteView = 'landing' | 'blog'

export function readBlogRouteFromUrl(): BlogRouteView {
  if (typeof window === 'undefined') return 'landing'
  const hash = window.location.hash.trim().toLowerCase()
  if (hash === '#/blog' || hash.startsWith('#/blog')) return 'blog'
  return 'landing'
}

export function syncUrlToBlogView(view: BlogRouteView) {
  if (typeof window === 'undefined') return
  if (view === 'blog') {
    if (window.location.hash !== '#/blog') {
      window.location.hash = '/blog'
    }
    return
  }
  if (window.location.hash) {
    history.replaceState(
      null,
      '',
      window.location.pathname + window.location.search,
    )
  }
}

export function isBlogHash(): boolean {
  return readBlogRouteFromUrl() === 'blog'
}

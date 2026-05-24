import type { ContentKind, ViewRecordResult } from '@/types/views'

const COUNTS_KEY = 'personal-blog-view-counts'
const VIEWERS_KEY = 'personal-blog-view-viewers'

/** 与后端一致：未登录按 IP 去重（Mock 用会话内模拟 IP） */
const ANONYMOUS_VIEWER_PREFIX = 'ip:'

function resolveMockClientIp(): string {
  const key = 'personal-blog-mock-client-ip'
  let ip = sessionStorage.getItem(key)
  if (!ip) {
    ip = `mock-${Math.random().toString(36).slice(2, 10)}`
    sessionStorage.setItem(key, ip)
  }
  return ip.replace(/:/g, '_')
}

function resolveViewerKey(): string {
  try {
    const raw = localStorage.getItem('personal-blog-session')
    if (raw) {
      const user = JSON.parse(raw) as { email?: string }
      if (user?.email) return user.email.trim().toLowerCase()
    }
  } catch {
    /* ignore */
  }
  return ANONYMOUS_VIEWER_PREFIX + resolveMockClientIp()
}

function contentKey(kind: ContentKind, id: string) {
  return `${kind}:${id}`
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function writeJson(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value))
}

export function mockRecordContentView(
  kind: ContentKind,
  id: string,
): ViewRecordResult {
  const ck = contentKey(kind, id)
  const counts = readJson<Record<string, number>>(COUNTS_KEY, {})
  const viewers = readJson<Record<string, string[]>>(VIEWERS_KEY, {})
  const seen = viewers[ck] ?? []
  const viewerKey = resolveViewerKey()

  let recorded = false
  if (!seen.includes(viewerKey)) {
    seen.push(viewerKey)
    viewers[ck] = seen
    counts[ck] = (counts[ck] ?? 0) + 1
    recorded = true
    writeJson(VIEWERS_KEY, viewers)
    writeJson(COUNTS_KEY, counts)
  }

  return { viewCount: counts[ck] ?? 0, recorded }
}

export function mockGetViewCount(kind: ContentKind, id: string): number {
  const counts = readJson<Record<string, number>>(COUNTS_KEY, {})
  return counts[contentKey(kind, id)] ?? 0
}

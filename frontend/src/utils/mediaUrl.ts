import { getApiBase } from '@/api/http'

/** 将后端返回的相对路径转为可访问的完整 URL */
export function resolveMediaUrl(url: string | undefined): string {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url
  }
  if (url.startsWith('/v1/')) {
    if (import.meta.env.DEV) {
      return `http://localhost:8080${url}`
    }
    // 生产：/v1/uploads/... → /api/uploads/...（Nginx /api → Spring Boot /v1）
    return `${getApiBase()}${url.replace(/^\/v1/, '')}`
  }
  if (url.startsWith('/uploads/')) {
    if (import.meta.env.DEV) {
      return `http://localhost:8080/v1${url}`
    }
    return `${getApiBase()}${url}`
  }
  if (url.startsWith('/avatars/')) {
    const base = import.meta.env.BASE_URL.replace(/\/$/, '')
    return `${base}${url}`
  }
  if (url.startsWith('/')) {
    return import.meta.env.DEV ? `http://localhost:8080/v1${url}` : `/v1${url}`
  }
  return url
}

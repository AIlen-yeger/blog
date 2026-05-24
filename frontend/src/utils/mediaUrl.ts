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
    const base = getApiBase().replace(/\/api\/?$/, '')
    return `${base}${url.replace(/^\/v1/, '')}`
  }
  if (url.startsWith('/uploads/')) {
    const path = `/v1${url}`
    return import.meta.env.DEV ? `http://localhost:8080${path}` : path
  }
  if (url.startsWith('/')) {
    return import.meta.env.DEV ? `http://localhost:8080/v1${url}` : `/v1${url}`
  }
  return url
}

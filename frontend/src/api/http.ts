import { AUTH_CODE_UNAUTHORIZED } from '@/constants/authCodes'
import { clearSession, getAuthToken } from '@/composables/useSession'
import { httpStatusMessage, toUserErrorMessage } from '@/utils/userErrorMessage'

export class ApiError extends Error {
  readonly code: number

  constructor(code: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

/** 开发环境默认走 Vite 代理 /api → localhost:8080 */
export function getApiBase(): string {
  const base = import.meta.env.VITE_API_BASE
  if (base) return base.replace(/\/$/, '')
  return import.meta.env.DEV ? '/api' : 'http://localhost:8080/v1'
}

export function useMockApi(): boolean {
  return import.meta.env.VITE_USE_MOCK === 'true'
}

type RequestOptions = {
  /** 默认 true；登录等接口传 false */
  auth?: boolean
}

export async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const { auth = true } = options
  const headers: Record<string, string> = {
    Accept: 'application/json',
  }
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData
  if (body !== undefined && !isFormData) {
    headers['Content-Type'] = 'application/json'
  }
  if (auth) {
    const token = getAuthToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  const url = `${getApiBase()}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, {
    method,
    headers,
    body:
      body === undefined
        ? undefined
        : isFormData
          ? (body as FormData)
          : JSON.stringify(body),
  })

  if (res.status === 204) {
    return undefined as T
  }

  let json: ApiEnvelope<T> | null = null
  try {
    const text = await res.text()
    if (text) json = JSON.parse(text) as ApiEnvelope<T>
  } catch {
    /* 非 JSON 响应 */
  }

  const code = json ? Number(json.code) : NaN
  if (!json || Number.isNaN(code)) {
    throw new ApiError(
      res.status,
      res.ok ? '服务响应异常，请稍后重试' : httpStatusMessage(res.status),
    )
  }

  if (code !== 0) {
    // 仅对已要求鉴权的请求清会话，避免着陆页公开接口 401 触发 logout 死循环
    if (auth && (code === AUTH_CODE_UNAUTHORIZED || res.status === 401)) {
      clearSession()
    }
    const raw = json.message?.trim() || ''
    throw new ApiError(
      code,
      toUserErrorMessage(new ApiError(code, raw), '请求失败，请稍后重试'),
    )
  }

  return json.data
}

export function post<T>(path: string, body: unknown, options?: RequestOptions) {
  return request<T>('POST', path, body, options)
}

export function get<T>(path: string, options?: RequestOptions) {
  return request<T>('GET', path, undefined, options)
}

export function put<T>(path: string, body: unknown, options?: RequestOptions) {
  return request<T>('PUT', path, body, options)
}

export function patch<T>(path: string, body: unknown, options?: RequestOptions) {
  return request<T>('PATCH', path, body, options)
}

export function del<T>(path: string, options?: RequestOptions) {
  return request<T>('DELETE', path, undefined, options)
}

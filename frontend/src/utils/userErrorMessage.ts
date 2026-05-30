import { ApiError } from '@/api/http'
import {
  AUTH_CODE_NOT_REGISTERED,
  AUTH_CODE_SEND_TOO_FREQUENT,
  AUTH_CODE_UNAUTHORIZED,
  AUTH_CODE_WRONG_PASSWORD,
} from '@/constants/authCodes'

const HTTP_IN_MESSAGE = /\bHTTP\s*\d{3}\b/gi

/** 已知业务错误码 → 用户可读文案（不展示数字码） */
const KNOWN_API_MESSAGES: Record<number, string> = {
  [AUTH_CODE_WRONG_PASSWORD]: '密码错误',
  [AUTH_CODE_NOT_REGISTERED]: '该邮箱尚未注册',
  [AUTH_CODE_SEND_TOO_FREQUENT]: '验证码发送过于频繁，请稍后再试',
  [AUTH_CODE_UNAUTHORIZED]: '登录已过期，请重新登录',
}

/** 根据 HTTP 状态生成文案（不含状态码字面量） */
export function httpStatusMessage(status: number): string {
  if (status >= 500) return '服务暂时不可用，请稍后再试'
  if (status === 404) return '未找到请求的内容'
  if (status === 403) return '没有权限访问'
  if (status === 401) return '请先登录后再试'
  if (status === 429) return '请求过于频繁，请稍后再试'
  if (status === 0) return '无法连接服务器，请检查网络后重试'
  if (status >= 400) return '请求未能完成，请稍后重试'
  return '服务响应异常，请稍后重试'
}

function looksTechnical(msg: string): boolean {
  if (HTTP_IN_MESSAGE.test(msg)) return true
  if (/Exception|ECONNREFUSED|ETIMEDOUT|NetworkError|fetch failed/i.test(msg)) return true
  if (/\b(?:status|code)\s*[:=]?\s*\d{3,5}\b/i.test(msg)) return true
  if (/\.sql\b|migration-/i.test(msg)) return true
  if (/public\/|node_modules|localhost|127\.0\.0\.1|:\d{4,5}\//i.test(msg)) return true
  if (/^\{[\s\S]*"code"/.test(msg)) return true
  if (/\bat\s+[\w.$]+\(/m.test(msg)) return true
  return false
}

function cleanMessage(msg: string): string {
  return msg.replace(HTTP_IN_MESSAGE, '').replace(/\s{2,}/g, ' ').trim()
}

/**
 * 将任意错误转为可展示给用户的文案（不含 HTTP 状态码、业务码等）。
 */
export function toUserErrorMessage(
  err: unknown,
  fallback = '操作失败，请稍后重试',
): string {
  if (err == null) return fallback

  if (typeof err === 'string') {
    const s = cleanMessage(err)
    if (!s || looksTechnical(s)) return fallback
    return s
  }

  if (err instanceof ApiError) {
    const known = KNOWN_API_MESSAGES[err.code]
    if (known) return known
    if (err.code >= 100 && err.code <= 599) {
      return httpStatusMessage(err.code)
    }
    const msg = cleanMessage(err.message)
    if (msg && !looksTechnical(msg)) return msg
    return fallback
  }

  if (err instanceof Error) {
    const msg = cleanMessage(err.message)
    if (!msg || looksTechnical(msg)) return fallback
    return msg
  }

  return fallback
}

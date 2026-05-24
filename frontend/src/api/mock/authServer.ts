/**
 * 本地 Mock「服务端」：仅模拟 HTTP 鉴权与角色下发，不代表客户端配置。
 * 接入真实后端后删除或停用，改由 src/api/auth.ts 请求远程接口。
 */
import type { AuthUser, LoginResult } from '@/types/auth'
import { ApiError } from '@/api/http'
import {
  AUTH_CODE_NOT_REGISTERED,
  AUTH_CODE_WRONG_PASSWORD,
} from '@/constants/authCodes'

const USERS_KEY = 'personal-blog-users'
const PENDING_KEY = 'personal-blog-pending'
const DEV_CODE = '123456'

interface StoredUser {
  email: string
  password: string
  role: AuthUser['role']
}

function loadUsers(): StoredUser[] {
  try {
    return JSON.parse(localStorage.getItem(USERS_KEY) ?? '[]') as StoredUser[]
  } catch {
    return []
  }
}

function saveUsers(users: StoredUser[]) {
  localStorage.setItem(USERS_KEY, JSON.stringify(users))
}

function buildLoginResult(user: StoredUser): LoginResult {
  return {
    token: `mock-token-${user.email}`,
    user: { email: user.email, role: user.role },
  }
}

function randomCode(): string {
  return String(Math.floor(100000 + Math.random() * 900000))
}

export function isQQEmail(email: string): boolean {
  return /^[^\s@]+@qq\.com$/i.test(email.trim())
}

/** 模拟 POST /auth/login（与后端错误码一致） */
export function mockLogin(email: string, password: string): LoginResult {
  const e = email.trim().toLowerCase()
  const found = loadUsers().find((u) => u.email === e)
  if (!found) {
    throw new ApiError(
      AUTH_CODE_NOT_REGISTERED,
      '该邮箱未注册，请完成验证码注册',
    )
  }
  if (found.password !== password) {
    throw new ApiError(AUTH_CODE_WRONG_PASSWORD, '密码错误')
  }
  return buildLoginResult(found)
}

/** 模拟 POST /auth/register/send-code；新账号进入验证码流程 */
export function mockSendRegisterCode(email: string, password: string): void {
  const code = import.meta.env.DEV ? DEV_CODE : randomCode()
  localStorage.setItem(
    PENDING_KEY,
    JSON.stringify({ email: email.trim().toLowerCase(), password, code }),
  )
  console.info('[mock-server] 邮箱验证码:', code)
}

export function mockHasAccount(email: string): boolean {
  const e = email.trim().toLowerCase()
  return loadUsers().some((u) => u.email === e)
}

/** 模拟 POST /auth/register/verify */
export function mockRegisterVerify(
  email: string,
  password: string,
  code: string,
): LoginResult {
  const raw = localStorage.getItem(PENDING_KEY)
  if (!raw) throw new Error('请先填写邮箱与密码')

  const pending = JSON.parse(raw) as {
    email: string
    password: string
    code: string
  }
  const e = email.trim().toLowerCase()
  const input = code.trim()
  const valid =
    input === pending.code || (import.meta.env.DEV && input === DEV_CODE)
  if (!valid) throw new Error('验证码错误')
  if (pending.email !== e || pending.password !== password) {
    throw new Error('注册信息已失效，请重新填写')
  }

  const users = loadUsers()
  let user = users.find((u) => u.email === e)
  if (!user) {
    user = { email: e, password, role: 'user' }
    users.push(user)
    saveUsers(users)
  }
  localStorage.removeItem(PENDING_KEY)
  return buildLoginResult(user)
}

/** 模拟 POST /auth/register/resend-code */
export function mockResendRegisterCode(email: string, password: string): void {
  mockSendRegisterCode(email, password)
}

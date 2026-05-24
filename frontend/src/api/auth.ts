import type { LoginResult } from '@/types/auth'
import { ApiError, post, useMockApi } from '@/api/http'
import { AUTH_CODE_NOT_REGISTERED } from '@/constants/authCodes'
import {
  isQQEmail,
  mockLogin,
  mockRegisterVerify,
  mockResendRegisterCode,
  mockSendRegisterCode,
} from '@/api/mock/authServer'

export { isQQEmail }
export { ApiError }

export type CredentialsResult =
  | { type: 'logged_in'; data: LoginResult }
  /** 未注册：仅表示应进入验证码页，发码在切页后单独调用 */
  | { type: 'need_verify'; message: string }

function validateCredentialsInput(email: string, password: string) {
  const e = email.trim().toLowerCase()
  if (!isQQEmail(e)) throw new Error('请使用 QQ 邮箱（@qq.com）')
  if (!password) throw new Error('请输入密码')
  if (password.length < 6) throw new Error('密码至少 6 位')
  return e
}

function isNotRegistered(err: unknown): err is ApiError {
  return err instanceof ApiError && err.code === AUTH_CODE_NOT_REGISTERED
}

/** POST /auth/login：未注册(40403) 只返回 need_verify，不在此步发验证码 */
export async function loginWithCredentials(
  email: string,
  password: string,
): Promise<CredentialsResult> {
  const e = validateCredentialsInput(email, password)

  try {
    const data = useMockApi()
      ? mockLogin(e, password)
      : await post<LoginResult>('/auth/login', { email: e, password }, { auth: false })
    return { type: 'logged_in', data }
  } catch (err) {
    if (isNotRegistered(err)) {
      return {
        type: 'need_verify',
        message: err.message || '该邮箱未注册，请完成验证码注册',
      }
    }
    throw err instanceof ApiError ? new Error(err.message) : err
  }
}

/** POST /auth/register/send-code（进入验证码页后调用） */
export async function sendRegisterCode(
  email: string,
  password: string,
): Promise<void> {
  const e = validateCredentialsInput(email, password)
  if (useMockApi()) {
    mockSendRegisterCode(e, password)
    return
  }
  await post('/auth/register/send-code', { email: e, password }, { auth: false })
}

export async function verifyRegistration(
  email: string,
  password: string,
  code: string,
): Promise<LoginResult> {
  const e = validateCredentialsInput(email, password)
  if (useMockApi()) {
    return mockRegisterVerify(e, password, code)
  }
  return post<LoginResult>(
    '/auth/register/verify',
    { email: e, password, code: code.trim() },
    { auth: false },
  )
}

export async function resendRegistrationCode(
  email: string,
  password: string,
): Promise<void> {
  const e = validateCredentialsInput(email, password)
  if (useMockApi()) {
    mockResendRegisterCode(e, password)
    return
  }
  await post('/auth/register/resend-code', { email: e }, { auth: false })
}

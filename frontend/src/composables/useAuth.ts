import { onUnmounted, ref } from 'vue'
import {
  loginWithCredentials,
  resendRegistrationCode,
  sendRegisterCode,
  verifyRegistration,
} from '@/api/auth'
import { ApiError } from '@/api/http'
import {
  AUTH_CODE_SEND_TOO_FREQUENT,
  AUTH_CODE_WRONG_PASSWORD,
} from '@/constants/authCodes'
import type { LoginResult } from '@/types/auth'
import {
  getDefaultResendCooldownSeconds,
  getResendRemainingSeconds,
  startResendCooldown,
} from '@/utils/resendCooldown'

export type LoginStep = 'credentials' | 'verify'

export function useAuth() {
  const step = ref<LoginStep>('credentials')
  const error = ref('')
  const verifyHint = ref('')
  const pendingEmail = ref('')
  const pendingPassword = ref('')
  const submitting = ref(false)
  const sendingCode = ref(false)
  const resendSecondsLeft = ref(0)

  let resendTimer: ReturnType<typeof setInterval> | null = null

  function refreshResendCooldown() {
    resendSecondsLeft.value = pendingEmail.value
      ? getResendRemainingSeconds(pendingEmail.value)
      : 0
  }

  function stopResendTimer() {
    if (resendTimer) {
      clearInterval(resendTimer)
      resendTimer = null
    }
  }

  function startResendTimer() {
    stopResendTimer()
    refreshResendCooldown()
    if (resendSecondsLeft.value <= 0) return
    resendTimer = setInterval(() => {
      refreshResendCooldown()
      if (resendSecondsLeft.value <= 0) stopResendTimer()
    }, 1000)
  }

  function beginResendCooldown(seconds = getDefaultResendCooldownSeconds()) {
    if (!pendingEmail.value) return
    startResendCooldown(pendingEmail.value, seconds)
    startResendTimer()
  }

  function resetFlow() {
    step.value = 'credentials'
    error.value = ''
    verifyHint.value = ''
    pendingEmail.value = ''
    pendingPassword.value = ''
    submitting.value = false
    sendingCode.value = false
    stopResendTimer()
    resendSecondsLeft.value = 0
  }

  function goToVerifyStep(email: string, password: string, message: string) {
    pendingEmail.value = email.trim().toLowerCase()
    pendingPassword.value = password
    error.value = ''
    verifyHint.value = message
    step.value = 'verify'
    startResendTimer()
  }

  async function dispatchRegisterCode(email: string, password: string) {
    if (getResendRemainingSeconds(email) > 0) {
      refreshResendCooldown()
      error.value = `${resendSecondsLeft.value} 秒后可重新发送验证码`
      return
    }

    sendingCode.value = true
    error.value = ''
    try {
      await sendRegisterCode(email, password)
      beginResendCooldown()
      verifyHint.value = `验证码已发送至 ${pendingEmail.value}，请查收邮件`
    } catch (e) {
      if (e instanceof ApiError && e.code === AUTH_CODE_SEND_TOO_FREQUENT) {
        beginResendCooldown()
        error.value = e.message || '验证码发送过于频繁，请稍后再试'
      } else {
        error.value =
          e instanceof Error ? e.message : '验证码邮件发送失败，请稍后重试'
      }
      verifyHint.value =
        '请填写验证码完成注册；若未收到邮件，可点击下方「重新发送」'
    } finally {
      sendingCode.value = false
    }
  }

  async function submitCredentials(
    email: string,
    password: string,
  ): Promise<LoginResult | null> {
    error.value = ''
    verifyHint.value = ''
    submitting.value = true
    try {
      const result = await loginWithCredentials(email, password)
      if (result.type === 'logged_in') {
        return result.data
      }

      goToVerifyStep(email, password, result.message)
      await dispatchRegisterCode(email, password)
      return null
    } catch (e) {
      if (e instanceof ApiError && e.code === AUTH_CODE_WRONG_PASSWORD) {
        error.value = e.message || '密码错误'
      } else {
        error.value = e instanceof Error ? e.message : '登录失败'
      }
      return null
    } finally {
      submitting.value = false
    }
  }

  async function submitVerify(
    email: string,
    password: string,
    code: string,
  ): Promise<LoginResult | null> {
    error.value = ''
    try {
      return await verifyRegistration(email, password, code)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '验证失败'
      return null
    }
  }

  async function resendCode(): Promise<void> {
    const email = pendingEmail.value
    const password = pendingPassword.value
    if (!email || !password) {
      error.value = '请先填写邮箱与密码'
      return
    }
    if (resendSecondsLeft.value > 0) {
      error.value = `${resendSecondsLeft.value} 秒后可重新发送验证码`
      return
    }
    await dispatchRegisterCode(email, password)
  }

  function backToCredentials() {
    step.value = 'credentials'
    error.value = ''
    verifyHint.value = ''
    sendingCode.value = false
    stopResendTimer()
    resendSecondsLeft.value = 0
  }

  onUnmounted(stopResendTimer)

  return {
    step,
    error,
    verifyHint,
    pendingEmail,
    submitting,
    sendingCode,
    resendSecondsLeft,
    resetFlow,
    submitCredentials,
    submitVerify,
    resendCode,
    backToCredentials,
  }
}

import { computed, ref } from 'vue'
import type { AuthUser, UserRole } from '@/types/auth'

const SESSION_KEY = 'personal-blog-session'
const TOKEN_KEY = 'personal-blog-token'

const currentUser = ref<AuthUser | null>(null)

function loadUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as AuthUser
    if (!data?.email || (data.role !== 'admin' && data.role !== 'user')) {
      return null
    }
    return data
  } catch {
    return null
  }
}

function persistSession(user: AuthUser | null, token?: string) {
  if (user && token) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(user))
    localStorage.setItem(TOKEN_KEY, token)
    return
  }
  localStorage.removeItem(SESSION_KEY)
  localStorage.removeItem(TOKEN_KEY)
}

/** 从 localStorage 恢复登录态（刷新页面时调用） */
export function initSessionFromStorage(): boolean {
  migrateLegacySessionStorage()

  const user = loadUser()
  const token = localStorage.getItem(TOKEN_KEY)
  if (user && token) {
    currentUser.value = user
    return true
  }
  if (user || token) {
    clearSession()
  }
  currentUser.value = null
  return false
}

function migrateLegacySessionStorage() {
  const legacyToken = sessionStorage.getItem(TOKEN_KEY)
  const legacyUser = sessionStorage.getItem(SESSION_KEY)
  if (legacyToken && !localStorage.getItem(TOKEN_KEY)) {
    localStorage.setItem(TOKEN_KEY, legacyToken)
  }
  if (legacyUser && !localStorage.getItem(SESSION_KEY)) {
    localStorage.setItem(SESSION_KEY, legacyUser)
  }
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(SESSION_KEY)
}

/** 登录成功：写入 token 与用户信息 */
export function setSessionFromLogin(result: {
  user: AuthUser
  token?: string
}) {
  if (!result.token) {
    console.warn('[personal-blog] 登录响应缺少 token，后续接口将无法鉴权')
  }
  currentUser.value = { ...result.user }
  if (result.token) {
    persistSession(currentUser.value, result.token)
  } else {
    persistSession(null)
    localStorage.setItem(SESSION_KEY, JSON.stringify(currentUser.value))
  }
}

export function clearSession() {
  currentUser.value = null
  persistSession(null)
  window.dispatchEvent(new CustomEvent('auth:logout'))
}

/** 退出登录：清除 token 并通知应用回到着陆页 */
export function logout() {
  clearSession()
}

export function getStoredUser(): AuthUser | null {
  return loadUser()
}

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function hasValidSession(): boolean {
  return !!getAuthToken() && !!loadUser()
}

export function useSession() {
  const role = computed<UserRole | null>(() => currentUser.value?.role ?? null)
  const isAdmin = computed(() => currentUser.value?.role === 'admin')
  const isLoggedIn = computed(() => hasValidSession())

  return {
    currentUser,
    role,
    isAdmin,
    isLoggedIn,
  }
}

// 模块加载时同步内存中的用户（便于非组件代码读取 role）
initSessionFromStorage()

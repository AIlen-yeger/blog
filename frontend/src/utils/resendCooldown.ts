const STORAGE_KEY = 'personal-blog-resend-cooldown'

/** 与后端 app.register.resend-cooldown-seconds 保持一致 */
export function getDefaultResendCooldownSeconds(): number {
  const raw = import.meta.env.VITE_RESEND_COOLDOWN_SECONDS
  const n = raw ? Number(raw) : 60
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 60
}

function loadMap(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<
      string,
      number
    >
  } catch {
    return {}
  }
}

function saveMap(map: Record<string, number>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(map))
}

function normalizeEmail(email: string): string {
  return email.trim().toLowerCase()
}

/** 剩余秒数，0 表示可发送 */
export function getResendRemainingSeconds(email: string): number {
  const e = normalizeEmail(email)
  if (!e) return 0
  const until = loadMap()[e]
  if (!until) return 0
  const left = Math.ceil((until - Date.now()) / 1000)
  if (left <= 0) {
    clearResendCooldown(e)
    return 0
  }
  return left
}

export function startResendCooldown(
  email: string,
  seconds = getDefaultResendCooldownSeconds(),
) {
  const e = normalizeEmail(email)
  if (!e || seconds <= 0) return
  const map = loadMap()
  map[e] = Date.now() + seconds * 1000
  saveMap(map)
}

export function clearResendCooldown(email: string) {
  const e = normalizeEmail(email)
  if (!e) return
  const map = loadMap()
  if (!(e in map)) return
  delete map[e]
  saveMap(map)
}

import { onMounted, onUnmounted, watch, type Ref } from 'vue'

function isQqOrigin(origin: string): boolean {
  try {
    const u = new URL(origin)
    return u.hostname === 'i.y.qq.com' || u.hostname.endsWith('.qq.com')
  } catch {
    return false
  }
}

function isEndedMessage(data: unknown): boolean {
  if (data == null) return false
  if (typeof data === 'string') {
    const s = data.toLowerCase()
    return /ended|finish|complete|playend|songend/.test(s)
  }
  if (typeof data !== 'object') return false
  const o = data as Record<string, unknown>
  if (o.ended === true || o.isEnded === true) return true
  const state = String(o.state ?? o.status ?? o.event ?? o.type ?? o.action ?? '').toLowerCase()
  return /ended|finish|complete|playend|songend/.test(state)
}

/**
 * QQ 官方 iframe 默认单曲循环；父页按曲目时长在结束后切换 songId。
 */
export function useQqEmbedAutoAdvance(options: {
  songId: Ref<string>
  durationSec: Ref<number | undefined>
  enabled: Ref<boolean>
  onEnded: () => void
}) {
  let timer: ReturnType<typeof setTimeout> | null = null

  function clearTimer() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  function schedule() {
    clearTimer()
    if (!options.enabled.value) return
    const sec = options.durationSec.value
    if (!sec || sec <= 0) return
    timer = setTimeout(() => options.onEnded(), sec * 1000 + 3000)
  }

  function onMessage(event: MessageEvent) {
    if (!options.enabled.value || !isQqOrigin(event.origin)) return
    if (!isEndedMessage(event.data)) return
    clearTimer()
    options.onEnded()
  }

  watch(
    () => [options.songId.value, options.durationSec.value, options.enabled.value] as const,
    () => schedule(),
    { immediate: true },
  )

  onMounted(() => {
    window.addEventListener('message', onMessage)
  })

  onUnmounted(() => {
    clearTimer()
    window.removeEventListener('message', onMessage)
  })

  return { restart: schedule }
}

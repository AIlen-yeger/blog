import { ref } from 'vue'

const STORAGE_KEY = 'desktop-pet-scale-v1'
const MIN = 0.55
const MAX = 1.85
const DEFAULT = 1
const STEP = 0.07

function readStored(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT
    const n = Number(raw)
    if (Number.isFinite(n)) return Math.min(MAX, Math.max(MIN, n))
  } catch {
    /* ignore */
  }
  return DEFAULT
}

function saveStored(scale: number) {
  try {
    localStorage.setItem(STORAGE_KEY, String(scale))
  } catch {
    /* ignore */
  }
}

export function useDesktopPetScale() {
  const spriteScale = ref(readStored())

  function onAvatarWheel(e: WheelEvent) {
    e.preventDefault()
    e.stopPropagation()
    const next = spriteScale.value + (e.deltaY < 0 ? STEP : -STEP)
    spriteScale.value = Math.min(MAX, Math.max(MIN, Math.round(next * 100) / 100))
    saveStored(spriteScale.value)
  }

  function resetScale() {
    spriteScale.value = DEFAULT
    saveStored(DEFAULT)
  }

  return {
    spriteScale,
    onAvatarWheel,
    resetScale,
    scaleMin: MIN,
    scaleMax: MAX,
  }
}

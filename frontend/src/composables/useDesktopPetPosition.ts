import { onMounted, onUnmounted, ref, type Ref } from 'vue'
import { isMobileViewport, mobileBottomReservePx } from '@/utils/viewport'

const STORAGE_KEY = 'desktop-pet-position-v1'
const DRAG_THRESHOLD_PX = 8

interface PetPosition {
  x: number
  y: number
}

function readStored(): PetPosition | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const p = JSON.parse(raw) as PetPosition
    if (typeof p.x === 'number' && typeof p.y === 'number') return p
  } catch {
    /* ignore */
  }
  return null
}

function saveStored(p: PetPosition) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(p))
  } catch {
    /* ignore */
  }
}

function defaultPosition(rootW: number, rootH: number): PetPosition {
  const margin = isMobileViewport() ? 10 : 20
  const bottomReserve = isMobileViewport()
    ? mobileBottomReservePx(!!document.querySelector('.blog-stage'))
    : margin
  if (isMobileViewport()) {
    return {
      x: margin,
      y: Math.max(margin, window.innerHeight - rootH - bottomReserve),
    }
  }
  return {
    x: Math.max(margin, window.innerWidth - rootW - margin),
    y: Math.max(margin, window.innerHeight - rootH - margin),
  }
}

function clampPosition(x: number, y: number, rootW: number, rootH: number): PetPosition {
  const margin = isMobileViewport() ? 10 : 8
  const bottomReserve = isMobileViewport()
    ? mobileBottomReservePx(!!document.querySelector('.blog-stage'))
    : margin
  const maxX = Math.max(margin, window.innerWidth - rootW - margin)
  const maxY = Math.max(margin, window.innerHeight - rootH - bottomReserve)
  return {
    x: Math.min(maxX, Math.max(margin, x)),
    y: Math.min(maxY, Math.max(margin, y)),
  }
}

function isInteractiveTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return !!target.closest('input, textarea, button, select, a, [contenteditable="true"]')
}

function isAvatarTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return !!target.closest('.pet-assistant__avatar')
}

export function useDesktopPetPosition(
  rootRef: Ref<HTMLElement | null>,
  onAvatarTap?: () => void,
) {
  const posX = ref(0)
  const posY = ref(0)
  const dragging = ref(false)

  let pointerId: number | null = null
  let dragOffsetX = 0
  let dragOffsetY = 0
  let startClientX = 0
  let startClientY = 0
  let hasMoved = false
  let startedOnAvatar = false

  function measureAndPlace(preferDefault = false) {
    const el = rootRef.value
    if (!el) return
    const rect = el.getBoundingClientRect()
    const stored = preferDefault ? null : readStored()
    const base = stored ?? defaultPosition(rect.width, rect.height)
    const clamped = clampPosition(base.x, base.y, rect.width, rect.height)
    posX.value = clamped.x
    posY.value = clamped.y
  }

  function onResize() {
    measureAndPlace(false)
  }

  function beginDrag(e: PointerEvent) {
    const el = rootRef.value
    if (!el) return
    dragging.value = true
    el.setPointerCapture(e.pointerId)
    document.body.style.userSelect = 'none'
  }

  function onPointerDown(e: PointerEvent) {
    if (e.button !== 0 || isInteractiveTarget(e.target)) return

    pointerId = e.pointerId
    hasMoved = false
    startedOnAvatar = isAvatarTarget(e.target)
    startClientX = e.clientX
    startClientY = e.clientY
    dragOffsetX = e.clientX - posX.value
    dragOffsetY = e.clientY - posY.value
  }

  function onPointerMove(e: PointerEvent) {
    if (pointerId !== e.pointerId) return

    const dx = e.clientX - startClientX
    const dy = e.clientY - startClientY
    if (!hasMoved && Math.hypot(dx, dy) >= DRAG_THRESHOLD_PX) {
      hasMoved = true
      beginDrag(e)
    }

    if (!dragging.value) return

    const el = rootRef.value
    if (!el) return
    const rect = el.getBoundingClientRect()
    const next = clampPosition(
      e.clientX - dragOffsetX,
      e.clientY - dragOffsetY,
      rect.width,
      rect.height,
    )
    posX.value = next.x
    posY.value = next.y
  }

  function onPointerUp(e: PointerEvent) {
    if (pointerId !== e.pointerId) return

    const tapOnAvatar = startedOnAvatar && !hasMoved

    if (dragging.value) {
      rootRef.value?.releasePointerCapture(e.pointerId)
      document.body.style.userSelect = ''
      saveStored({ x: posX.value, y: posY.value })
    }

    if (tapOnAvatar) {
      onAvatarTap?.()
    }

    dragging.value = false
    pointerId = null
    hasMoved = false
    startedOnAvatar = false
  }

  onMounted(() => {
    requestAnimationFrame(() => measureAndPlace(false))
    window.addEventListener('resize', onResize)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', onResize)
    document.body.style.userSelect = ''
  })

  return {
    posX,
    posY,
    dragging,
    measureAndPlace,
    onPointerDown,
    onPointerMove,
    onPointerUp,
  }
}

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

const canvasRef = ref<HTMLCanvasElement | null>(null)

interface RainDrop {
  x: number
  y: number
  len: number
  speed: number
  opacity: number
  width: number
}

let ctx: CanvasRenderingContext2D | null = null
let drops: RainDrop[] = []
let raf = 0
let w = 0
let h = 0
let running = false
let reducedMotion = false

const DROP_COUNT = 220

function rand(min: number, max: number) {
  return min + Math.random() * (max - min)
}

function spawnDrop(resetY = false): RainDrop {
  return {
    x: Math.random() * w,
    y: resetY ? rand(-h, 0) : Math.random() * h,
    len: rand(18, 42),
    speed: rand(11, 24),
    opacity: rand(0.2, 0.52),
    width: rand(1.1, 2.4),
  }
}

function initDrops() {
  drops = Array.from({ length: DROP_COUNT }, () => spawnDrop(true))
}

function resize() {
  const canvas = canvasRef.value
  if (!canvas) return
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  w = canvas.clientWidth
  h = canvas.clientHeight
  canvas.width = Math.floor(w * dpr)
  canvas.height = Math.floor(h * dpr)
  ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  initDrops()
}

function tick() {
  if (!ctx || !running) return
  ctx.clearRect(0, 0, w, h)

  for (const d of drops) {
    d.y += d.speed
    d.x += 0.55

    ctx.beginPath()
    ctx.strokeStyle = `rgba(196, 218, 255, ${d.opacity})`
    ctx.lineWidth = d.width
    ctx.lineCap = 'round'
    ctx.moveTo(d.x, d.y)
    ctx.lineTo(d.x - 2, d.y + d.len)
    ctx.stroke()

    if (d.y - d.len > h || d.x > w + 20) {
      Object.assign(d, spawnDrop(true))
      d.y = rand(-40, -8)
    }
  }

  raf = requestAnimationFrame(tick)
}

function start() {
  if (running || reducedMotion) return
  running = true
  raf = requestAnimationFrame(tick)
}

function stop() {
  running = false
  cancelAnimationFrame(raf)
}

function onVisibility() {
  if (document.hidden) stop()
  else start()
}

onMounted(() => {
  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  resize()
  window.addEventListener('resize', resize)
  document.addEventListener('visibilitychange', onVisibility)
  if (!reducedMotion) start()
})

onUnmounted(() => {
  stop()
  window.removeEventListener('resize', resize)
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<template>
  <canvas
    ref="canvasRef"
    class="landing-rain"
    aria-hidden="true"
  />
</template>

<style scoped>
.landing-rain {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  pointer-events: none;
  opacity: 0.88;
}
</style>

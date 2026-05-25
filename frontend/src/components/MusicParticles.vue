<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { musicLevel } from '@/composables/useMusicAnalyser'
import type { LyricLine } from '@/utils/lrc'
import { pickLyricSnippet } from '@/utils/lrc'
import type { ParticleTheme } from '@/types/music'
import {
  getLeafPalette,
  getSakuraPalette,
} from '@/utils/seasonPalette'

const props = withDefaults(
  defineProps<{
    active?: boolean
    theme?: ParticleTheme
    /** 是否飘落歌词（与樱花/落叶叠加） */
    lyricsFall?: boolean
    lyricLines?: LyricLine[]
    currentTime?: number
  }>(),
  {
    active: false,
    theme: 'mixed',
    lyricsFall: true,
    lyricLines: () => [],
    currentTime: 0,
  },
)

const canvasRef = ref<HTMLCanvasElement | null>(null)
let raf = 0
let particles: Particle[] = []
let spawnTimer = 0
let lyricSpawnTimer = 0
let reducedMotion = false
/** 视觉用响度，比原始 musicLevel 变化更慢，减轻闪烁 */
let smoothLevel = 0

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  rot: number
  rotSpeed: number
  size: number
  opacity: number
  life: number
  maxLife: number
  kind: 'sakura' | 'leaf' | 'lyric'
  sway: number
  swaySpeed: number
  text?: string
  /** 歌词固定色，避免随 sway 变色闪烁 */
  colorIdx?: number
}

const MAX_LYRIC_ON_SCREEN = 5
const MAX_LYRIC_FALLBACK = 3

const LYRIC_COLORS: [number, number, number][] = [
  [255, 105, 180],
  [56, 189, 248],
  [250, 204, 21],
  [192, 132, 252],
  [52, 211, 153],
  [251, 113, 133],
]

function lyricCount(): number {
  return particles.filter((p) => p.kind === 'lyric').length
}

function fallSpeedMul(level: number): number {
  return 0.32 + level * 2.35
}

function spawnEveryFrames(level: number): number {
  return Math.max(2, Math.round(9 - level * 6))
}

function lyricSpawnEveryFrames(sparse: boolean): number {
  return sparse ? 72 : 52
}

function pickKind(): 'sakura' | 'leaf' {
  if (props.theme === 'sakura') return 'sakura'
  if (props.theme === 'leaf') return 'leaf'
  return Math.random() < 0.55 ? 'sakura' : 'leaf'
}

function spawn(w: number, _h: number, level: number) {
  const kind = pickKind()
  const size = kind === 'sakura' ? 6 + Math.random() * 10 : 8 + Math.random() * 12
  const boost = 0.5 + level * 0.9
  particles.push({
    x: Math.random() * w,
    y: -size - Math.random() * 40,
    vx: (Math.random() - 0.5) * (0.45 + level * 0.5),
    vy: (0.28 + Math.random() * 0.75) * boost,
    rot: Math.random() * Math.PI * 2,
    rotSpeed: (Math.random() - 0.5) * (0.02 + level * 0.04),
    size,
    opacity: 0.5 + Math.random() * 0.4,
    life: 0,
    maxLife: 280 + Math.random() * 220,
    kind,
    sway: Math.random() * Math.PI * 2,
    swaySpeed: 0.018 + Math.random() * 0.028 + level * 0.02,
  })
  if (particles.length > 120) particles.shift()
}

function spawnLyric(w: number, _h: number, text: string, maxOnScreen: number) {
  if (lyricCount() >= maxOnScreen) return
  const raw = text.trim()
  if (!raw) return
  const display = raw.length > 28 ? `${raw.slice(0, 28)}…` : raw
  const fontSize = 22 + Math.min(10, Math.floor(display.length / 5))
  particles.push({
    x: 40 + Math.random() * Math.max(80, w - 80),
    y: -fontSize - Math.random() * 24,
    vx: (Math.random() - 0.5) * 0.22,
    vy: 0.28 + Math.random() * 0.38,
    rot: (Math.random() - 0.5) * 0.06,
    rotSpeed: 0,
    size: fontSize,
    opacity: 0.88,
    life: 0,
    maxLife: 420 + Math.random() * 160,
    kind: 'lyric',
    sway: Math.random() * Math.PI * 2,
    swaySpeed: 0.014 + Math.random() * 0.012,
    text: display,
    colorIdx: Math.floor(Math.random() * LYRIC_COLORS.length),
  })
  if (particles.length > 120) particles.shift()
}

function rgba(c: [number, number, number], a: number) {
  return `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${a})`
}

function drawPetal(ctx: CanvasRenderingContext2D, p: Particle) {
  const s = p.size
  const pal = getSakuraPalette()
  ctx.fillStyle = rgba(pal.petal, p.opacity)
  ctx.beginPath()
  for (let i = 0; i < 5; i++) {
    const a = (Math.PI * 2 * i) / 5 + p.rot * 0.2
    const px = Math.cos(a) * s * 0.55
    const py = Math.sin(a) * s * 0.38
    if (i === 0) ctx.moveTo(px, py)
    else ctx.lineTo(px, py)
  }
  ctx.closePath()
  ctx.fill()
  ctx.fillStyle = rgba(pal.center, p.opacity * 0.75)
  ctx.beginPath()
  ctx.ellipse(0, 0, s * 0.12, s * 0.2, 0, 0, Math.PI * 2)
  ctx.fill()
}

function drawLeaf(ctx: CanvasRenderingContext2D, p: Particle) {
  const s = p.size
  const pal = getLeafPalette()
  const g = ctx.createLinearGradient(-s, 0, s, 0)
  g.addColorStop(0, rgba(pal.start, p.opacity))
  g.addColorStop(0.5, rgba(pal.mid, p.opacity))
  g.addColorStop(1, rgba(pal.end, p.opacity * 0.9))
  ctx.fillStyle = g
  ctx.beginPath()
  ctx.moveTo(0, -s * 0.55)
  ctx.quadraticCurveTo(s * 0.65, -s * 0.1, 0, s * 0.55)
  ctx.quadraticCurveTo(-s * 0.65, -s * 0.1, 0, -s * 0.55)
  ctx.fill()
  ctx.strokeStyle = rgba(pal.vein, p.opacity * 0.55)
  ctx.lineWidth = 0.6
  ctx.beginPath()
  ctx.moveTo(0, -s * 0.45)
  ctx.lineTo(0, s * 0.45)
  ctx.stroke()
}

function lyricColor(p: Particle): [number, number, number] {
  const idx = p.colorIdx ?? 0
  return LYRIC_COLORS[idx % LYRIC_COLORS.length]!
}

function lyricOpacity(p: Particle): number {
  const enter = Math.min(1, p.life / 36)
  const exit = Math.min(1, (p.maxLife - p.life) / 72)
  return 0.9 * enter * exit
}

function drawLyric(ctx: CanvasRenderingContext2D, p: Particle) {
  if (!p.text) return
  const [r, g, b] = lyricColor(p)
  const a = lyricOpacity(p)
  if (a < 0.03) return

  ctx.font = `600 ${p.size}px var(--font-sans, "Noto Sans SC", sans-serif)`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = `rgb(${r}, ${g}, ${b})`
  ctx.globalAlpha = a
  ctx.fillText(p.text, 0, 0)
  ctx.globalAlpha = 1
}

function tick() {
  const canvas = canvasRef.value
  if (!canvas || !props.active || reducedMotion) {
    raf = 0
    return
  }

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const targetLevel = musicLevel.value
  smoothLevel += (targetLevel - smoothLevel) * 0.035
  const level = smoothLevel
  const speedMul = fallSpeedMul(level)
  const spawnGap = spawnEveryFrames(level)
  const lines = props.lyricLines ?? []
  const showLyrics = props.lyricsFall && lines.length > 0
  const sparseLyrics = lines.length <= 3
  const lyricGap = lyricSpawnEveryFrames(sparseLyrics)
  const maxLyrics = sparseLyrics ? MAX_LYRIC_FALLBACK : MAX_LYRIC_ON_SCREEN
  const lyricSpawnChance = sparseLyrics ? 0.28 : 0.4

  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const rect = canvas.getBoundingClientRect()
  const w = rect.width
  const h = rect.height
  if (w < 2 || h < 2) {
    raf = requestAnimationFrame(tick)
    return
  }

  if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
    canvas.width = Math.floor(w * dpr)
    canvas.height = Math.floor(h * dpr)
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }

  ctx.clearRect(0, 0, w, h)

  spawnTimer += 1
  if (spawnTimer % spawnGap === 0) spawn(w, h, level)

  if (showLyrics) {
    lyricSpawnTimer += 1
    if (lyricSpawnTimer % lyricGap === 0 && Math.random() < lyricSpawnChance) {
      const snippet = pickLyricSnippet(lines, props.currentTime ?? 0, sparseLyrics)
      if (snippet) spawnLyric(w, h, snippet, maxLyrics)
    }
  }

  particles = particles.filter((p) => {
    p.life += 1
    p.sway += p.swaySpeed

    if (p.kind === 'lyric') {
      p.x += p.vx + Math.sin(p.sway) * 0.18
      p.y += p.vy
      p.opacity = lyricOpacity(p)
    } else {
      const swayAmp = 0.25 + level * 0.35
      p.x += p.vx + Math.sin(p.sway) * swayAmp
      p.y += p.vy * speedMul
      p.rot += p.rotSpeed * (0.6 + level * 0.8)
      const fade = 1 - p.life / p.maxLife
      p.opacity = Math.max(0, fade * (0.75 + level * 0.18))
    }

    ctx.save()
    ctx.translate(p.x, p.y)
    ctx.rotate(p.rot)
    if (p.kind === 'sakura') drawPetal(ctx, p)
    else if (p.kind === 'leaf') drawLeaf(ctx, p)
    else drawLyric(ctx, p)
    ctx.restore()

    return p.y < h + 40 && p.life < p.maxLife && p.opacity > 0.02
  })

  raf = requestAnimationFrame(tick)
}

function start() {
  stop()
  if (!props.active || reducedMotion) return
  particles = []
  spawnTimer = 0
  lyricSpawnTimer = 0
  smoothLevel = 0
  raf = requestAnimationFrame(tick)
}

function stop() {
  if (raf) cancelAnimationFrame(raf)
  raf = 0
  particles = []
  const canvas = canvasRef.value
  const ctx = canvas?.getContext('2d')
  if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
}

let resizeObs: ResizeObserver | null = null

onMounted(() => {
  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  resizeObs = new ResizeObserver(() => {})
  if (canvasRef.value) resizeObs.observe(canvasRef.value)
})

onUnmounted(() => {
  stop()
  resizeObs?.disconnect()
})

watch(
  () => props.active,
  (v) => (v ? start() : stop()),
  { immediate: true },
)

watch(
  () => [props.theme, props.lyricsFall, props.lyricLines.length] as const,
  () => {
    if (props.active) {
      particles = []
      start()
    }
  },
)
</script>

<template>
  <canvas
    ref="canvasRef"
    class="music-particles"
    aria-hidden="true"
  />
</template>

<style scoped>
.music-particles {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
</style>

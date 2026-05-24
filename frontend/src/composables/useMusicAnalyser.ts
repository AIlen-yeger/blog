import { ref } from 'vue'

/** 当前音乐响度 0–1，供粒子等视觉特效使用 */
export const musicLevel = ref(0)

let audioCtx: AudioContext | null = null
let analyser: AnalyserNode | null = null
let source: MediaElementAudioSourceNode | null = null
let timeDomain: Uint8Array<ArrayBuffer> | null = null
let meterRaf = 0
let connectedEl: HTMLAudioElement | null = null

function computeRms(data: Uint8Array<ArrayBuffer>): number {
  let sum = 0
  for (let i = 0; i < data.length; i++) {
    const sample = (data[i] - 128) / 128
    sum += sample * sample
  }
  return Math.sqrt(sum / data.length)
}

function meterTick() {
  if (!analyser || !timeDomain) {
    musicLevel.value = 0
    return
  }

  analyser.getByteTimeDomainData(timeDomain)
  const instant = Math.min(1, computeRms(timeDomain) * 3.2)
  const prev = musicLevel.value
  const smooth = instant > prev ? 0.1 : 0.045
  musicLevel.value = prev + (instant - prev) * smooth

  meterRaf = requestAnimationFrame(meterTick)
}

export async function resumeMusicAudioContext() {
  if (audioCtx?.state === 'suspended') {
    await audioCtx.resume()
  }
}

export function connectMusicAnalyser(el: HTMLAudioElement) {
  if (connectedEl === el && source) return

  try {
    if (!audioCtx) audioCtx = new AudioContext()
    if (source) {
      try {
        source.disconnect()
      } catch {
        /* ignore */
      }
    }

    source = audioCtx.createMediaElementSource(el)
    analyser = audioCtx.createAnalyser()
    analyser.fftSize = 512
    analyser.smoothingTimeConstant = 0.82
    timeDomain = new Uint8Array(analyser.fftSize)

    source.connect(analyser)
    analyser.connect(audioCtx.destination)

    connectedEl = el
  } catch {
    /* 已连接过同一元素时部分浏览器会抛错，忽略后粒子用默认速度 */
  }
}

export function startMusicLevelMeter() {
  if (meterRaf) return
  void resumeMusicAudioContext()
  meterRaf = requestAnimationFrame(meterTick)
}

export function stopMusicLevelMeter() {
  if (meterRaf) cancelAnimationFrame(meterRaf)
  meterRaf = 0
  musicLevel.value = 0
}

export function useMusicAnalyser() {
  return { musicLevel }
}

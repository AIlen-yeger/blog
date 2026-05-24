import { computed, ref, watch } from 'vue'
import type { ParticleTheme, PlayOrderMode } from '@/types/music'
import {
  aboutMusicTracks,
  defaultParticleTheme,
  type MusicTrack,
} from '@/data/musicTracks'
import { resolveMusicSrc } from '@/utils/musicSrc'
import {
  connectMusicAnalyser,
  resumeMusicAudioContext,
  startMusicLevelMeter,
  stopMusicLevelMeter,
} from '@/composables/useMusicAnalyser'
import {
  clearMusicPlayback,
  loadMusicPlayback,
  saveMusicPlayback,
} from '@/utils/musicPlaybackStorage'

function formatTime(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

async function fetchMusicTracks(): Promise<MusicTrack[]> {
  try {
    const res = await fetch(`/music/manifest.json?t=${Date.now()}`)
    if (!res.ok) return aboutMusicTracks
    const data: unknown = await res.json()
    if (!Array.isArray(data) || data.length === 0) return aboutMusicTracks
    return data as MusicTrack[]
  } catch {
    return aboutMusicTracks
  }
}

function waitCanPlay(a: HTMLAudioElement): Promise<void> {
  if (a.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const ok = () => {
      cleanup()
      resolve()
    }
    const fail = () => {
      cleanup()
      reject(new Error('load'))
    }
    const cleanup = () => {
      a.removeEventListener('canplay', ok)
      a.removeEventListener('error', fail)
    }
    a.addEventListener('canplay', ok, { once: true })
    a.addEventListener('error', fail, { once: true })
  })
}

/** 全局单例，刷新页面后从 localStorage 恢复 */
const musicMode = ref(false)
const trackIndex = ref(0)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const loadError = ref('')
const audio = ref<HTMLAudioElement | null>(null)
const tracks = ref<MusicTrack[]>([...aboutMusicTracks])
const tracksLoaded = ref(false)
const loadedTrackId = ref<string | null>(null)
const restoreDone = ref(false)
const pendingSeek = ref(0)
const pendingResume = ref(false)
const playOrderMode = ref<PlayOrderMode>('sequential')
/** 随机模式下「上一首」用的历史栈（存曲目下标） */
const shuffleHistory = ref<number[]>([])

let listenersBound = false
let persistTimer: ReturnType<typeof setTimeout> | null = null
let tracksInitPromise: Promise<void> | null = null

const currentTrack = computed(() => tracks.value[trackIndex.value] ?? tracks.value[0])
const particleTheme = computed<ParticleTheme>(
  () => currentTrack.value?.particleTheme ?? defaultParticleTheme,
)
const progressPercent = computed(() =>
  duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0,
)
const timeLabel = computed(
  () => `${formatTime(currentTime.value)} / ${formatTime(duration.value)}`,
)

function persistPlaybackSoon() {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(() => {
    persistTimer = null
    if (!loadedTrackId.value && !isPlaying.value && currentTime.value <= 0) return
    saveMusicPlayback({
      trackId: currentTrack.value?.id ?? loadedTrackId.value,
      currentTime: currentTime.value,
      wasPlaying: isPlaying.value,
      musicMode: musicMode.value,
      playOrder: playOrderMode.value,
      updatedAt: Date.now(),
    })
  }, 400)
}

function persistPlaybackNow() {
  if (persistTimer) {
    clearTimeout(persistTimer)
    persistTimer = null
  }
  if (!loadedTrackId.value && !isPlaying.value && currentTime.value <= 0) {
    clearMusicPlayback()
    return
  }
  saveMusicPlayback({
    trackId: currentTrack.value?.id ?? loadedTrackId.value,
    currentTime: currentTime.value,
    wasPlaying: isPlaying.value,
    musicMode: musicMode.value,
    playOrder: playOrderMode.value,
    updatedAt: Date.now(),
  })
}

function applySavedSnapshot() {
  const saved = loadMusicPlayback()
  if (!saved?.trackId || tracks.value.length === 0) return

  const idx = tracks.value.findIndex((t) => t.id === saved.trackId)
  if (idx < 0) return

  trackIndex.value = idx
  musicMode.value = saved.musicMode
  playOrderMode.value = saved.playOrder ?? 'sequential'
  shuffleHistory.value = []
  pendingSeek.value = saved.currentTime
  pendingResume.value = saved.wasPlaying
  currentTime.value = saved.currentTime
}

async function ensureTracksLoaded() {
  if (tracksLoaded.value) return
  if (!tracksInitPromise) {
    tracksInitPromise = (async () => {
      tracks.value = await fetchMusicTracks()
      tracksLoaded.value = true
      if (trackIndex.value >= tracks.value.length) trackIndex.value = 0
      applySavedSnapshot()
    })()
  }
  await tracksInitPromise
}

function seekAudioTo(seconds: number) {
  const a = audio.value
  if (!a || !Number.isFinite(seconds)) return
  const max = a.duration && Number.isFinite(a.duration) ? a.duration : seconds
  a.currentTime = Math.min(Math.max(0, seconds), max)
  currentTime.value = a.currentTime
}

async function tryRestorePlayback() {
  if (restoreDone.value || !audio.value) return
  await ensureTracksLoaded()
  if (!pendingSeek.value && !pendingResume.value && !loadedTrackId.value) {
    restoreDone.value = true
    return
  }

  const track = currentTrack.value
  if (!track) {
    restoreDone.value = true
    return
  }

  loadCurrent()
  const a = audio.value
  if (!a) return

  try {
    await waitCanPlay(a)
    if (pendingSeek.value > 0) seekAudioTo(pendingSeek.value)
    duration.value = a.duration || duration.value

    if (pendingResume.value) {
      try {
        await resumeMusicAudioContext()
        await a.play()
        isPlaying.value = true
        startMusicLevelMeter()
      } catch {
        isPlaying.value = false
        stopMusicLevelMeter()
      }
    }
  } catch {
    /* 音频未就绪，保留进度供用户手动播放 */
  } finally {
    pendingSeek.value = 0
    pendingResume.value = false
    restoreDone.value = true
    persistPlaybackSoon()
  }
}

function attachAudioListeners(el: HTMLAudioElement) {
  el.addEventListener('timeupdate', onTimeUpdate)
  el.addEventListener('loadedmetadata', onLoadedMetadata)
  el.addEventListener('ended', onEnded)
  el.addEventListener('error', onAudioError)
  el.addEventListener('pause', onAudioPause)
  el.addEventListener('play', onAudioPlay)
}

function loadCurrent() {
  const a = audio.value
  const track = currentTrack.value
  if (!a || !track) return
  loadError.value = ''
  const sameTrack = loadedTrackId.value === track.id && !!a.src
  if (!sameTrack) {
    duration.value = 0
    a.src = resolveMusicSrc(track.src)
    a.load()
    loadedTrackId.value = track.id
    if (!restoreDone.value && pendingSeek.value > 0) {
      a.addEventListener(
        'loadedmetadata',
        () => seekAudioTo(pendingSeek.value),
        { once: true },
      )
    }
  }
}

async function toggleMusicMode() {
  await ensureTracksLoaded()

  if (musicMode.value) {
    musicMode.value = false
    persistPlaybackSoon()
    return
  }

  musicMode.value = true
  if (tracks.value.length === 0) {
    loadError.value = 'public/music/ 中没有找到 mp3，请放入音频后重启 dev'
    return
  }
  loadCurrent()
  persistPlaybackSoon()
}

async function play() {
  const a = audio.value
  const track = currentTrack.value
  if (!a || !track) return
  await ensureTracksLoaded()
  loadError.value = ''
  if (!a.src) loadCurrent()
  try {
    await waitCanPlay(a)
    await resumeMusicAudioContext()
    await a.play()
    isPlaying.value = true
    startMusicLevelMeter()
    persistPlaybackSoon()
  } catch {
    if (a.error?.code === MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED) {
      loadError.value = `无法加载：${track.title}（检查 public/music/ 内是否有该文件）`
    } else if (a.error) {
      loadError.value = '音频加载失败，请确认文件名与 manifest 一致'
    } else {
      loadError.value = '请点击播放按钮继续播放'
    }
    isPlaying.value = false
    stopMusicLevelMeter()
    persistPlaybackSoon()
  }
}

function pause() {
  audio.value?.pause()
  isPlaying.value = false
  stopMusicLevelMeter()
  persistPlaybackNow()
}

function togglePlayPause() {
  if (isPlaying.value) pause()
  else void play()
}

function stopAndReset() {
  const a = audio.value
  if (!a) return
  a.pause()
  a.currentTime = 0
  isPlaying.value = false
  currentTime.value = 0
  loadedTrackId.value = null
  pendingSeek.value = 0
  pendingResume.value = false
  clearMusicPlayback()
  stopMusicLevelMeter()
  shuffleHistory.value = []
}

function onTimeUpdate() {
  currentTime.value = audio.value?.currentTime ?? 0
  persistPlaybackSoon()
}

function onLoadedMetadata() {
  duration.value = audio.value?.duration ?? 0
  if (pendingSeek.value > 0 && audio.value) {
    seekAudioTo(pendingSeek.value)
  }
}

function onEnded() {
  nextTrack(true)
}

function onAudioError() {
  const name = currentTrack.value?.title ?? '当前曲目'
  loadError.value = `无法播放「${name}」，请确认文件在 public/music/ 且已重启 npm run dev`
  isPlaying.value = false
  persistPlaybackSoon()
}

function onAudioPause() {
  if (audio.value && !audio.value.ended) {
    isPlaying.value = false
    stopMusicLevelMeter()
    persistPlaybackSoon()
  }
}

function onAudioPlay() {
  isPlaying.value = true
  startMusicLevelMeter()
  persistPlaybackSoon()
}

function seekByPercent(percent: number) {
  const a = audio.value
  if (!a || !duration.value) return
  a.currentTime = (percent / 100) * duration.value
  currentTime.value = a.currentTime
  persistPlaybackSoon()
}

function pickRandomIndex(avoid?: number): number {
  const n = tracks.value.length
  if (n <= 1) return 0
  let idx = Math.floor(Math.random() * n)
  let guard = 0
  while (idx === avoid && guard < 12) {
    idx = Math.floor(Math.random() * n)
    guard += 1
  }
  return idx
}

function goToTrackIndex(index: number, auto = false) {
  if (tracks.value.length === 0) return
  trackIndex.value = ((index % tracks.value.length) + tracks.value.length) % tracks.value.length
  pendingSeek.value = 0
  loadCurrent()
  if (auto || isPlaying.value) void play()
  else persistPlaybackSoon()
}

function setPlayOrderMode(mode: PlayOrderMode) {
  if (playOrderMode.value === mode) return
  playOrderMode.value = mode
  shuffleHistory.value = []
  persistPlaybackSoon()
}

function togglePlayOrderMode() {
  setPlayOrderMode(playOrderMode.value === 'sequential' ? 'shuffle' : 'sequential')
}

function prevTrack() {
  if (tracks.value.length === 0) return
  if (playOrderMode.value === 'shuffle') {
    const prev = shuffleHistory.value.pop()
    if (prev === undefined) {
      goToTrackIndex(pickRandomIndex(trackIndex.value))
      return
    }
    goToTrackIndex(prev)
    return
  }
  goToTrackIndex(trackIndex.value - 1)
}

function nextTrack(auto = false) {
  if (tracks.value.length === 0) return
  if (playOrderMode.value === 'shuffle') {
    shuffleHistory.value.push(trackIndex.value)
    goToTrackIndex(pickRandomIndex(trackIndex.value), auto)
    return
  }
  goToTrackIndex(trackIndex.value + 1, auto)
}

function bindAudio(el: HTMLAudioElement | null) {
  audio.value = el
  if (!el) return
  if (!listenersBound) {
    attachAudioListeners(el)
    listenersBound = true
  }
  connectMusicAnalyser(el)
  void tryRestorePlayback()
}

if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', persistPlaybackNow)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') persistPlaybackNow()
  })
}

watch(trackIndex, () => {
  if (musicMode.value && restoreDone.value) loadCurrent()
})

export function useAboutMusic() {
  void ensureTracksLoaded()

  return {
    musicMode,
    tracks,
    currentTrack,
    particleTheme,
    trackIndex,
    isPlaying,
    currentTime,
    duration,
    progressPercent,
    timeLabel,
    loadError,
    playOrderMode,
    setPlayOrderMode,
    togglePlayOrderMode,
    bindAudio,
    toggleMusicMode,
    togglePlayPause,
    stopAndReset,
    prevTrack,
    nextTrack,
    onTimeUpdate,
    onLoadedMetadata,
    onEnded,
    onAudioError,
    seekByPercent,
    formatTime,
  }
}

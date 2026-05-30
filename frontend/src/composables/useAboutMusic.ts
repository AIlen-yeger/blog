import { computed, ref, watch } from 'vue'
import type { ParticleTheme, PlayOrderMode } from '@/types/music'
import {
  aboutMusicTracks,
  defaultParticleTheme,
  isQqMusicTrack,
  mergeMusicTracks,
  type MusicTrack,
} from '@/data/musicTracks'
import { resolveMusicSrc } from '@/utils/musicSrc'
import {
  connectMusicAnalyser,
  resumeMusicAudioContext,
  startMusicLevelMeter,
  stopMusicLevelMeter,
} from '@/composables/useMusicAnalyser'
import { loadBlogMusicTracks, MUSIC_TRACKS_CHANGED } from '@/composables/useUserMusicTracks'
import { MUSIC_PLAY_COUNT_UPDATED, MIN_EFFECTIVE_PLAY_SECONDS, recordTrackPlay } from '@/composables/useMusicPlayRecord'
import {
  globalQqNext,
  globalQqPrev,
  hydrateGlobalQqFromStorage,
  markQqPlaying,
  applyQqTeleportSlot,
  prepareBlogHandoff,
  setGlobalQqTracks,
  setQqTeleportSlot,
  syncQqTeleportSlot,
  useGlobalQqPlayer,
} from '@/composables/useGlobalQqPlayer'
import {
  clearMusicPlayback,
  loadMusicPlayback,
  saveMusicPlayback,
  type MusicPlaybackSnapshot,
} from '@/utils/musicPlaybackStorage'

function formatTime(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return '0:00'
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

async function fetchMusicTracks(): Promise<MusicTrack[]> {
  let mp3Tracks: MusicTrack[] = []
  try {
    const res = await fetch(`/music/manifest.json?t=${Date.now()}`)
    if (res.ok) {
      const data: unknown = await res.json()
      if (Array.isArray(data)) {
        mp3Tracks = (data as MusicTrack[]).filter((t) => !isQqMusicTrack(t))
      }
    }
  } catch {
    /* 无 manifest 时仍尝试 API 曲目 */
  }

  const qqFromApi = await loadBlogMusicTracks()
  if (qqFromApi.length > 0) {
    return [...mp3Tracks, ...qqFromApi]
  }
  return mergeMusicTracks(mp3Tracks)
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
/** QQ 曲目：返回资料页后保持 iframe 挂载以继续播放 */
const qqBackgroundActive = ref(false)
/** 随机模式下「上一首」用的历史栈（存曲目下标） */
const shuffleHistory = ref<number[]>([])
/** 本地 mp3：当前曲目在本轮切歌后是否已计入有效播放 */
const localPlayCountedForTrackId = ref<string | null>(null)

let listenersBound = false
let persistTimer: ReturnType<typeof setTimeout> | null = null
let tracksInitPromise: Promise<void> | null = null

export function invalidateMusicTracksCache() {
  tracksLoaded.value = false
  tracksInitPromise = null
}

const currentTrack = computed(() => tracks.value[trackIndex.value] ?? tracks.value[0])
const isQqTrack = computed(() => isQqMusicTrack(currentTrack.value))
const globalQqState = useGlobalQqPlayer()

const embedPlaybackActive = computed(
  () => isQqTrack.value && (musicMode.value || qqBackgroundActive.value),
)
const visualPlaybackActive = computed(
  () =>
    isPlaying.value ||
    (isQqTrack.value && globalQqState.qqPlaying.value),
)
const particleTheme = computed<ParticleTheme>(
  () => currentTrack.value?.particleTheme ?? defaultParticleTheme,
)
const progressPercent = computed(() =>
  duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0,
)
const timeLabel = computed(
  () => `${formatTime(currentTime.value)} / ${formatTime(duration.value)}`,
)

function buildPlaybackSnapshot(): MusicPlaybackSnapshot | null {
  const trackId = currentTrack.value?.id ?? loadedTrackId.value
  if (!trackId) {
    if (!isPlaying.value && currentTime.value <= 0 && !musicMode.value) return null
    return null
  }
  return {
    trackId,
    currentTime: currentTime.value,
    wasPlaying: isPlaying.value,
    musicMode: musicMode.value,
    playOrder: playOrderMode.value,
    updatedAt: Date.now(),
  }
}

function persistPlaybackSoon() {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(() => {
    persistTimer = null
    const snapshot = buildPlaybackSnapshot()
    if (!snapshot) {
      if (!isPlaying.value && currentTime.value <= 0 && !musicMode.value) {
        clearMusicPlayback()
      }
      return
    }
    saveMusicPlayback(snapshot)
  }, 400)
}

function persistPlaybackNow() {
  if (persistTimer) {
    clearTimeout(persistTimer)
    persistTimer = null
  }
  const snapshot = buildPlaybackSnapshot()
  if (!snapshot) {
    if (!isPlaying.value && currentTime.value <= 0 && !musicMode.value) {
      clearMusicPlayback()
    }
    return
  }
  saveMusicPlayback(snapshot)
}

function applySavedSnapshot(opts?: { restoreMusicUi?: boolean }) {
  const saved = loadMusicPlayback()
  if (!saved?.trackId || tracks.value.length === 0) return

  const idx = tracks.value.findIndex((t) => t.id === saved.trackId)
  if (idx < 0) return

  trackIndex.value = idx
  if (opts?.restoreMusicUi !== false) {
    musicMode.value = saved.musicMode && saved.wasPlaying
  }
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
      const qqList = tracks.value.filter((t) => isQqMusicTrack(t))
      if (qqList.length > 0) {
        hydrateGlobalQqFromStorage(qqList)
      }
      applySavedSnapshot()
      const saved = loadMusicPlayback()
      if (saved?.wasPlaying && isQqMusicTrack(tracks.value[trackIndex.value])) {
        qqBackgroundActive.value = !saved.musicMode
        markQqPlaying(true)
      }
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
  if (!track) return
  loadError.value = ''
  if (isQqMusicTrack(track)) {
    a?.pause()
    isPlaying.value = false
    stopMusicLevelMeter()
    loadedTrackId.value = track.id
    currentTime.value = 0
    duration.value = 0
    return
  }
  if (!a) return
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
    if (isQqTrack.value) {
      qqBackgroundActive.value = true
      setQqTeleportSlot('hidden')
    }
    persistPlaybackSoon()
    return
  }

  musicMode.value = true
  if (isQqTrack.value) setQqTeleportSlot('about')
  if (tracks.value.length === 0) {
    loadError.value = '暂无可播放的音乐'
    return
  }
  loadCurrent()
  persistPlaybackSoon()
}

async function play() {
  const track = currentTrack.value
  if (!track) return
  await ensureTracksLoaded()
  loadError.value = ''
  if (isQqMusicTrack(track)) {
    musicMode.value = true
    qqBackgroundActive.value = true
    setQqTeleportSlot(musicMode.value ? 'about' : 'hidden')
    loadCurrent()
    persistPlaybackSoon()
    return
  }
  const a = audio.value
  if (!a) return
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
      loadError.value = `无法加载「${track.title}」，请稍后再试`
    } else if (a.error) {
      loadError.value = '音频加载失败，请稍后再试'
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
  if (isQqTrack.value) {
    musicMode.value = true
    loadCurrent()
    return
  }
  if (isPlaying.value) pause()
  else void play()
}

function stopAndReset() {
  const a = audio.value
  if (a) {
    a.pause()
    a.currentTime = 0
  }
  isPlaying.value = false
  currentTime.value = 0
  loadedTrackId.value = null
  pendingSeek.value = 0
  pendingResume.value = false
  qqBackgroundActive.value = false
  if (isQqTrack.value) markQqPlaying(false)
  clearMusicPlayback()
  stopMusicLevelMeter()
  shuffleHistory.value = []
}

function maybeCountLocalEffectivePlay() {
  const track = currentTrack.value
  const id = track?.id?.trim()
  if (!id || isQqMusicTrack(track)) return
  if (!isPlaying.value) return
  if (currentTime.value < MIN_EFFECTIVE_PLAY_SECONDS) return
  if (localPlayCountedForTrackId.value === id) return
  localPlayCountedForTrackId.value = id
  void recordTrackPlay(id)
}

function onTimeUpdate() {
  currentTime.value = audio.value?.currentTime ?? 0
  maybeCountLocalEffectivePlay()
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
  loadError.value = `无法播放「${name}」，请稍后再试`
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
  if (isQqTrack.value) return
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
  localPlayCountedForTrackId.value = null
  const next = tracks.value[trackIndex.value]
  if (isQqMusicTrack(next)) {
    const qqList = tracks.value.filter((t) => isQqMusicTrack(t))
    const qi = qqList.findIndex((t) => t.id === next.id)
    if (qi >= 0) {
      const g = useGlobalQqPlayer()
      g.trackIndex.value = qi
    }
    if (musicMode.value) setQqTeleportSlot('about')
    else if (qqBackgroundActive.value) setQqTeleportSlot('hidden')
  } else {
    qqBackgroundActive.value = false
    setQqTeleportSlot('landing')
  }
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
  if (isQqTrack.value) {
    globalQqPrev()
    const g = useGlobalQqPlayer()
    const idx = tracks.value.findIndex((t) => t.id === g.currentTrack.value?.id)
    if (idx >= 0) goToTrackIndex(idx)
    return
  }
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
  if (isQqTrack.value) {
    globalQqNext()
    const g = useGlobalQqPlayer()
    const idx = tracks.value.findIndex((t) => t.id === g.currentTrack.value?.id)
    if (idx >= 0) goToTrackIndex(idx, auto)
    return
  }
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
  window.addEventListener(MUSIC_TRACKS_CHANGED, () => {
    invalidateMusicTracksCache()
    void ensureTracksLoaded()
  })
  window.addEventListener(MUSIC_PLAY_COUNT_UPDATED, (ev) => {
    const detail = (ev as CustomEvent<{ trackId: string; playCount: number }>).detail
    if (!detail?.trackId) return
    tracks.value = tracks.value.map((t) =>
      t.id === detail.trackId ? { ...t, playCount: detail.playCount } : t,
    )
  })
}

watch(trackIndex, () => {
  if (tracksLoaded.value) persistPlaybackSoon()
  if (musicMode.value && restoreDone.value) loadCurrent()
})

watch(musicMode, (open) => {
  if (!isQqTrack.value) return
  if (open) void applyQqTeleportSlot('about')
  else if (qqBackgroundActive.value) void applyQqTeleportSlot('hidden')
  else void applyQqTeleportSlot('landing')
})

/** 着陆页切歌后与全局播放列表同步（进入博客时沿用同一首） */
export async function syncGlobalMusicTrackId(trackId: string) {
  await ensureTracksLoaded()
  const idx = tracks.value.findIndex((t) => t.id === trackId)
  if (idx >= 0) trackIndex.value = idx
  const qqList = tracks.value.filter((t) => isQqMusicTrack(t))
  setGlobalQqTracks(qqList)
  const qqIdx = qqList.findIndex((t) => t.id === trackId)
  if (qqIdx >= 0) {
    const g = useGlobalQqPlayer()
    g.trackIndex.value = qqIdx
  }
  persistPlaybackSoon()
}

/** 着陆页滑入博客前：保存 QQ 播放进度并屏外续播 */
export function selectTrackById(trackId: string) {
  const idx = tracks.value.findIndex((t) => t.id === trackId)
  if (idx >= 0) goToTrackIndex(idx)
}

export async function handoffLandingMusicToBlog() {
  const g = useGlobalQqPlayer()
  const activelyPlaying = g.qqPlaying.value

  musicMode.value = false
  qqBackgroundActive.value = false

  prepareBlogHandoff()
  syncQqTeleportSlot('hidden')

  const globalTrack = g.currentTrack.value
  if (globalTrack && g.tracks.value.length > 0) {
    setGlobalQqTracks(g.tracks.value)
    const inList = tracks.value.some((t) => t.id === globalTrack.id)
    if (!inList) {
      const mp3 = tracks.value.filter((t) => !isQqMusicTrack(t))
      tracks.value = [...mp3, ...g.tracks.value]
    }
    selectTrackById(globalTrack.id)
  }

  await applyQqTeleportSlot('hidden')

  if (activelyPlaying && g.songId.value) {
    musicMode.value = true
    qqBackgroundActive.value = true
    markQqPlaying(true)
  } else {
    markQqPlaying(false)
  }

  void ensureTracksLoaded().then(async () => {
    applySavedSnapshot({ restoreMusicUi: false })

    if (activelyPlaying && g.songId.value) {
      musicMode.value = true
      qqBackgroundActive.value = true
      markQqPlaying(true)
      await applyQqTeleportSlot('about')
    } else {
      musicMode.value = false
      qqBackgroundActive.value = false
      markQqPlaying(false)
      syncQqTeleportSlot('hidden')
    }
  })
}

/** 从博客回到着陆页：重置 About 音乐 UI，避免 Teleport 仍指向 #about-qq-slot */
export function resetAboutMusicForLanding() {
  musicMode.value = false
  qqBackgroundActive.value = false
  syncQqTeleportSlot('landing')
}

export function useAboutMusic() {
  void ensureTracksLoaded()
  const globalQq = useGlobalQqPlayer()

  return {
    globalQq,
    musicMode,
    tracks,
    currentTrack,
    isQqTrack,
    qqBackgroundActive,
    embedPlaybackActive,
    visualPlaybackActive,
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
    selectTrackById,
    onTimeUpdate,
    onLoadedMetadata,
    onEnded,
    onAudioError,
    seekByPercent,
    formatTime,
  }
}

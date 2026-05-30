import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import {
  MIN_EFFECTIVE_PLAY_SECONDS,
  recordTrackPlay,
} from '@/composables/useMusicPlayRecord'
import type { MusicTrack } from '@/data/musicTracks'
import { isQqMusicTrack } from '@/data/musicTracks'
import {
  findTrackIndexById,
  loadMusicPlayback,
  saveMusicPlayback,
} from '@/utils/musicPlaybackStorage'

/** Teleport 挂载点：着陆页 / 关于页播放器 / 屏外续播 */
export type QqTeleportSlot = 'landing' | 'about' | 'hidden'

const teleportSlot = ref<QqTeleportSlot>('landing')
/** 实际 Teleport 目标（目标节点不存在时回退到屏外，避免 iframe 被销毁） */
export const qqTeleportTo = ref('#qq-music-offscreen')
const tracks = ref<MusicTrack[]>([])
const trackIndex = ref(0)
const currentTime = ref(0)
const duration = ref(0)
const qqPlaying = ref(false)
/** 当前曲目在本轮切歌后是否已计入有效播放 */
const playCountedForTrackId = ref<string | null>(null)

let tickTimer: ReturnType<typeof setInterval> | null = null
let persistTimer: ReturnType<typeof setTimeout> | null = null

const currentTrack = computed(() => tracks.value[trackIndex.value])
const songId = computed(() => currentTrack.value?.qqSongId ?? '')
const active = computed(() => !!songId.value && tracks.value.length > 0)

function persistSoon() {
  if (persistTimer) clearTimeout(persistTimer)
  persistTimer = setTimeout(() => {
    persistTimer = null
    const track = currentTrack.value
    if (!track?.id) return
    saveMusicPlayback({
      trackId: track.id,
      currentTime: currentTime.value,
      wasPlaying: qqPlaying.value,
      musicMode: teleportSlot.value === 'about',
      updatedAt: Date.now(),
    })
  }, 350)
}

function maybeCountEffectivePlay() {
  const track = currentTrack.value
  const id = track?.id?.trim()
  if (!id || !qqPlaying.value) return
  if (currentTime.value < MIN_EFFECTIVE_PLAY_SECONDS) return
  if (playCountedForTrackId.value === id) return
  playCountedForTrackId.value = id
  void recordTrackPlay(id)
}

function startTick() {
  if (tickTimer) return
  tickTimer = setInterval(() => {
    if (!qqPlaying.value) return
    const max = duration.value > 0 ? duration.value : Infinity
    if (currentTime.value < max) {
      currentTime.value = Math.min(currentTime.value + 1, max)
      maybeCountEffectivePlay()
      persistSoon()
    }
  }, 1000)
}

function stopTick() {
  if (tickTimer) {
    clearInterval(tickTimer)
    tickTimer = null
  }
}

function applyDurationFromTrack(track?: MusicTrack) {
  const sec = track?.durationSec
  duration.value = sec && sec > 0 ? sec : duration.value
}

function restoreFromStorage(list: MusicTrack[]) {
  const saved = loadMusicPlayback()
  if (!saved?.trackId || list.length === 0) return
  const idx = findTrackIndexById(list, saved.trackId)
  if (idx >= 0) trackIndex.value = idx
  currentTime.value = saved.currentTime ?? 0
  qqPlaying.value = !!saved.wasPlaying
  applyDurationFromTrack(list[trackIndex.value])
}

export function setGlobalQqTracks(list: MusicTrack[]) {
  const qq = list.filter((t) => isQqMusicTrack(t))
  tracks.value = qq
  if (qq.length === 0) {
    trackIndex.value = 0
    return
  }
  if (trackIndex.value >= qq.length) trackIndex.value = 0
  const saved = loadMusicPlayback()
  if (saved?.trackId) {
    const idx = findTrackIndexById(qq, saved.trackId)
    if (idx >= 0) trackIndex.value = idx
  }
  applyDurationFromTrack(qq[trackIndex.value])
}

export function hydrateGlobalQqFromStorage(list: MusicTrack[]) {
  setGlobalQqTracks(list)
  restoreFromStorage(tracks.value)
  if (qqPlaying.value) startTick()
}

function resolveTeleportSelector(slot: QqTeleportSlot): string {
  if (slot === 'landing' && document.querySelector('#landing-qq-slot')) {
    return '#landing-qq-slot'
  }
  if (slot === 'about' && document.querySelector('#about-qq-slot')) {
    return '#about-qq-slot'
  }
  return '#qq-music-offscreen'
}

/** 切换挂载点；DOM 未就绪时先挂到屏外，避免登录页卸载后播放器消失 */
export async function applyQqTeleportSlot(slot: QqTeleportSlot) {
  teleportSlot.value = slot
  await nextTick()
  qqTeleportTo.value = resolveTeleportSelector(slot)
  if (slot !== 'hidden' && qqTeleportTo.value === '#qq-music-offscreen') {
    await new Promise((r) => setTimeout(r, 80))
    await nextTick()
    qqTeleportTo.value = resolveTeleportSelector(slot)
  }
  persistSoon()
}

export function setQqTeleportSlot(slot: QqTeleportSlot) {
  void applyQqTeleportSlot(slot)
}

export function markQqPlaying(playing = true) {
  qqPlaying.value = playing
  if (playing) startTick()
  else stopTick()
  persistSoon()
}

export function globalQqPrev() {
  const n = tracks.value.length
  if (n <= 1) return
  trackIndex.value = (trackIndex.value - 1 + n) % n
  currentTime.value = 0
  applyDurationFromTrack(currentTrack.value)
  persistSoon()
}

export function globalQqNext() {
  const n = tracks.value.length
  if (n <= 1) return
  trackIndex.value = (trackIndex.value + 1) % n
  currentTime.value = 0
  applyDurationFromTrack(currentTrack.value)
  persistSoon()
}

export function globalQqSelectIndex(index: number) {
  if (tracks.value.length === 0) return
  trackIndex.value = ((index % tracks.value.length) + tracks.value.length) % tracks.value.length
  currentTime.value = 0
  applyDurationFromTrack(currentTrack.value)
  persistSoon()
}

export function prepareBlogHandoff() {
  const track = currentTrack.value
  if (!track?.id) return
  saveMusicPlayback({
    trackId: track.id,
    currentTime: currentTime.value,
    wasPlaying: qqPlaying.value,
    musicMode: true,
    updatedAt: Date.now(),
  })
}

watch(
  () => currentTrack.value?.id,
  (id, prev) => {
    if (id !== prev) {
      playCountedForTrackId.value = null
    }
    if (id && id !== prev) currentTime.value = 0
    applyDurationFromTrack(currentTrack.value)
    persistSoon()
  },
)

watch(songId, () => {
  applyDurationFromTrack(currentTrack.value)
})

onUnmounted(() => {
  stopTick()
})

export function useGlobalQqPlayer() {
  return {
    teleportSlot,
    teleportTarget: qqTeleportTo,
    tracks,
    trackIndex,
    currentTrack,
    songId,
    active,
    currentTime,
    duration,
    qqPlaying,
    setGlobalQqTracks,
    hydrateGlobalQqFromStorage,
    setQqTeleportSlot,
    markQqPlaying,
    globalQqPrev,
    globalQqNext,
    globalQqSelectIndex,
    prepareBlogHandoff,
  }
}

import { type ComputedRef, onMounted, ref, watch } from 'vue'
import type { MusicTrack } from '@/data/musicTracks'
import {
  findTrackIndexById,
  loadMusicPlayback,
  saveCurrentTrackId,
} from '@/utils/musicPlaybackStorage'

/**
 * 根据 localStorage 恢复/保存当前曲目下标（与 useAboutMusic 共用 blog:music-playback）
 */
export function usePersistedTrackIndex(
  tracks: ComputedRef<MusicTrack[]>,
  fallbackIndex: () => number = () => 0,
) {
  const currentIndex = ref(0)
  let ready = false

  function indexFromStorage(): number {
    const list = tracks.value
    if (list.length === 0) return 0
    const saved = loadMusicPlayback()
    const idx = findTrackIndexById(list, saved?.trackId)
    if (idx >= 0) return idx
    const fb = fallbackIndex()
    return fb >= 0 && fb < list.length ? fb : 0
  }

  function hydrate() {
    currentIndex.value = indexFromStorage()
    ready = true
    const track = tracks.value[currentIndex.value]
    if (track?.id) saveCurrentTrackId(track.id)
  }

  if (typeof window !== 'undefined') {
    hydrate()
  }

  onMounted(() => {
    hydrate()
  })

  watch(tracks, () => {
    if (currentIndex.value >= tracks.value.length) {
      currentIndex.value = 0
    }
    if (ready) {
      const idx = indexFromStorage()
      if (idx !== currentIndex.value) currentIndex.value = idx
    }
  })

  watch(currentIndex, () => {
    if (!ready) return
    const track = tracks.value[currentIndex.value]
    if (track?.id) saveCurrentTrackId(track.id)
  })

  return { currentIndex, hydrate }
}

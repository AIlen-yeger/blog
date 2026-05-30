import { ref } from 'vue'
import { deleteMusicTrack, fetchMyMusicTracks, fetchSiteOwnerMusicTracks } from '@/api/music'
import { useMockApi } from '@/api/http'
import { aboutMusicTracks, isQqMusicTrack, type MusicTrack } from '@/data/musicTracks'
import { hasValidSession } from '@/composables/useSession'
import { setGlobalQqTracks } from '@/composables/useGlobalQqPlayer'

export const MUSIC_TRACKS_CHANGED = 'music:tracks-changed'

/** 着陆页从 API 拉取的 QQ 曲目 */
export const landingMusicTracks = ref<MusicTrack[]>([])
export const landingMusicLoading = ref(false)

export function notifyMusicTracksChanged() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(MUSIC_TRACKS_CHANGED))
  }
}

/** 从 API 加载着陆页音乐（已登录优先自己的列表，否则站点主人） */
export async function loadLandingMusicTracks(): Promise<MusicTrack[]> {
  if (useMockApi()) {
    landingMusicTracks.value = aboutMusicTracks.filter((t) => isQqMusicTrack(t))
    return landingMusicTracks.value
  }

  landingMusicLoading.value = true
  try {
    let list: MusicTrack[]
    if (hasValidSession()) {
      try {
        list = await fetchMyMusicTracks()
      } catch {
        list = await fetchSiteOwnerMusicTracks()
      }
    } else {
      list = await fetchSiteOwnerMusicTracks()
    }
    landingMusicTracks.value = list.filter((t) => isQqMusicTrack(t))
    setGlobalQqTracks(landingMusicTracks.value)
    return landingMusicTracks.value
  } catch {
    landingMusicTracks.value = []
    return []
  } finally {
    landingMusicLoading.value = false
  }
}

export async function removeMusicTrack(track: MusicTrack): Promise<void> {
  if (useMockApi()) {
    landingMusicTracks.value = landingMusicTracks.value.filter((t) => t.id !== track.id)
    setGlobalQqTracks(landingMusicTracks.value)
    notifyMusicTracksChanged()
    return
  }
  await deleteMusicTrack(track.id)
  notifyMusicTracksChanged()
  await loadLandingMusicTracks()
}

/** About 页 / 博客内播放器：拉取当前用户或站点主人 QQ 曲目 */
export async function loadBlogMusicTracks(): Promise<MusicTrack[]> {
  if (useMockApi()) {
    return aboutMusicTracks.filter((t) => isQqMusicTrack(t))
  }
  try {
    if (hasValidSession()) {
      return (await fetchMyMusicTracks()).filter((t) => isQqMusicTrack(t))
    }
    return (await fetchSiteOwnerMusicTracks()).filter((t) => isQqMusicTrack(t))
  } catch {
    return []
  }
}

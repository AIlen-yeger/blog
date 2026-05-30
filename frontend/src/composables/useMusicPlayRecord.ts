import { post, useMockApi } from '@/api/http'
import { landingMusicTracks } from '@/composables/useUserMusicTracks'

export const MUSIC_PLAY_COUNT_UPDATED = 'music:play-count-updated'

const DEBOUNCE_MS = 90_000
const DEBOUNCE_KEY = 'blog:music-play-debounce'

/** 有效播放时长阈值（秒）：累计收听超过该时长才计 1 次播放 */
export const MIN_EFFECTIVE_PLAY_SECONDS = Number(
  import.meta.env.VITE_MUSIC_PLAY_MIN_SECONDS ?? 30,
)

/** 本地列表里更新播放次数（避免整表重拉） */
export function patchTrackPlayCount(trackId: string, playCount: number) {
  landingMusicTracks.value = landingMusicTracks.value.map((t) =>
    t.id === trackId ? { ...t, playCount } : t,
  )
  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent(MUSIC_PLAY_COUNT_UPDATED, { detail: { trackId, playCount } }),
    )
  }
}

/**
 * 上报一次播放（同一曲目 90 秒内不重复计数，防刷新刷量）。
 * 仅对数据库中的曲目 id 有效（API 列表），静态 fallback 曲目会静默跳过。
 * 一般由播放器在累计收听达到 MIN_EFFECTIVE_PLAY_SECONDS 后调用。
 */
export async function recordTrackPlay(trackId: string | undefined | null): Promise<void> {
  const id = trackId?.trim()
  if (!id || useMockApi()) return
  if (id.startsWith('qq-')) return

  try {
    const raw = sessionStorage.getItem(DEBOUNCE_KEY)
    if (raw) {
      const [lastId, ts] = raw.split('|')
      if (lastId === id && Date.now() - Number(ts) < DEBOUNCE_MS) return
    }
    sessionStorage.setItem(DEBOUNCE_KEY, `${id}|${Date.now()}`)

    const updated = await post<{ playCount?: number }>(
      `/music/tracks/${encodeURIComponent(id)}/play`,
      {},
      { auth: false },
    )
    if (typeof updated?.playCount === 'number') {
      patchTrackPlayCount(id, updated.playCount)
    }
  } catch {
    /* 统计失败不影响播放 */
  }
}

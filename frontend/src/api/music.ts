import { del, get, post } from '@/api/http'
import type { MusicTrack } from '@/data/musicTracks'

export interface ApiMusicTrack {
  id: string
  title: string
  artist: string
  src: string
  qqSongId: string
  durationSec?: number | null
  sortOrder?: number
  sourceUrl?: string | null
  playCount?: number | null
}

export interface AddMusicTrackPayload {
  shareUrl?: string
  qqSongId?: string
  title?: string
  artist?: string
  src?: string
  durationSec?: number
}

export function apiTrackToMusicTrack(d: ApiMusicTrack): MusicTrack {
  return {
    id: d.id,
    title: d.title,
    artist: d.artist,
    src: d.src || '',
    qqSongId: d.qqSongId,
    durationSec: d.durationSec ?? undefined,
    playCount: d.playCount ?? 0,
  }
}

/** 着陆页：站点主人公开列表 */
export async function fetchSiteOwnerMusicTracks(): Promise<MusicTrack[]> {
  const list = await get<ApiMusicTrack[]>('/music/site-owner', { auth: false })
  return list.map(apiTrackToMusicTrack)
}

/** 当前登录用户列表 */
export async function fetchMyMusicTracks(): Promise<MusicTrack[]> {
  const list = await get<ApiMusicTrack[]>('/music/me')
  return list.map(apiTrackToMusicTrack)
}

export async function parseQqMusicShareUrl(shareUrl: string): Promise<{ qqSongId: string; shareUrl: string }> {
  return post<{ qqSongId: string; shareUrl: string }>('/music/parse', { shareUrl })
}

export async function addMusicTrack(payload: AddMusicTrackPayload): Promise<MusicTrack> {
  const created = await post<ApiMusicTrack>('/music/tracks', payload)
  return apiTrackToMusicTrack(created)
}

export async function deleteMusicTrack(id: string): Promise<void> {
  await del<void>(`/music/tracks/${encodeURIComponent(id)}`)
}

import type { PlayOrderMode } from '@/types/music'

export interface MusicPlaybackSnapshot {
  trackId: string | null
  currentTime: number
  wasPlaying: boolean
  musicMode: boolean
  playOrder?: PlayOrderMode
  updatedAt: number
}

const STORAGE_KEY = 'blog:music-playback'

export function loadMusicPlayback(): MusicPlaybackSnapshot | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as MusicPlaybackSnapshot
    if (!data || typeof data !== 'object') return null
    return {
      trackId: typeof data.trackId === 'string' ? data.trackId : null,
      currentTime: Number.isFinite(data.currentTime) ? Math.max(0, data.currentTime) : 0,
      wasPlaying: !!data.wasPlaying,
      musicMode: !!data.musicMode,
      playOrder: data.playOrder === 'shuffle' ? 'shuffle' : 'sequential',
      updatedAt: data.updatedAt ?? 0,
    }
  } catch {
    return null
  }
}

export function saveMusicPlayback(snapshot: MusicPlaybackSnapshot) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot))
  } catch {
    /* 存储满或隐私模式 */
  }
}

export function clearMusicPlayback() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

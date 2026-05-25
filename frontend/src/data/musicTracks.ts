import type { ParticleTheme } from '@/types/music'

export interface MusicTrack {
  id: string
  title: string
  artist: string
  /** 放在 public/music/ 下的路径，或完整 https URL（CDN/OSS）；QQ 曲目可留空 */
  src: string
  /** QQ 音乐官方外链 songid（与 src 二选一，优先使用嵌入播放器） */
  qqSongId?: string
  /** 播放时粒子主题；不填则用 defaultParticleTheme */
  particleTheme?: ParticleTheme
  /** 同目录 .lrc 路径；不填则按音频文件名自动匹配 */
  lyricsSrc?: string
}

const envTheme = import.meta.env.VITE_MUSIC_PARTICLE_THEME as ParticleTheme | undefined
const validThemes = new Set<ParticleTheme>(['sakura', 'leaf', 'mixed'])

/** 将 mp3 放入 public/music/ 后即可播放；也可改为 CDN 完整 URL */
export const defaultParticleTheme: ParticleTheme =
  envTheme && validThemes.has(envTheme) ? envTheme : 'mixed'

/**
 * 无 manifest 时的占位；有 mp3 时由 scripts/musicManifest 自动生成 manifest.json。
 * 带 qqSongId 的条目会合并进播放列表，并使用 QQ 官方 iframe 播放器。
 * songid：在 y.qq.com 分享链接里 ?songid= 后面的数字。
 */
export const aboutMusicTracks: MusicTrack[] = [
  {
    id: 'qq-3583378',
    title: 'Sacred Play Secret Place',
    artist: 'matryoshka',
    src: '',
    qqSongId: '3583378',
  },
  {
    id: 'qq-301860905',
    title: 'Rainy proof',
    artist: 'HACHI',
    src: '',
    qqSongId: '301860905'
  }
]

export function isQqMusicTrack(track: MusicTrack | undefined): boolean {
  return !!track?.qqSongId?.trim()
}

/** 合并本地 manifest 与静态 QQ 曲目 */
export function mergeMusicTracks(manifest: MusicTrack[]): MusicTrack[] {
  const qqTracks = aboutMusicTracks.filter((t) => isQqMusicTrack(t))
  if (manifest.length === 0) return qqTracks.length > 0 ? qqTracks : aboutMusicTracks
  const ids = new Set(manifest.map((t) => t.id))
  const extra = qqTracks.filter((t) => !ids.has(t.id))
  return extra.length > 0 ? [...manifest, ...extra] : manifest
}

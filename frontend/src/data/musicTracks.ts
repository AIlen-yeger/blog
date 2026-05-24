import type { ParticleTheme } from '@/types/music'

export interface MusicTrack {
  id: string
  title: string
  artist: string
  /** 放在 public/music/ 下的路径，或完整 https URL（CDN/OSS） */
  src: string
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

/** 无 manifest 时的占位；有 mp3 时由 scripts/musicManifest 自动生成 manifest.json */
export const aboutMusicTracks: MusicTrack[] = []
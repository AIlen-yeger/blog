/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_USE_MOCK?: string
  readonly VITE_RESEND_COOLDOWN_SECONDS?: string
  readonly VITE_MUSIC_BASE?: string
  readonly VITE_MUSIC_PARTICLE_THEME?: string
  readonly VITE_LANDING_VIDEO_URL?: string
  readonly VITE_LANDING_QQ_SONG_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

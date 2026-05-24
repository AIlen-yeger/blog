/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_USE_MOCK?: string
  readonly VITE_RESEND_COOLDOWN_SECONDS?: string
  readonly VITE_MUSIC_BASE?: string
  readonly VITE_MUSIC_PARTICLE_THEME?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

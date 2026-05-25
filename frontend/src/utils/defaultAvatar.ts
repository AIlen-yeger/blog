/** 着陆页 / Mock 默认头像（public/avatars/default.svg） */
export const DEFAULT_AVATAR_PATH = '/avatars/default.svg'

export function defaultAvatarUrl(): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '')
  return `${base}${DEFAULT_AVATAR_PATH}`
}

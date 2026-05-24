/** 对路径各段做 URL 编码（支持中文、空格、括号等文件名） */
export function encodeMusicPath(path: string): string {
  return path
    .split('/')
    .map((seg) => {
      if (!seg) return seg
      try {
        return encodeURIComponent(decodeURIComponent(seg))
      } catch {
        return encodeURIComponent(seg)
      }
    })
    .join('/')
}

/** 解析曲目地址：支持完整 URL，或通过 VITE_MUSIC_BASE 指向 CDN/OSS */
export function resolveMusicSrc(src: string): string {
  if (/^https?:\/\//i.test(src)) return src
  const base = (import.meta.env.VITE_MUSIC_BASE as string | undefined)?.replace(/\/$/, '') ?? ''
  const path = src.startsWith('/') ? src : `/${src}`
  return `${base}${encodeMusicPath(path)}`
}

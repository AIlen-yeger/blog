/** 优先 PNG（真透明），无则回退 JPG */
export function petSpriteSrc(id: string, ext: 'png' | 'jpg' = 'png'): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '')
  return `${base}/desktop-pet/${id}.${ext}`
}

export function petSpriteFallback(src: string): string | null {
  if (src.endsWith('.png')) return src.replace(/\.png$/i, '.jpg')
  return null
}

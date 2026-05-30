/** 从 QQ 音乐分享链接或文本解析 songid（与后端 QqMusicUrlParser 规则一致） */
export function parseQqMusicSongId(input: string): string | null {
  const text = input.trim()
  if (!text) return null

  const patterns = [
    /[?&]songid=(\d+)/i,
    /[?&]songmid=([A-Za-z0-9]+)/i,
    /\/songDetail\/(\d+)/i,
    /songid[=:]\s*(\d+)/i,
    /^(\d{5,12})$/,
  ]

  for (const pattern of patterns) {
    const m = text.match(pattern)
    if (m?.[1]) return m[1]
  }
  return null
}

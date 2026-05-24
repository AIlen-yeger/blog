export interface LyricLine {
  time: number
  text: string
}

/** 元数据行（词曲作者、版权等）或开头标题头 */
function isSkippableLyric(text: string, timeSec: number): boolean {
  const t = text.trim()
  if (!t) return true
  if (/^(词|曲|编|作词|作曲|编曲|制作人|演唱|混音|和声|出品|推广|SP|OP)[:：]/i.test(t)) {
    return true
  }
  if (/TME|著作权|文化有限公司|酷狗|星曜计划|享有本翻译|鲸鱼向海/.test(t)) {
    return true
  }
  if (/^『/.test(t) || /^Time goes/i.test(t)) return true
  // 常见单行 / 双语 LRC 开头的「歌名 - 歌手」头
  if (timeSec < 6 && t.length < 96 && /[-–—]/.test(t)) {
    if (!/[，。！？、；]/.test(t) || /feat\.|Michita|ミチタ/i.test(t)) return true
  }
  return false
}

/**
 * 解析 LRC，支持：
 * - 每行一句
 * - 整文件挤在一行、多个 [mm:ss.xx] 连写
 */
export function parseLrc(content: string): LyricLine[] {
  const lines: LyricLine[] = []
  // 去掉 [ti:xxx] [ar:xxx] 等非时间轴标签
  const stripped = content.replace(/\[(?!(\d+):(\d+(?:\.\d+)?)\])[^\]]*\]/g, '')
  const re = /\[(\d+):(\d+(?:\.\d+)?)\]([^\[]*)/g
  let match: RegExpExecArray | null

  while ((match = re.exec(stripped)) !== null) {
    const min = Number(match[1])
    const sec = Number(match[2])
    const text = match[3].replace(/\r?\n/g, ' ').trim()
    if (!text || !Number.isFinite(min) || !Number.isFinite(sec)) continue

    const time = min * 60 + sec
    if (isSkippableLyric(text, time)) continue

    lines.push({ time, text })
  }

  lines.sort((a, b) => a.time - b.time)

  const deduped: LyricLine[] = []
  for (const line of lines) {
    const prev = deduped[deduped.length - 1]
    if (prev && prev.time === line.time && prev.text === line.text) continue
    deduped.push(line)
  }
  return deduped
}

/** 当前播放时刻对应的歌词行下标 */
export function lyricIndexAt(lines: LyricLine[], t: number): number {
  if (!lines.length) return -1
  let idx = 0
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].time <= t) idx = i
    else break
  }
  return idx
}

/** 随机取当前行附近一句，用于飘落；sparse 时仅当前行，避免曲名/歌手刷屏 */
export function pickLyricSnippet(lines: LyricLine[], t: number, sparse = false): string | null {
  if (!lines.length) return null
  const idx = lyricIndexAt(lines, t)
  if (idx < 0) return lines[0]?.text ?? null
  if (sparse) return lines[idx]?.text ?? null
  const pool: string[] = []
  if (lines[idx]) pool.push(lines[idx].text)
  if (idx > 0 && lines[idx - 1]) pool.push(lines[idx - 1].text)
  if (idx + 1 < lines.length && lines[idx + 1]) pool.push(lines[idx + 1].text)
  const unique = [...new Set(pool.filter(Boolean))]
  if (!unique.length) return null
  return unique[Math.floor(Math.random() * unique.length)] ?? null
}

export function lrcPathFromAudioSrc(src: string): string {
  return src.replace(/\.(mp3|m4a|ogg|wav|flac)(\?.*)?$/i, '.lrc')
}

import fs from 'node:fs'
import path from 'node:path'
import type { Plugin } from 'vite'

const MUSIC_DIR = 'public/music'
const MANIFEST_FILE = 'manifest.json'
const AUDIO_EXT = /\.(mp3|m4a|ogg|wav|flac)$/i

export interface MusicManifestEntry {
  id: string
  title: string
  artist: string
  src: string
  particleTheme?: 'sakura' | 'leaf' | 'mixed'
  lyricsSrc?: string
}

/** 从文件名解析：艺术家 - 曲名.mp3 */
export function parseMusicFilename(filename: string): { title: string; artist: string } {
  const base = filename.replace(AUDIO_EXT, '').trim()
  const m = base.match(/^(.+?)\s*[-–—]\s*(.+)$/)
  if (m) return { artist: m[1].trim(), title: m[2].trim() }
  return { artist: '本地音乐', title: base || filename }
}

function normName(s: string): string {
  return s.toLowerCase().replace(/[\s_\-–—(（)）]/g, '')
}

/** 同名 .lrc 或按曲名/歌手模糊匹配（文件名不一致时） */
export function findLyricsFile(
  dir: string,
  audioFile: string,
  title: string,
  artist: string,
): string | undefined {
  const exact = `${audioFile.replace(AUDIO_EXT, '')}.lrc`
  if (fs.existsSync(path.join(dir, exact))) return exact

  const lrcFiles = fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isFile() && e.name.toLowerCase().endsWith('.lrc'))
    .map((e) => e.name)

  const nt = normName(title)
  const na = normName(artist)

  const scored = lrcFiles
    .map((name) => {
      const nf = normName(name)
      let score = 0
      if (nt && nf.includes(nt)) score += 3
      if (na && nf.includes(na)) score += 2
      else if (na.length >= 4 && nf.includes(na.slice(0, 4))) score += 1
      return { name, score }
    })
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)

  return scored[0]?.name
}

export function generateMusicManifest(projectRoot: string): number {
  const dir = path.join(projectRoot, MUSIC_DIR)
  if (!fs.existsSync(dir)) return 0

  const files = fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isFile() && AUDIO_EXT.test(e.name))
    .map((e) => e.name)
    .sort((a, b) => a.localeCompare(b, 'zh-CN'))

  const tracks: MusicManifestEntry[] = files.map((file, i) => {
    const { title, artist } = parseMusicFilename(file)
    const lrcFile = findLyricsFile(dir, file, title, artist)
    return {
      id: `local-${i}-${file}`,
      title,
      artist,
      src: `/music/${file}`,
      particleTheme: i % 2 === 0 ? 'sakura' : 'leaf',
      ...(lrcFile ? { lyricsSrc: `/music/${lrcFile}` } : {}),
    }
  })

  const outPath = path.join(dir, MANIFEST_FILE)
  fs.writeFileSync(outPath, `${JSON.stringify(tracks, null, 2)}\n`, 'utf8')
  return tracks.length
}

export function musicManifestPlugin(): Plugin {
  let root = ''
  const regen = () => {
    if (!root) return
    const n = generateMusicManifest(root)
    // eslint-disable-next-line no-console
    console.log(`[music-manifest] ${n} 首曲目 → ${MUSIC_DIR}/${MANIFEST_FILE}`)
  }

  return {
    name: 'music-manifest',
    configResolved(config) {
      root = config.root
      regen()
    },
    configureServer(server) {
      const dir = path.join(root, MUSIC_DIR)
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
      server.watcher.add(dir)
      const onChange = (file: string) => {
        if (AUDIO_EXT.test(file) || /\.lrc$/i.test(file) || file.endsWith(MANIFEST_FILE)) regen()
      }
      server.watcher.on('add', onChange)
      server.watcher.on('unlink', onChange)
    },
    buildStart() {
      regen()
    },
  }
}

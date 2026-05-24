import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const AUDIO_EXT = /\.(mp3|m4a|ogg|wav|flac)$/i
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const dir = path.join(root, 'public/music')

function parseMusicFilename(filename) {
  const base = filename.replace(AUDIO_EXT, '').trim()
  const m = base.match(/^(.+?)\s*[-–—]\s*(.+)$/)
  if (m) return { artist: m[1].trim(), title: m[2].trim() }
  return { artist: '本地音乐', title: base || filename }
}

if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })

const files = fs
  .readdirSync(dir)
  .filter((f) => AUDIO_EXT.test(f))
  .sort((a, b) => a.localeCompare(b, 'zh-CN'))

const tracks = files.map((file, i) => {
  const { title, artist } = parseMusicFilename(file)
  return {
    id: `local-${i}-${file}`,
    title,
    artist,
    src: `/music/${file}`,
    particleTheme: i % 2 === 0 ? 'sakura' : 'leaf',
  }
})

fs.writeFileSync(
  path.join(dir, 'manifest.json'),
  `${JSON.stringify(tracks, null, 2)}\n`,
  'utf8',
)
console.log(`已生成 ${tracks.length} 首曲目 → public/music/manifest.json`)

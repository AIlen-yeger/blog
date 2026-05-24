import { computed, ref, watch } from 'vue'
import type { LyricLine } from '@/utils/lrc'
import { lrcPathFromAudioSrc, parseLrc } from '@/utils/lrc'
import { resolveMusicSrc } from '@/utils/musicSrc'
import { useAboutMusic } from '@/composables/useAboutMusic'
import type { MusicTrack } from '@/data/musicTracks'

const fileLyrics = ref<LyricLine[]>([])
let loadToken = 0

async function fetchLyrics(url: string): Promise<LyricLine[]> {
  const fetchUrl = `${url}${url.includes('?') ? '&' : '?'}t=${Date.now()}`
  const res = await fetch(fetchUrl)
  if (!res.ok) return []
  const text = await res.text()
  return parseLrc(text)
}

async function lyricsSrcFromManifest(track: MusicTrack): Promise<string | undefined> {
  try {
    const res = await fetch(`/music/manifest.json?t=${Date.now()}`)
    if (!res.ok) return undefined
    const list = (await res.json()) as MusicTrack[]
    const self = list.find((t) => t.id === track.id)
    if (self?.lyricsSrc) return self.lyricsSrc
    const norm = (s: string) => s.toLowerCase().replace(/[\s_\-–—(（)）]/g, '')
    const nt = norm(track.title)
    const match = list.find(
      (t) => t.lyricsSrc && norm(t.title) === nt,
    )
    return match?.lyricsSrc
  } catch {
    return undefined
  }
}

export function useMusicLyrics() {
  const { currentTrack } = useAboutMusic()

  async function loadForTrack() {
    const track = currentTrack.value
    const token = ++loadToken
    fileLyrics.value = []

    if (!track) return

    const fromManifest = await lyricsSrcFromManifest(track)
    const explicit = track.lyricsSrc ?? fromManifest
    const guessed = lrcPathFromAudioSrc(track.src)
    const candidates = [explicit, guessed]
      .filter((u): u is string => !!u)
      .map((u) => resolveMusicSrc(u))

    for (const url of [...new Set(candidates)]) {
      try {
        const lines = await fetchLyrics(url)
        if (token !== loadToken) return
        if (lines.length > 0) {
          fileLyrics.value = lines
          return
        }
      } catch {
        /* 尝试下一个路径 */
      }
    }
  }

  watch(
    () => [currentTrack.value?.id, currentTrack.value?.lyricsSrc] as const,
    () => {
      void loadForTrack()
    },
    { immediate: true },
  )

  const hasLrcFile = computed(() => fileLyrics.value.length > 0)

  const fallbackLines = computed<LyricLine[]>(() => {
    const t = currentTrack.value
    if (!t) return []
    const out: LyricLine[] = []
    if (t.title) out.push({ time: 0, text: t.title })
    if (t.artist && t.artist !== t.title) out.push({ time: 0, text: t.artist })
    return out
  })

  const lyricLines = computed(() =>
    fileLyrics.value.length > 0 ? fileLyrics.value : fallbackLines.value,
  )

  return {
    lyricLines,
    hasLrcFile,
    reloadLyrics: loadForTrack,
  }
}

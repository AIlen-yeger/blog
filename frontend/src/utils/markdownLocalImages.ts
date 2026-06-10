const MD_IMAGE_RE = /!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g
const HTML_IMG_RE = /<img\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi
const IMAGE_EXT_RE = /\.(png|jpe?g|gif|webp|svg|bmp|avif)$/i

export function normalizePathKey(path: string): string {
  return path
    .trim()
    .replace(/\\/g, '/')
    .replace(/^\.\//, '')
    .replace(/^\/+/, '')
    .toLowerCase()
}

function basename(path: string): string {
  const normalized = path.replace(/\\/g, '/').trim()
  return (normalized.split('/').pop() || normalized).toLowerCase()
}

function isRemoteUrl(path: string): boolean {
  const p = path.trim().toLowerCase()
  return (
    p.startsWith('http://') ||
    p.startsWith('https://') ||
    p.startsWith('//') ||
    p.startsWith('/v1/') ||
    p.startsWith('/uploads/')
  )
}

export function isLocalImagePath(path: string): boolean {
  const p = path.trim()
  if (!p || isRemoteUrl(p)) return false
  if (/^(file:|data:)/i.test(p)) return true
  if (/^[a-zA-Z]:[\\/]/.test(p)) return true
  return IMAGE_EXT_RE.test(p)
}

/** 从同批选中的文件建立「相对路径 / 文件名 → File」索引（支持文件夹上传 webkitRelativePath） */
export function buildFileLookup(files: File[]): Map<string, File> {
  const map = new Map<string, File>()
  for (const file of files) {
    const rel = (file as File & { webkitRelativePath?: string }).webkitRelativePath?.trim()
    if (rel) {
      const norm = normalizePathKey(rel)
      map.set(norm, file)
      const parts = norm.split('/')
      for (let i = 1; i < parts.length; i += 1) {
        map.set(parts.slice(i).join('/'), file)
      }
    }
    map.set(normalizePathKey(file.name), file)
  }
  return map
}

export function findFileForImageRef(ref: string, lookup: Map<string, File>): File | null {
  const norm = normalizePathKey(ref)
  const direct = lookup.get(norm)
  if (direct) return direct
  const base = basename(ref)
  return lookup.get(base) ?? null
}

export function extractLocalImageRefs(markdown: string): string[] {
  const found: string[] = []
  const seen = new Set<string>()

  const collect = (src: string) => {
    if (!src || !isLocalImagePath(src) || seen.has(src)) return
    seen.add(src)
    found.push(src)
  }

  MD_IMAGE_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = MD_IMAGE_RE.exec(markdown)) !== null) {
    collect(m[2])
  }
  HTML_IMG_RE.lastIndex = 0
  while ((m = HTML_IMG_RE.exec(markdown)) !== null) {
    collect(m[1])
  }
  return found
}

function chunk<T>(items: T[], size: number): T[][] {
  const out: T[][] = []
  for (let i = 0; i < items.length; i += size) {
    out.push(items.slice(i, i + size))
  }
  return out
}

function replaceImageRef(markdown: string, ref: string, url: string): string {
  const escaped = ref.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const mdRe = new RegExp(`(!\\[[^\\]]*\\]\\()${escaped}((?:\\s+"[^"]*")?\\))`, 'g')
  const htmlRe = new RegExp(`(<img\\b[^>]*\\bsrc=["'])${escaped}(["'][^>]*>)`, 'gi')
  return markdown.replace(mdRe, `$1${url}$2`).replace(htmlRe, `$1${url}$2`)
}

/**
 * 解析 Markdown 中的本地图片引用，从同批文件池匹配并异步上传，再写回云端 URL。
 * 浏览器无法按 C:\\ 绝对路径读盘，需用户同批选中图片或上传整个文件夹。
 */
export async function uploadAndRewriteMarkdownImages(
  markdown: string,
  poolFiles: File[],
  upload: (file: File) => Promise<string>,
  opts?: { concurrency?: number },
): Promise<{ text: string; uploaded: number; unmatched: string[] }> {
  const refs = extractLocalImageRefs(markdown)
  if (!refs.length) {
    return { text: markdown, uploaded: 0, unmatched: [] }
  }

  const lookup = buildFileLookup(poolFiles)
  const fileToRefs = new Map<File, string[]>()
  const unmatched: string[] = []

  for (const ref of refs) {
    const file = findFileForImageRef(ref, lookup)
    if (!file) {
      unmatched.push(ref)
      continue
    }
    const list = fileToRefs.get(file) ?? []
    list.push(ref)
    fileToRefs.set(file, list)
  }

  let text = markdown
  let uploaded = 0
  const concurrency = opts?.concurrency ?? 3
  const entries = [...fileToRefs.entries()]

  for (const batch of chunk(entries, concurrency)) {
    await Promise.all(
      batch.map(async ([file, refList]) => {
        const url = await upload(file)
        for (const ref of refList) {
          text = replaceImageRef(text, ref, url)
          uploaded += 1
        }
      }),
    )
  }

  return { text, uploaded, unmatched }
}

/** @deprecated 仅按文件名匹配；请优先用 uploadAndRewriteMarkdownImages */
export function buildImageUrlMap(
  files: File[],
  uploaded: { name: string; url: string }[],
): Map<string, string> {
  const map = new Map<string, string>()
  for (let i = 0; i < files.length; i += 1) {
    const file = files[i]
    const url = uploaded[i]?.url
    if (!url) continue
    map.set(file.name.toLowerCase(), url)
    map.set(basename(file.name), url)
  }
  return map
}

export function collectUnmatchedLocalImages(markdown: string): string[] {
  return extractLocalImageRefs(markdown)
}

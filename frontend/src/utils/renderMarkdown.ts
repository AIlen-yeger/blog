/** 笔记正文轻量 Markdown 渲染（无第三方依赖，仅常用语法） */

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderInlineMarkdown(text: string): string {
  let out = escapeHtml(text)
  out = out.replace(/`([^`\n]+)`/g, '<code>$1</code>')
  out = out.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
  out = out.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>')
  return out
}

function renderBlockLine(line: string): string {
  const trimmed = line.trimEnd()
  const h3 = trimmed.match(/^###\s+(.+)$/)
  if (h3) return `<h3>${renderInlineMarkdown(h3[1])}</h3>`
  const h2 = trimmed.match(/^##\s+(.+)$/)
  if (h2) return `<h2>${renderInlineMarkdown(h2[1])}</h2>`
  const h1 = trimmed.match(/^#\s+(.+)$/)
  if (h1) return `<h1>${renderInlineMarkdown(h1[1])}</h1>`
  if (!trimmed.trim()) return ''
  return `<p>${renderInlineMarkdown(trimmed)}</p>`
}

/** 将 Markdown 笔记正文转为可安全 v-html 的 HTML */
export function renderNoteMarkdown(source: string): string {
  const normalized = (source ?? '').replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  if (!normalized.trim()) return ''

  const blocks: string[] = []
  let inCode = false
  let codeLines: string[] = []

  for (const line of normalized.split('\n')) {
    if (line.trim().startsWith('```')) {
      if (inCode) {
        blocks.push(`<pre class="md-code"><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
        codeLines = []
        inCode = false
      } else {
        inCode = true
      }
      continue
    }
    if (inCode) {
      codeLines.push(line)
      continue
    }
    const block = renderBlockLine(line)
    if (block) blocks.push(block)
  }

  if (inCode && codeLines.length) {
    blocks.push(`<pre class="md-code"><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`)
  }

  return blocks.join('')
}

/** 摘要等纯文本场景：去掉常见 Markdown 标记 */
export function stripMarkdownForPlainText(source: string): string {
  return (source ?? '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\s+/g, ' ')
    .trim()
}
